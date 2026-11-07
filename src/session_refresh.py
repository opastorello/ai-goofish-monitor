"""
Keep each account's ``_m_h5_tk`` token fresh between runs.

The H5 token lives ~2 hours. Instead of waiting for a scrape to hit
FAIL_SYS_TOKEN_EXPIRED, a light ``mtop.common.getTimestamp`` call (what the
goofish-sync extension does every 30 minutes) makes the server hand out a new
token via Set-Cookie, which is merged into the account's login-state file. No
browser, no detail page, a single request.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import httpx

from src.cookie_state import normalize_state
from src.human_verification import save_session_cookies

MTOP_HOST = "https://h5api.m.goofish.com"
APP_KEY = "34839810"
REFRESH_NAMES = ("_m_h5_tk", "_m_h5_tk_enc")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def token_expiry_seconds(cookies: list[dict], *, now: Optional[float] = None) -> Optional[float]:
    """Seconds until the current _m_h5_tk expires (None when unknown/missing)."""
    for cookie in cookies:
        if cookie.get("name") == "_m_h5_tk":
            _, _, expiry = str(cookie.get("value", "")).partition("_")
            if expiry.isdigit():
                return int(expiry) / 1000 - (time.time() if now is None else now)
    return None


def _login_call(http: httpx.Client, jar: dict[str, str], user_agent: str):
    from src.services.login_status_service import _call

    return _call(http, jar, user_agent)


def refresh_session(state_path: str, *, client: Optional[httpx.Client] = None, min_remaining: float = 45 * 60) -> dict[str, Any]:
    """Refresh the token when it is missing or about to expire. Returns a small report."""
    report: dict[str, Any] = {"state": state_path, "refreshed": False, "reason": ""}
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            state = normalize_state(json.load(handle))
    except (OSError, ValueError) as exc:
        report["reason"] = f"unreadable: {exc}"
        return report
    cookies = (state or {}).get("cookies") or []
    if not any(c.get("name") == "cookie2" for c in cookies):
        report["reason"] = "no login (cookie2) in the file"
        return report
    remaining = token_expiry_seconds(cookies)
    if remaining is not None and remaining > min_remaining:
        report["reason"] = f"token still valid for {int(remaining // 60)} min"
        return report

    jar = {c["name"]: c["value"] for c in cookies if c.get("name") and c.get("value") is not None}
    user_agent = ((state.get("headers") or {}).get("User-Agent")
                  or (state.get("headers") or {}).get("user-agent") or DEFAULT_USER_AGENT)
    owns = client is None
    http = client or httpx.Client(timeout=15.0)
    try:
        # A correctly signed call with a stale token makes mtop answer
        # FAIL_SYS_TOKEN_EXOIRED *with* fresh _m_h5_tk cookies (an unsigned
        # getTimestamp call never issues one).
        _, response = _login_call(http, jar, user_agent)
    except (httpx.HTTPError, ValueError) as exc:
        report["reason"] = f"request failed: {exc}"
        return report
    finally:
        if owns:
            http.close()

    fresh = []
    for name in REFRESH_NAMES:
        value = response.cookies.get(name)
        if value:
            fresh.append({"name": name, "value": value, "domain": ".goofish.com", "path": "/",
                          "expires": -1, "httpOnly": False, "secure": True, "sameSite": "Lax"})
    if not fresh:
        report["reason"] = "the server did not issue a new token"
        return report
    changed = save_session_cookies(state_path, fresh)
    report.update(refreshed=bool(changed), reason="token renewed" if changed else "no change")
    return report


def refresh_all_accounts(state_dir: str = "state") -> list[dict[str, Any]]:
    reports = []
    if not os.path.isdir(state_dir):
        return reports
    for name in sorted(os.listdir(state_dir)):
        if name.endswith(".json"):
            reports.append(refresh_session(os.path.join(state_dir, name)))
    return reports

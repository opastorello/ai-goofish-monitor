"""
Login-state check ("auth status"): is the saved Goofish cookie file still logged in?

It signs and sends one lightweight mtop request (the same one the web client uses
to load the signed-in user) over plain HTTP, so no browser is launched and nothing
is scraped. Cookie values are never returned.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

APP_KEY = "34839810"
MTOP_HOST = "https://h5api.m.goofish.com"
LOGIN_USER_API = "mtop.taobao.idlemessage.pc.loginuser.get"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)

_RISK_KEYWORDS = ("RGV587_ERROR", "FAIL_SYS_USER_VALIDATE", "哎哟喂", "/punish")
_TOKEN_KEYWORDS = ("FAIL_SYS_TOKEN_EXOIRED", "FAIL_SYS_TOKEN_EMPTY", "令牌过期")
_SESSION_KEYWORDS = ("FAIL_SYS_SESSION_EXPIRED", "FAIL_SYS_ILLEGAL_ACCESS")


def generate_sign(timestamp_ms: str, token: str, data: str) -> str:
    return hashlib.md5(f"{token}&{timestamp_ms}&{APP_KEY}&{data}".encode()).hexdigest()


def _load_cookies(state_path: str) -> tuple[dict[str, str], dict]:
    with open(state_path, "r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    cookies = {
        str(item["name"]): str(item["value"])
        for item in (snapshot.get("cookies") or [])
        if isinstance(item, dict) and item.get("name") and item.get("value") is not None
    }
    return cookies, snapshot if isinstance(snapshot, dict) else {}


def _token_parts(cookies: dict[str, str]) -> tuple[str, Optional[datetime]]:
    raw = cookies.get("_m_h5_tk", "")
    token, _, expiry = raw.partition("_")
    expires_at = None
    if expiry.isdigit():
        try:
            expires_at = datetime.fromtimestamp(int(expiry) / 1000, tz=timezone.utc)
        except (ValueError, OSError):
            expires_at = None
    return token, expires_at


def _classify(ret_text: str) -> str:
    if "SUCCESS" in ret_text:
        return "valid"
    if any(key in ret_text for key in _RISK_KEYWORDS):
        return "risk_control"
    if any(key in ret_text for key in _TOKEN_KEYWORDS):
        return "token_expired"
    if any(key in ret_text for key in _SESSION_KEYWORDS):
        return "expired"
    return "error"


def _call(client: httpx.Client, cookies: dict[str, str], user_agent: str) -> tuple[dict, httpx.Response]:
    token, _ = _token_parts(cookies)
    timestamp = str(int(time.time() * 1000))
    data = "{}"
    params = {
        "jsv": "2.7.2",
        "appKey": APP_KEY,
        "t": timestamp,
        "sign": generate_sign(timestamp, token, data),
        "v": "1.0",
        "type": "originaljson",
        "accountSite": "xianyu",
        "dataType": "json",
        "timeout": "20000",
        "api": LOGIN_USER_API,
        "sessionOption": "AutoLoginOnly",
        "spm_cnt": "a21ybx.im.0.0",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.goofish.com",
        "referer": "https://www.goofish.com/",
        "user-agent": user_agent,
        "cookie": "; ".join(f"{name}={value}" for name, value in cookies.items()),
    }
    response = client.post(
        f"{MTOP_HOST}/h5/{LOGIN_USER_API}/1.0/", params=params, headers=headers, data={"data": data}
    )
    return response.json(), response


def check_login_state(
    state_path: str, *, client: Optional[httpx.Client] = None
) -> dict[str, Any]:
    """Return {valid, status, nick, unb, tracknick, reason, h5_token_expires_at, checked_at}."""
    result: dict[str, Any] = {
        "valid": False,
        "status": "error",
        "nick": "",
        "unb": "",
        "tracknick": "",
        "reason": "",
        "h5_token_expires_at": None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if not os.path.isfile(state_path):
        result.update(status="missing_file", reason="login state file not found")
        return result
    try:
        cookies, snapshot = _load_cookies(state_path)
    except (OSError, ValueError) as exc:
        result.update(status="invalid_file", reason=f"could not read the login state file: {exc}")
        return result

    result["unb"] = cookies.get("unb", "")
    result["tracknick"] = cookies.get("tracknick", "")
    token, expires_at = _token_parts(cookies)
    result["h5_token_expires_at"] = expires_at.isoformat() if expires_at else None
    if not token:
        result.update(status="missing_token", reason="_m_h5_tk cookie is missing; export the login state again")
        return result

    user_agent = (snapshot.get("headers") or {}).get("user-agent") or DEFAULT_USER_AGENT
    owns_client = client is None
    http = client or httpx.Client(timeout=20.0)
    try:
        for attempt in (1, 2):
            try:
                payload, response = _call(http, cookies, user_agent)
            except (httpx.HTTPError, ValueError) as exc:
                result.update(status="error", reason=f"request failed: {exc}")
                return result
            ret_text = " ".join(str(item) for item in (payload.get("ret") or []))
            status = _classify(ret_text)
            if status == "token_expired" and attempt == 1:
                # the server hands out a fresh _m_h5_tk with the failure; retry once with it
                for name in ("_m_h5_tk", "_m_h5_tk_enc"):
                    fresh = response.cookies.get(name)
                    if fresh:
                        cookies[name] = fresh
                if _token_parts(cookies)[0] != token:
                    token = _token_parts(cookies)[0]
                    continue
            if status == "valid":
                data = payload.get("data") or {}
                result.update(valid=True, status="valid", nick=str(data.get("nick") or ""))
                return result
            reason = ret_text.strip() or "unexpected response"
            result.update(status="expired" if status == "token_expired" else status, reason=reason[:300])
            return result
    finally:
        if owns_client:
            http.close()
    return result

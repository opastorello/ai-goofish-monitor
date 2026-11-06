"""Accept a login-state file in either shape.

* Playwright storage state: ``{"cookies": [...], "origins": [...]}`` (possibly with the
  extension's extra ``env``/``headers`` keys).
* A bare cookie list exported by a browser extension (Cookie-Editor style:
  ``expirationDate``, ``storeId``, ``sameSite: "no_restriction"``...).

Playwright silently ignores the second shape, which looks like "not logged in".
"""
from __future__ import annotations

from typing import Any

_SAME_SITE = {"no_restriction": "None", "none": "None", "lax": "Lax", "strict": "Strict"}


def _to_playwright_cookie(item: dict) -> dict:
    cookie = {
        "name": str(item["name"]),
        "value": str(item.get("value", "")),
        "domain": item.get("domain") or "",
        "path": item.get("path") or "/",
        "httpOnly": bool(item.get("httpOnly", False)),
        "secure": bool(item.get("secure", False)),
        "sameSite": _SAME_SITE.get(str(item.get("sameSite") or "").lower(), "Lax"),
    }
    expires = item.get("expires", item.get("expirationDate"))
    cookie["expires"] = float(expires) if isinstance(expires, (int, float)) and expires > 0 else -1
    return cookie


def normalize_state(data: Any) -> Any:
    """Return a dict with Playwright-shaped cookies when given a bare cookie list."""
    if isinstance(data, list):
        return {
            "cookies": [_to_playwright_cookie(c) for c in data if isinstance(c, dict) and c.get("name")],
            "origins": [],
        }
    return data

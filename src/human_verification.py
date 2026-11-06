"""
Let a person solve Goofish's slider and keep the session that results.

When the detail API answers FAIL_SYS_USER_VALIDATE in a *visible* browser, the page
shows a verification the scraper cannot pass. Instead of giving up at once, the run
waits (bounded) for the person to solve it in the open window. Passing hands the
browser the anti-bot cookies (x5sec, ...), so the new cookies are merged back into the
account's login-state file: later runs, headless ones included, start with them.

Only meaningful with a window; headless runs keep the previous behaviour (stop).
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from src.cookie_state import normalize_state

ANTI_BOT_NAMES = ("x5sec", "mtop_partitioned_detect")


def _key(cookie: dict) -> tuple:
    return (cookie.get("name"), cookie.get("domain"), cookie.get("path") or "/")


def merge_cookies(existing: list[dict], fresh: list[dict]) -> list[dict]:
    """Union by (name, domain, path); a fresh cookie replaces the stored one."""
    merged: dict[tuple, dict] = {}
    for cookie in list(existing or []) + list(fresh or []):
        if isinstance(cookie, dict) and cookie.get("name"):
            merged[_key(cookie)] = cookie
    return list(merged.values())


def anti_bot_values(cookies: list[dict]) -> dict[str, str]:
    return {
        c["name"]: str(c.get("value") or "")
        for c in cookies or []
        if isinstance(c, dict) and c.get("name") in ANTI_BOT_NAMES
    }


def solved_by_cookies(before: dict[str, str], cookies: list[dict]) -> bool:
    """True once an anti-bot cookie exists that was not there (or changed) before."""
    now = anti_bot_values(cookies)
    return any(now.get(name) and now.get(name) != before.get(name) for name in ANTI_BOT_NAMES)


def has_x5sec(cookies: list[dict]) -> bool:
    return bool(anti_bot_values(cookies).get("x5sec"))


def save_session_cookies(state_path: str, fresh_cookies: list[dict], *, now: Optional[datetime] = None) -> bool:
    """
    Merge `fresh_cookies` into the login-state file, keeping everything else in it
    (headers, env, storage...). Atomic write. Returns True when the file changed.
    """
    with open(state_path, "r", encoding="utf-8") as handle:
        snapshot = normalize_state(json.load(handle))
    if not isinstance(snapshot, dict):
        return False
    existing = snapshot.get("cookies") or []
    merged = merge_cookies(existing, fresh_cookies)
    if merged == existing:
        return False
    snapshot["cookies"] = merged
    snapshot["cookiesRefreshedAt"] = (now or datetime.now(timezone.utc)).isoformat()

    directory = os.path.dirname(os.path.abspath(state_path))
    mode = os.stat(state_path).st_mode & 0o777
    fd, tmp_path = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, state_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return True


async def wait_for_human_verification(
    page,
    context,
    state_path: str,
    *,
    timeout_seconds: float,
    detail_url_pattern: str,
    poll_seconds: float = 2.0,
    log: Callable[[str], Any] = print,
    sleep: Callable[[float], Any] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """
    Wait up to `timeout_seconds` for the verification on `page` to be solved. Solved means
    a new anti-bot cookie showed up in the context, or the page's detail request was
    replayed and succeeded. On success the session is saved and True is returned.
    """
    before = anti_bot_values(await context.cookies())
    replayed = {"ok": False}

    async def on_response(response) -> None:
        if detail_url_pattern not in getattr(response, "url", ""):
            return
        try:
            body = await response.json()
        except Exception:  # noqa: BLE001 - not JSON / page navigating
            return
        if "SUCCESS" in str((body or {}).get("ret")):
            replayed["ok"] = True

    page.on("response", on_response)
    try:
        try:
            await page.bring_to_front()
        except Exception:  # noqa: BLE001 - headless or page already gone
            pass
        deadline = clock() + timeout_seconds
        while clock() < deadline:
            if page.is_closed():
                return False
            cookies = await context.cookies()
            if replayed["ok"] or solved_by_cookies(before, cookies):
                save_session_cookies(state_path, cookies)
                log(f"验证已通过，新的登录态已保存到 {state_path}。继续处理下一个商品，本商品下次运行再处理。")
                if has_x5sec(cookies):
                    log("登录态里已包含 x5sec 反爬 Cookie，之后的运行（包括无窗口模式）会沿用它。")
                return True
            await sleep(poll_seconds)
        return False
    finally:
        try:
            page.remove_listener("response", on_response)
        except Exception:  # noqa: BLE001
            pass

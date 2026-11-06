"""
Open a visible browser with an account's login state so a person can solve the
Goofish slider, then keep the resulting anti-bot cookies and lift the cool-down.

Run as a subprocess (the Accounts page "Resolver verificação" button does this):
    python -m src.verify_session <state_file> [url]
Progress is written to logs/account-verify.json so the UI can show it.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time

from playwright.async_api import async_playwright

from src.account_guard import AccountGuard, account_key
from src.config import DETAIL_API_URL_PATTERN
from src.human_verification import wait_for_human_verification
from src.scraper import (
    _build_context_overrides,
    _build_extra_headers,
    _clean_kwargs,
    _default_context_options,
    _resolve_browser_channel,
    prepare_chromium_launch_args,
)

STATUS_FILE = os.path.join("logs", "account-verify.json")
DEFAULT_URL = "https://www.goofish.com/"
WAIT_SECONDS = int(os.getenv("VERIFY_SESSION_WAIT_SECONDS", "600"))


def write_status(status: str, account: str, message: str = "") -> None:
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    payload = {"status": status, "account": account, "message": message, "updated_at": time.time(), "pid": os.getpid()}
    tmp = STATUS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    os.replace(tmp, STATUS_FILE)


def pick_item_url() -> str:
    """A recent item page: the detail view is where the slider shows up."""
    try:
        with sqlite3.connect(os.path.join("data", "app.sqlite3")) as conn:
            row = conn.execute("SELECT item_id FROM result_items WHERE item_id IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        if row and row[0]:
            return f"https://www.goofish.com/item?id={row[0]}"
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_URL


async def run(state_file: str, url: str | None) -> int:
    account = account_key(state_file)
    write_status("opening", account)
    with open(state_file, "r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, args=prepare_chromium_launch_args(), channel=_resolve_browser_channel()
        )
        kwargs = _default_context_options()
        storage_state = state_file
        if isinstance(snapshot, dict) and any(k in snapshot for k in ("env", "headers", "page", "storage")):
            storage_state = {"cookies": snapshot.get("cookies", [])}
            kwargs.update(_build_context_overrides(snapshot))
            headers = _build_extra_headers(snapshot.get("headers"))
            if headers:
                kwargs["extra_http_headers"] = headers
        context = await browser.new_context(storage_state=storage_state, **_clean_kwargs(kwargs))
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = await context.new_page()
        write_status("waiting", account, "Resolva o slider na janela do navegador.")
        try:
            await page.goto(url or pick_item_url(), wait_until="domcontentloaded", timeout=45000)
        except Exception:  # noqa: BLE001 - the page may still be usable
            pass
        solved = await wait_for_human_verification(
            page, context, state_file, timeout_seconds=WAIT_SECONDS,
            detail_url_pattern=DETAIL_API_URL_PATTERN, log=print,
        )
        if solved:
            AccountGuard().reset(account)
            write_status("solved", account, "Verificação concluída; o resfriamento da conta foi liberado.")
            await asyncio.sleep(2)
        else:
            closed = page.is_closed()
            write_status("closed" if closed else "timeout", account,
                         "A janela foi fechada sem concluir." if closed else "Tempo esgotado sem concluir a verificação.")
        try:
            await browser.close()
        except Exception:  # noqa: BLE001
            pass
    return 0 if solved else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python -m src.verify_session <state_file> [url]")
    sys.exit(asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))

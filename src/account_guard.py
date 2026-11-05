"""
Account-level risk-control guardrail, modelled on goofish-cli's built-in guard.

Two protections, both persisted per account (so every task and every process that
shares an account shares them):

* Circuit breaker - the first RGV587 / FAIL_SYS_USER_VALIDATE style block trips a
  cool-down. While it lasts, runs on that account do not touch Goofish at all,
  because retrying while challenged only extends the block. It lifts by itself, or
  by hand (Accounts page). Note this only clears the *local* breaker: the server
  side challenge has its own clock.
* Token bucket - item-detail visits are paced (default 1 per minute after a small
  burst) across all tasks of the account.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

from src.failure_guard import (
    _FileLock,
    _atomic_write_json,
    _ensure_parent_dir,
    _read_json_file,
)

DEFAULT_PATH = "logs/account-risk-guard.json"
DEFAULT_COOLDOWN_MINUTES = 30
DEFAULT_BUCKET_CAPACITY = 3
DEFAULT_REFILL_SECONDS = 60


def _env_number(name: str, default: float, minimum: float) -> float:
    try:
        return max(minimum, float(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def account_key(state_path: Optional[str]) -> str:
    """Stable key for an account: the state file name without extension."""
    base = os.path.basename(str(state_path or "")).strip()
    return os.path.splitext(base)[0] or "default"


class AccountGuard:
    def __init__(
        self,
        path: Optional[str] = None,
        *,
        cooldown_seconds: Optional[float] = None,
        bucket_capacity: Optional[int] = None,
        refill_seconds: Optional[float] = None,
    ):
        self.path = path or os.getenv("ACCOUNT_RISK_GUARD_PATH") or DEFAULT_PATH
        self.cooldown_seconds = (
            cooldown_seconds
            if cooldown_seconds is not None
            else _env_number("ACCOUNT_RISK_COOLDOWN_MINUTES", DEFAULT_COOLDOWN_MINUTES, 1) * 60
        )
        self.bucket_capacity = int(
            bucket_capacity
            if bucket_capacity is not None
            else _env_number("ACCOUNT_DETAIL_BUCKET_CAPACITY", DEFAULT_BUCKET_CAPACITY, 1)
        )
        self.refill_seconds = (
            refill_seconds
            if refill_seconds is not None
            else _env_number("ACCOUNT_DETAIL_REFILL_SECONDS", DEFAULT_REFILL_SECONDS, 1)
        )

    # -- persistence ---------------------------------------------------------
    def _mutate(self, updater):
        _ensure_parent_dir(self.path)
        with open(self.path, "a+", encoding="utf-8") as handle:
            with _FileLock(handle):
                handle.seek(0)
                data = _read_json_file(self.path)
                accounts = data.get("accounts")
                if not isinstance(accounts, dict):
                    accounts = {}
                data["accounts"] = accounts
                data.setdefault("version", 1)
                result = updater(accounts)
                _atomic_write_json(self.path, data)
                return result

    def _read(self) -> dict:
        data = _read_json_file(self.path)
        accounts = data.get("accounts")
        return accounts if isinstance(accounts, dict) else {}

    # -- circuit breaker -----------------------------------------------------
    def cooldown_remaining(self, key: str, *, now: Optional[float] = None) -> float:
        """Seconds left on the account's cool-down (0 when it may run)."""
        entry = self._read().get(key) or {}
        until = entry.get("cooldown_until") if isinstance(entry, dict) else None
        if not isinstance(until, (int, float)):
            return 0.0
        return max(0.0, float(until) - (time.time() if now is None else now))

    def trip(self, key: str, reason: str = "", *, now: Optional[float] = None) -> float:
        """Start (or extend) the cool-down; returns when it ends (epoch seconds)."""
        current = time.time() if now is None else now
        until = current + self.cooldown_seconds

        def _apply(accounts: dict) -> float:
            entry = accounts.get(key)
            entry = entry if isinstance(entry, dict) else {}
            entry.update(
                cooldown_until=until,
                tripped_at=current,
                reason=(reason or "risk control")[:300],
                trips=int(entry.get("trips", 0) or 0) + 1,
            )
            accounts[key] = entry
            return until

        return self._mutate(_apply)

    def reset(self, key: Optional[str] = None) -> int:
        """Lift the cool-down of one account, or of all. Returns how many were cooling."""

        def _apply(accounts: dict) -> int:
            targets = [key] if key is not None else list(accounts)
            lifted = 0
            for name in targets:
                entry = accounts.get(name)
                if isinstance(entry, dict) and entry.get("cooldown_until"):
                    lifted += 1
                    entry["cooldown_until"] = None
                    entry["reason"] = None
            return lifted

        return self._mutate(_apply)

    # -- token bucket --------------------------------------------------------
    def acquire_detail_slot(self, key: str, *, now: Optional[float] = None) -> float:
        """
        Reserve one item-detail visit. Returns how many seconds the caller must wait
        before making it (0 when a token was free). Reservations may drive the bucket
        negative, so concurrent processes queue up instead of bursting together.
        """
        current = time.time() if now is None else now

        def _apply(accounts: dict) -> float:
            entry = accounts.get(key)
            entry = entry if isinstance(entry, dict) else {}
            tokens = entry.get("tokens")
            stamp = entry.get("tokens_at")
            if not isinstance(tokens, (int, float)) or not isinstance(stamp, (int, float)):
                tokens, stamp = float(self.bucket_capacity), current
            tokens = min(
                float(self.bucket_capacity),
                float(tokens) + max(0.0, current - float(stamp)) / self.refill_seconds,
            )
            tokens -= 1
            entry["tokens"] = tokens
            entry["tokens_at"] = current
            accounts[key] = entry
            return 0.0 if tokens >= 0 else -tokens * self.refill_seconds

        return self._mutate(_apply)

    # -- reporting -----------------------------------------------------------
    def snapshot(self, *, now: Optional[float] = None) -> list[dict]:
        current = time.time() if now is None else now
        rows = []
        for key, entry in sorted(self._read().items()):
            if not isinstance(entry, dict):
                continue
            remaining = self.cooldown_remaining(key, now=current)
            rows.append(
                {
                    "account": key,
                    "cooling_down": remaining > 0,
                    "cooldown_remaining_seconds": int(remaining),
                    "reason": entry.get("reason") if remaining > 0 else None,
                    "trips": int(entry.get("trips", 0) or 0),
                }
            )
        return rows

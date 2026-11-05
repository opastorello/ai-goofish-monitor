"""
Small operator CLI, modelled on goofish-cli's `auth` namespace.

  python -m src.cli auth status [--account NAME_OR_PATH]
  python -m src.cli auth reset-guard [--task TASK_NAME]

Both print JSON, so they are easy to script.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from src.failure_guard import FailureGuard
from src.infrastructure.config.env_manager import env_manager
from src.services.login_status_service import check_login_state


def _state_dir() -> str:
    return (env_manager.get_value("ACCOUNT_STATE_DIR", "state") or "state").strip().strip("\"'")


def _resolve_accounts(account: str | None) -> list[tuple[str, str]]:
    state_dir = _state_dir()
    if account:
        path = account if os.path.sep in account or account.endswith(".json") else os.path.join(state_dir, f"{account}.json")
        return [(os.path.splitext(os.path.basename(path))[0], path)]
    if not os.path.isdir(state_dir):
        return []
    return [
        (os.path.splitext(name)[0], os.path.join(state_dir, name))
        for name in sorted(os.listdir(state_dir))
        if name.endswith(".json")
    ]


def cmd_status(args) -> int:
    accounts = _resolve_accounts(args.account)
    if not accounts:
        print(json.dumps({"error": "no login state files found"}, ensure_ascii=False))
        return 1
    results = [{"name": name, **check_login_state(path)} for name, path in accounts]
    print(json.dumps(results[0] if len(results) == 1 else results, ensure_ascii=False, indent=2))
    return 0 if all(item["valid"] for item in results) else 2


def cmd_reset_guard(args) -> int:
    count = FailureGuard().reset(args.task)
    print(json.dumps({"ok": True, "reset": count}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.cli")
    namespaces = parser.add_subparsers(dest="namespace", required=True)
    auth = namespaces.add_parser("auth", help="login state and risk-control guard")
    commands = auth.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="check whether the saved login is still valid")
    status.add_argument("--account", help="account name or path to a state JSON (default: all accounts)")
    status.set_defaults(func=cmd_status)

    reset = commands.add_parser("reset-guard", help="manually lift the risk-control circuit breaker")
    reset.add_argument("--task", help="task name (default: every task)")
    reset.set_defaults(func=cmd_reset_guard)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

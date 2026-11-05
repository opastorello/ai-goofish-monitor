from datetime import datetime, timedelta, timezone

from src.failure_guard import FailureGuard


def _guard(tmp_path):
    return FailureGuard(str(tmp_path / "guard.json"), threshold=2, pause_seconds=3600, tz_name="UTC")


def test_snapshot_lists_paused_tasks(tmp_path):
    guard = _guard(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    guard.record_failure("a", reason="FAIL_SYS_USER_VALIDATE", now=now)
    guard.record_failure("a", reason="FAIL_SYS_USER_VALIDATE", now=now)
    guard.record_success("b", now=now)
    rows = {row["task_name"]: row for row in guard.snapshot(now=now + timedelta(minutes=1))}
    assert rows["a"]["paused"] is True and rows["a"]["consecutive_failures"] == 2
    assert rows["a"]["last_failure_reason"] == "FAIL_SYS_USER_VALIDATE"
    assert rows["b"]["paused"] is False and rows["b"]["last_success_at"]
    # the pause expires on its own
    assert {r["task_name"]: r for r in guard.snapshot(now=now + timedelta(hours=2))}["a"]["paused"] is False


def test_reset_one_task_or_all(tmp_path):
    guard = _guard(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for name in ("a", "b"):
        guard.record_failure(name, reason="x", now=now)
        guard.record_failure(name, reason="x", now=now)
    assert guard.reset("a") == 1
    rows = {row["task_name"]: row for row in guard.snapshot(now=now)}
    assert rows["a"]["paused"] is False and rows["a"]["consecutive_failures"] == 0
    assert rows["b"]["paused"] is True
    assert guard.reset() == 2
    assert all(not row["paused"] for row in guard.snapshot(now=now))
    assert guard.reset("missing") == 0


def test_cli_reset_guard_prints_json(tmp_path, monkeypatch, capsys):
    from src import cli

    path = tmp_path / "guard.json"
    monkeypatch.setenv("TASK_FAILURE_GUARD_PATH", str(path))
    monkeypatch.setenv("TASK_FAILURE_THRESHOLD", "1")
    FailureGuard().record_failure("a", reason="x")
    assert cli.main(["auth", "reset-guard", "--task", "a"]) == 0
    assert '"reset": 1' in capsys.readouterr().out
    assert cli.main(["auth", "reset-guard"]) == 0

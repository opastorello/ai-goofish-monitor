import pytest

from src.account_guard import AccountGuard, account_key


def _guard(tmp_path, **kwargs):
    kwargs.setdefault("cooldown_seconds", 600)
    kwargs.setdefault("bucket_capacity", 2)
    kwargs.setdefault("refill_seconds", 60)
    return AccountGuard(str(tmp_path / "guard.json"), **kwargs)


def test_account_key_uses_the_state_file_name():
    assert account_key("state/minhaconta.json") == "minhaconta"
    assert account_key("/x/y/acc_1.json") == "acc_1"
    assert account_key(None) == "default"


def test_trip_starts_a_cooldown_that_expires_by_itself(tmp_path):
    guard = _guard(tmp_path)
    assert guard.cooldown_remaining("a", now=1000) == 0
    guard.trip("a", "FAIL_SYS_USER_VALIDATE", now=1000)
    assert guard.cooldown_remaining("a", now=1100) == pytest.approx(500)
    assert guard.cooldown_remaining("b", now=1100) == 0  # other accounts are unaffected
    assert guard.cooldown_remaining("a", now=1700) == 0


def test_trip_again_extends_and_counts(tmp_path):
    guard = _guard(tmp_path)
    guard.trip("a", "x", now=0)
    guard.trip("a", "y", now=400)
    assert guard.cooldown_remaining("a", now=500) == pytest.approx(500)
    assert guard.snapshot(now=500)[0]["trips"] == 2


def test_reset_lifts_one_account_or_all(tmp_path):
    guard = _guard(tmp_path)
    guard.trip("a", "x", now=0)
    guard.trip("b", "x", now=0)
    assert guard.reset("a") == 1
    assert guard.cooldown_remaining("a", now=1) == 0
    assert guard.cooldown_remaining("b", now=1) > 0
    assert guard.reset() == 1
    assert guard.reset("missing") == 0
    assert all(not row["cooling_down"] for row in guard.snapshot(now=1))


def test_bucket_allows_a_burst_then_paces_visits(tmp_path):
    guard = _guard(tmp_path)  # capacity 2, one token per 60s
    assert guard.acquire_detail_slot("a", now=0) == 0
    assert guard.acquire_detail_slot("a", now=0) == 0
    assert guard.acquire_detail_slot("a", now=0) == pytest.approx(60)   # third must wait
    assert guard.acquire_detail_slot("a", now=0) == pytest.approx(120)  # reservations queue up
    # after enough idle time the bucket refills (and never exceeds its capacity)
    assert guard.acquire_detail_slot("a", now=10_000) == 0
    assert guard.acquire_detail_slot("a", now=10_000) == 0
    assert guard.acquire_detail_slot("a", now=10_000) > 0


def test_bucket_is_per_account(tmp_path):
    guard = _guard(tmp_path, bucket_capacity=1)
    assert guard.acquire_detail_slot("a", now=0) == 0
    assert guard.acquire_detail_slot("b", now=0) == 0
    assert guard.acquire_detail_slot("a", now=0) > 0


def test_state_persists_across_instances(tmp_path):
    _guard(tmp_path).trip("a", "x", now=0)
    assert _guard(tmp_path).cooldown_remaining("a", now=1) > 0

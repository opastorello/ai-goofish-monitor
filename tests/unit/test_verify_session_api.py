import json

from src.api.routes import accounts


def test_verify_status_idle_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(accounts, "VERIFY_STATUS_FILE", str(tmp_path / "missing.json"))
    assert accounts._read_verify_status() == {"status": "idle"}


def test_verify_status_stale_waiting_becomes_closed(tmp_path, monkeypatch):
    path = tmp_path / "verify.json"
    path.write_text(json.dumps({"status": "waiting", "account": "a"}), encoding="utf-8")
    monkeypatch.setattr(accounts, "VERIFY_STATUS_FILE", str(path))
    monkeypatch.setattr(accounts, "_verify_process", None)
    assert accounts._read_verify_status()["status"] == "closed"


def test_verify_status_keeps_final_state(tmp_path, monkeypatch):
    path = tmp_path / "verify.json"
    path.write_text(json.dumps({"status": "solved", "account": "a"}), encoding="utf-8")
    monkeypatch.setattr(accounts, "VERIFY_STATUS_FILE", str(path))
    assert accounts._read_verify_status()["status"] == "solved"

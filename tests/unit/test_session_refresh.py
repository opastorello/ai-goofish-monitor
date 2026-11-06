import json

import httpx

from src.session_refresh import refresh_session, token_expiry_seconds


def _write(path, cookies):
    path.write_text(json.dumps({"cookies": cookies, "origins": []}), encoding="utf-8")


def _cookie(name, value):
    return {"name": name, "value": value, "domain": ".goofish.com", "path": "/", "expires": -1,
            "httpOnly": False, "secure": True, "sameSite": "Lax"}


def test_token_expiry_parse():
    assert token_expiry_seconds([_cookie("_m_h5_tk", "abc_2000000")], now=1000) == 1000
    assert token_expiry_seconds([_cookie("other", "x")]) is None


def test_skips_when_token_still_fresh(tmp_path):
    path = tmp_path / "a.json"
    _write(path, [_cookie("cookie2", "c"), _cookie("_m_h5_tk", "abc_99999999999999")])
    report = refresh_session(str(path))
    assert not report["refreshed"] and "still valid" in report["reason"]


def test_refreshes_expired_token(tmp_path):
    path = tmp_path / "a.json"
    _write(path, [_cookie("cookie2", "c"), _cookie("_m_h5_tk", "old_1000")])

    def handler(request):
        return httpx.Response(200, json={"ret": ["SUCCESS"]},
                              headers=[("set-cookie", "_m_h5_tk=new_9999999999999; Path=/; Domain=goofish.com"),
                                       ("set-cookie", "_m_h5_tk_enc=enc; Path=/; Domain=goofish.com")])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    report = refresh_session(str(path), client=client)
    assert report["refreshed"]
    saved = {c["name"]: c["value"] for c in json.loads(path.read_text())["cookies"]}
    assert saved["_m_h5_tk"] == "new_9999999999999"
    assert saved["cookie2"] == "c"


def test_no_login_no_request(tmp_path):
    path = tmp_path / "a.json"
    _write(path, [_cookie("_m_h5_tk", "old_1000")])
    assert "no login" in refresh_session(str(path))["reason"]

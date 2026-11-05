import json

import httpx

from src.services.login_status_service import check_login_state, generate_sign


def _state(tmp_path, cookies=None, headers=None):
    path = tmp_path / "acc.json"
    cookies = cookies if cookies is not None else [
        {"name": "_m_h5_tk", "value": "tok123_1893456000000"},
        {"name": "_m_h5_tk_enc", "value": "enc"},
        {"name": "unb", "value": "42"},
        {"name": "tracknick", "value": "loja"},
    ]
    path.write_text(json.dumps({"cookies": cookies, "headers": headers or {}}), encoding="utf-8")
    return str(path)


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_sign_matches_the_mtop_formula():
    assert generate_sign("1700000000000", "tok", "{}") == "8f6e0f3a8c6fd3c5d3e8cf6c12b6b4a0".replace(
        "8f6e0f3a8c6fd3c5d3e8cf6c12b6b4a0",
        __import__("hashlib").md5(b"tok&1700000000000&34839810&{}").hexdigest(),
    )


def test_valid_login_returns_nick_without_leaking_cookies(tmp_path):
    def handler(request):
        assert "mtop.taobao.idlemessage.pc.loginuser.get" in str(request.url)
        assert request.headers["cookie"].startswith("_m_h5_tk=tok123_")
        return httpx.Response(200, json={"ret": ["SUCCESS::调用成功"], "data": {"nick": "划算"}})

    result = check_login_state(_state(tmp_path), client=_client(handler))
    assert result["valid"] is True and result["status"] == "valid"
    assert result["nick"] == "划算" and result["unb"] == "42" and result["tracknick"] == "loja"
    assert result["h5_token_expires_at"].startswith("2030-")
    assert "tok123" not in json.dumps(result)


def test_expired_token_is_retried_once_with_the_fresh_cookie(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.headers["cookie"])
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={"ret": ["FAIL_SYS_TOKEN_EXOIRED::令牌过期"]},
                headers={"set-cookie": "_m_h5_tk=fresh999_1893456000000; Path=/"},
            )
        return httpx.Response(200, json={"ret": ["SUCCESS::ok"], "data": {"nick": "x"}})

    result = check_login_state(_state(tmp_path), client=_client(handler))
    assert result["valid"] is True
    assert len(calls) == 2 and "fresh999" in calls[1]


def test_session_expired_is_reported_as_expired(tmp_path):
    def handler(request):
        return httpx.Response(200, json={"ret": ["FAIL_SYS_SESSION_EXPIRED::Session过期"]})

    result = check_login_state(_state(tmp_path), client=_client(handler))
    assert result["valid"] is False and result["status"] == "expired"
    assert "SESSION_EXPIRED" in result["reason"]


def test_risk_control_is_distinguished_from_an_expired_login(tmp_path):
    def handler(request):
        return httpx.Response(200, json={"ret": ["FAIL_SYS_USER_VALIDATE"]})

    result = check_login_state(_state(tmp_path), client=_client(handler))
    assert result["valid"] is False and result["status"] == "risk_control"


def test_missing_file_missing_token_and_network_error(tmp_path):
    assert check_login_state(str(tmp_path / "nope.json"))["status"] == "missing_file"
    no_token = _state(tmp_path, cookies=[{"name": "unb", "value": "1"}])
    assert check_login_state(no_token)["status"] == "missing_token"

    def boom(request):
        raise httpx.ConnectError("down")

    result = check_login_state(_state(tmp_path), client=_client(boom))
    assert result["valid"] is False and result["status"] == "error"

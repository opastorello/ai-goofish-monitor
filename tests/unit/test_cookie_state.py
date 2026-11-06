from src.cookie_state import normalize_state


def test_bare_cookie_list_becomes_playwright_state():
    state = normalize_state([
        {"name": "x5sec", "value": "v", "domain": "h5api.m.goofish.com", "expirationDate": 1793936062.5,
         "sameSite": "no_restriction", "secure": True, "storeId": "0"},
        {"name": "cookie2", "value": "c", "domain": ".goofish.com", "session": True},
        {"value": "no-name"},
    ])
    assert [c["name"] for c in state["cookies"]] == ["x5sec", "cookie2"]
    assert state["cookies"][0]["expires"] == 1793936062.5
    assert state["cookies"][0]["sameSite"] == "None"
    assert state["cookies"][1]["expires"] == -1
    assert "storeId" not in state["cookies"][0]


def test_dict_state_is_untouched():
    data = {"cookies": [], "origins": [], "env": {}}
    assert normalize_state(data) is data

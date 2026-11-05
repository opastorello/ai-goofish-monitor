import asyncio
import json
import os

from src.human_verification import (
    anti_bot_values,
    has_x5sec,
    merge_cookies,
    save_session_cookies,
    solved_by_cookies,
    wait_for_human_verification,
)

DETAIL = "h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail"


def _cookie(name, value, domain=".goofish.com", path="/"):
    return {"name": name, "value": value, "domain": domain, "path": path, "expires": -1,
            "httpOnly": False, "secure": True, "sameSite": "Lax"}


def test_merge_keeps_stored_cookies_and_lets_fresh_ones_win():
    existing = [_cookie("unb", "1"), _cookie("cookie2", "old")]
    merged = merge_cookies(existing, [_cookie("cookie2", "new"), _cookie("x5sec", "tok")])
    assert {c["name"]: c["value"] for c in merged} == {"unb": "1", "cookie2": "new", "x5sec": "tok"}
    assert [c["name"] for c in merged] == ["unb", "cookie2", "x5sec"]  # order is stable
    # same name on another domain is a different cookie
    assert len(merge_cookies([_cookie("a", "1")], [_cookie("a", "2", domain=".taobao.com")])) == 2


def test_solved_by_cookies_needs_a_new_or_changed_anti_bot_cookie():
    assert solved_by_cookies({}, [_cookie("x5sec", "tok")])
    assert not solved_by_cookies({"x5sec": "tok"}, [_cookie("x5sec", "tok")])      # unchanged
    assert solved_by_cookies({"x5sec": "tok"}, [_cookie("x5sec", "tok2")])         # refreshed
    assert not solved_by_cookies({}, [_cookie("unb", "1"), _cookie("x5sec", "")])  # empty / unrelated
    assert has_x5sec([_cookie("x5sec", "t")]) and not has_x5sec([_cookie("unb", "1")])
    assert anti_bot_values([_cookie("x5sec", "t"), _cookie("unb", "1")]) == {"x5sec": "t"}


def test_save_merges_into_the_state_file_and_keeps_everything_else(tmp_path):
    path = tmp_path / "acc.json"
    path.write_text(json.dumps({
        "cookies": [_cookie("unb", "1")],
        "headers": {"user-agent": "UA"},
        "env": {"locale": "zh-CN"},
    }), encoding="utf-8")
    os.chmod(path, 0o600)
    assert save_session_cookies(str(path), [_cookie("unb", "1"), _cookie("x5sec", "tok")]) is True
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert {c["name"] for c in saved["cookies"]} == {"unb", "x5sec"}
    assert saved["headers"] == {"user-agent": "UA"} and saved["env"] == {"locale": "zh-CN"}
    assert "cookiesRefreshedAt" in saved
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".tmp")]
    # nothing new -> untouched
    assert save_session_cookies(str(path), [_cookie("x5sec", "tok")]) is False


class FakeResponse:
    def __init__(self, url, body):
        self.url, self._body = url, body

    async def json(self):
        return self._body


class FakePage:
    def __init__(self):
        self.handlers, self.closed, self.fronted = [], False, False

    def on(self, _event, handler):
        self.handlers.append(handler)

    def remove_listener(self, _event, handler):
        self.handlers.remove(handler)

    async def bring_to_front(self):
        self.fronted = True

    def is_closed(self):
        return self.closed


class FakeContext:
    """cookies() returns the next scripted jar on every call (the last one repeats)."""

    def __init__(self, jars):
        self.jars = list(jars)

    async def cookies(self):
        return self.jars.pop(0) if len(self.jars) > 1 else self.jars[0]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds
        await asyncio.sleep(0)   # let other coroutines (a simulated person) run


def _state(tmp_path):
    path = tmp_path / "acc.json"
    path.write_text(json.dumps({"cookies": [_cookie("unb", "1")]}), encoding="utf-8")
    return str(path)


def _run(page, context, state, clock, timeout=30, log=None):
    return asyncio.run(wait_for_human_verification(
        page, context, state, timeout_seconds=timeout, detail_url_pattern=DETAIL,
        poll_seconds=2, log=log or (lambda _m: None), sleep=clock.sleep, clock=clock))


def test_waits_until_x5sec_appears_then_saves_the_session(tmp_path):
    state, clock, page = _state(tmp_path), FakeClock(), FakePage()
    jars = [[_cookie("unb", "1")], [_cookie("unb", "1")], [_cookie("unb", "1")],
            [_cookie("unb", "1"), _cookie("x5sec", "tok")]]
    messages = []
    assert _run(page, FakeContext(jars), state, clock, log=messages.append) is True
    assert page.fronted and not page.handlers          # window raised, listener removed
    assert "x5sec" in {c["name"] for c in json.loads(open(state, encoding="utf-8").read())["cookies"]}
    assert any("已保存" in m for m in messages) and any("x5sec" in m for m in messages)
    assert 0 < clock.now < 30                           # returned as soon as it was solved


def test_a_successful_replay_of_the_detail_request_also_counts(tmp_path):
    state, clock, page = _state(tmp_path), FakeClock(), FakePage()
    context = FakeContext([[_cookie("unb", "1")]])

    async def scenario():
        task = asyncio.create_task(wait_for_human_verification(
            page, context, state, timeout_seconds=30, detail_url_pattern=DETAIL,
            poll_seconds=2, log=lambda _m: None, sleep=clock.sleep, clock=clock))
        while not page.handlers:                      # wait until the listener is registered
            await asyncio.sleep(0)
        await page.handlers[0](FakeResponse("https://x/other", {"ret": ["SUCCESS::ok"]}))   # unrelated URL
        await page.handlers[0](FakeResponse(f"https://{DETAIL}/1.0/", {"ret": ["FAIL_SYS_USER_VALIDATE"]}))
        await asyncio.sleep(0)
        assert not task.done()                        # neither of those counts as solved
        await page.handlers[0](FakeResponse(f"https://{DETAIL}/1.0/", {"ret": ["SUCCESS::ok"]}))
        return await task

    assert asyncio.run(scenario()) is True


def test_times_out_when_nobody_solves_it(tmp_path):
    state, clock = _state(tmp_path), FakeClock()
    before = open(state, encoding="utf-8").read()
    assert _run(FakePage(), FakeContext([[_cookie("unb", "1")]]), state, clock, timeout=10) is False
    assert clock.now >= 10
    assert open(state, encoding="utf-8").read() == before   # nothing written


def test_stops_waiting_if_the_window_is_closed(tmp_path):
    page = FakePage()
    page.closed = True
    assert _run(page, FakeContext([[_cookie("unb", "1")]]), _state(tmp_path), FakeClock()) is False

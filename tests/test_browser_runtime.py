from pathlib import Path
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import SkillConfig
from modules.browser_runtime import BrowserRuntime


class _FakePage:
    def __init__(self) -> None:
        self.url = "https://www.taobao.com"
        self.timeout_value = None
        self.text_content = "欢迎来到淘宝"
        self.goto_calls = []
        self.fill_calls = []
        self.press_calls = []
        self.screenshot_calls = []

    def set_default_timeout(self, value: int) -> None:
        self.timeout_value = value

    def goto(self, url: str, wait_until: str, timeout: int) -> None:
        self.url = url
        self.goto_calls.append((url, wait_until, timeout))

    def fill(self, selector: str, keyword: str) -> None:
        self.fill_calls.append((selector, keyword))

    def press(self, selector: str, key: str) -> None:
        self.press_calls.append((selector, key))

    def content(self) -> str:
        return self.text_content

    def screenshot(self, path: str, full_page: bool) -> None:
        self.screenshot_calls.append((path, full_page))

    def close(self) -> None:
        return None


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self.page = page
        self.timeout_value = None

    def set_default_timeout(self, value: int) -> None:
        self.timeout_value = value

    def new_page(self) -> _FakePage:
        return self.page

    def close(self) -> None:
        return None


class _FakeBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self.context = context
        self.new_context_kwargs = None

    def new_context(self, **kwargs):
        self.new_context_kwargs = kwargs
        return self.context

    def close(self) -> None:
        return None


class _FakeChromium:
    def __init__(self, browser: _FakeBrowser) -> None:
        self.browser = browser
        self.launch_kwargs = None

    def launch(self, **kwargs) -> _FakeBrowser:
        self.launch_kwargs = kwargs
        return self.browser


class _FakePlaywright:
    def __init__(self, chromium: _FakeChromium) -> None:
        self.chromium = chromium
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _FakePlaywrightLauncher:
    def __init__(self, pw: _FakePlaywright) -> None:
        self.pw = pw

    def start(self) -> _FakePlaywright:
        return self.pw


def _make_runtime(tmp_path: Path):
    page = _FakePage()
    context = _FakeContext(page=page)
    browser = _FakeBrowser(context=context)
    chromium = _FakeChromium(browser=browser)
    fake_pw = _FakePlaywright(chromium=chromium)

    def fake_factory():
        return _FakePlaywrightLauncher(fake_pw)

    config = SkillConfig(storage_state_path=tmp_path / "storage_state.json")
    runtime = BrowserRuntime(config=config, playwright_factory=fake_factory)
    return runtime, fake_pw, chromium, browser, page


def test_start_uses_storage_state_when_exists(tmp_path: Path) -> None:
    runtime, _pw, _chromium, browser, _page = _make_runtime(tmp_path)
    runtime.config.storage_state_path.write_text('{"cookies":[],"origins":[]}', encoding="utf-8")

    runtime.start()

    assert browser.new_context_kwargs["storage_state"] == str(runtime.config.storage_state_path)


def test_search_keyword_invokes_fill_and_press(tmp_path: Path) -> None:
    runtime, _pw, _chromium, _browser, page = _make_runtime(tmp_path)
    runtime.start()

    runtime.search_keyword("蓝牙耳机")

    assert page.fill_calls == [("input[name='q']", "蓝牙耳机")]
    assert page.press_calls == [("input[name='q']", "Enter")]


def test_is_login_page_detects_login_hint(tmp_path: Path) -> None:
    runtime, _pw, _chromium, _browser, page = _make_runtime(tmp_path)
    runtime.start()
    page.url = "https://login.taobao.com/member/login.jhtml"

    assert runtime.is_login_page() is True


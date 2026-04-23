from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import SkillConfig
from modules.auth_manager import (
    AUTHENTICATED,
    CAPTCHA_DETECTED,
    LOGIN_REQUIRED,
    RISK_CONTROL_PAGE,
    AuthManager,
)


class _FakeRuntime:
    def __init__(
        self,
        *,
        login_page: bool,
        visible_text: str,
        page_url: str,
        page_title: str,
        storage_exists: bool,
        page_html: str = "",
    ):
        self._login_page = login_page
        self._visible_text = visible_text
        self._page_url = page_url
        self._page_title = page_title
        self._storage_exists = storage_exists
        self._page_html = page_html

    def is_login_page(self) -> bool:
        return self._login_page

    def get_visible_text(self) -> str:
        return self._visible_text

    def get_page_url(self) -> str:
        return self._page_url

    def get_page_title(self) -> str:
        return self._page_title

    def get_page_html(self) -> str:
        return self._page_html

    def has_storage_state(self) -> bool:
        return self._storage_exists


def test_need_login_true_and_login_page_returns_login_required() -> None:
    runtime = _FakeRuntime(
        login_page=True,
        visible_text="Please sign in",
        page_url="https://login.taobao.com",
        page_title="Taobao Login",
        storage_exists=True,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == LOGIN_REQUIRED


def test_captcha_page_returns_captcha_status() -> None:
    runtime = _FakeRuntime(
        login_page=False,
        visible_text="Please complete captcha",
        page_url="https://login.taobao.com",
        page_title="Security Check",
        storage_exists=True,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == CAPTCHA_DETECTED


def test_risk_control_page_returns_risk_control_status() -> None:
    runtime = _FakeRuntime(
        login_page=False,
        visible_text="Access restricted",
        page_url="https://sec.taobao.com/punish?x=1",
        page_title="Risk Control",
        storage_exists=True,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == RISK_CONTROL_PAGE


def test_need_login_false_skips_forcing_login() -> None:
    runtime = _FakeRuntime(
        login_page=True,
        visible_text="Please login",
        page_url="https://login.taobao.com",
        page_title="Taobao Login",
        storage_exists=False,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=False) == AUTHENTICATED


def test_html_keyword_alone_does_not_force_login() -> None:
    runtime = _FakeRuntime(
        login_page=False,
        visible_text="Welcome back",
        page_url="https://s.taobao.com/search?q=headset",
        page_title="Search Results",
        storage_exists=True,
        page_html="<html><body>please login keyword in html only</body></html>",
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == AUTHENTICATED

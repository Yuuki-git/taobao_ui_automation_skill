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
    def __init__(self, *, login_page: bool, page_text: str, page_url: str, storage_exists: bool):
        self._login_page = login_page
        self._page_text = page_text
        self._page_url = page_url
        self._storage_exists = storage_exists

    def is_login_page(self) -> bool:
        return self._login_page

    def get_page_text(self) -> str:
        return self._page_text

    def get_page_url(self) -> str:
        return self._page_url

    def has_storage_state(self) -> bool:
        return self._storage_exists


def test_need_login_true_and_login_page_returns_login_required() -> None:
    runtime = _FakeRuntime(
        login_page=True,
        page_text="请登录后继续",
        page_url="https://login.taobao.com",
        storage_exists=True,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == LOGIN_REQUIRED


def test_captcha_page_returns_captcha_status() -> None:
    runtime = _FakeRuntime(
        login_page=False,
        page_text="系统检测到异常，请输入验证码继续",
        page_url="https://login.taobao.com",
        storage_exists=True,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == CAPTCHA_DETECTED


def test_risk_control_page_returns_risk_control_status() -> None:
    runtime = _FakeRuntime(
        login_page=False,
        page_text="请稍后重试",
        page_url="https://sec.taobao.com/punish?x=1",
        storage_exists=True,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=True) == RISK_CONTROL_PAGE


def test_need_login_false_skips_forcing_login() -> None:
    runtime = _FakeRuntime(
        login_page=True,
        page_text="请登录",
        page_url="https://login.taobao.com",
        storage_exists=False,
    )
    manager = AuthManager(runtime=runtime, config=SkillConfig())

    assert manager.ensure_authenticated(need_login=False) == AUTHENTICATED


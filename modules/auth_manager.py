from __future__ import annotations

import logging
from typing import Any

from config import SkillConfig


AUTHENTICATED = "AUTHENTICATED"
LOGIN_REQUIRED = "LOGIN_REQUIRED"
CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
RISK_CONTROL_PAGE = "RISK_CONTROL_PAGE"


class AuthManager:
    """Determine authentication state without complex auto-login logic."""

    def __init__(self, *, runtime: Any, config: SkillConfig, task_id: str | None = None):
        self.runtime = runtime
        self.config = config
        self._logger = logging.LoggerAdapter(
            logging.getLogger(__name__), {"task_id": task_id or "-"}
        )

    def ensure_authenticated(self, *, need_login: bool) -> str:
        """Return one of AUTHENTICATED / LOGIN_REQUIRED / CAPTCHA_DETECTED / RISK_CONTROL_PAGE."""

        page_url = self._safe_lower(self.runtime.get_page_url())
        page_title = self._safe_lower(self._get_page_title())
        visible_text = self._safe_lower(self._get_visible_text())

        if self._is_captcha_signal(
            page_url=page_url, page_title=page_title, visible_text=visible_text
        ):
            return CAPTCHA_DETECTED

        if self._is_risk_control_signal(
            page_url=page_url, page_title=page_title, visible_text=visible_text
        ):
            return RISK_CONTROL_PAGE

        if not need_login:
            return AUTHENTICATED

        if self._is_login_required_signal(
            page_url=page_url, page_title=page_title, visible_text=visible_text
        ):
            return LOGIN_REQUIRED

        if self.runtime.is_login_page():
            return LOGIN_REQUIRED

        if not self.runtime.has_storage_state():
            self._logger.info("Storage state missing while login is required.")
            return LOGIN_REQUIRED

        return AUTHENTICATED

    def _get_visible_text(self) -> str:
        if hasattr(self.runtime, "get_visible_text"):
            return str(self.runtime.get_visible_text() or "")
        if hasattr(self.runtime, "get_page_text"):
            # Compatibility path for older runtime implementations.
            return str(self.runtime.get_page_text() or "")
        return ""

    def _get_page_title(self) -> str:
        if hasattr(self.runtime, "get_page_title"):
            return str(self.runtime.get_page_title() or "")
        return ""

    @staticmethod
    def _safe_lower(value: str) -> str:
        return value.lower() if isinstance(value, str) else ""

    @staticmethod
    def _is_login_required_signal(
        *, page_url: str, page_title: str, visible_text: str
    ) -> bool:
        login_url_tokens = (
            "login.taobao.com",
            "member/login",
            "login.jhtml",
            "passport.taobao.com",
        )
        login_title_tokens = (
            "taobao account login",
            "taobao sign in",
            "account login",
            "sms login",
            "扫码登录",
            "账户登录",
            "短信登录",
            "会员登录",
        )
        login_text_tokens = (
            "please sign in to continue",
            "sign in to continue",
            "account login",
            "sms login",
            "scan qr to login",
            "请登录后继续",
            "请先登录",
            "账户登录",
            "短信登录",
            "扫码登录",
            "重新登录",
        )
        return (
            any(token in page_url for token in login_url_tokens)
            or any(token in page_title for token in login_title_tokens)
            or any(token in visible_text for token in login_text_tokens)
        )

    @staticmethod
    def _is_captcha_signal(*, page_url: str, page_title: str, visible_text: str) -> bool:
        tokens = (
            "captcha",
            "slider verify",
            "security verification",
            "验证码",
            "滑块验证",
            "安全验证",
        )
        return any(
            token in page_url or token in page_title or token in visible_text
            for token in tokens
        )

    @staticmethod
    def _is_risk_control_signal(
        *, page_url: str, page_title: str, visible_text: str
    ) -> bool:
        tokens = (
            "sec.taobao.com/punish",
            "risk control",
            "访问受限",
            "风控",
            "异常访问",
            "账号风险",
        )
        return any(
            token in page_url or token in page_title or token in visible_text
            for token in tokens
        )

from __future__ import annotations

import logging
from typing import Any

from config import SkillConfig


AUTHENTICATED = "AUTHENTICATED"
LOGIN_REQUIRED = "LOGIN_REQUIRED"
CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
RISK_CONTROL_PAGE = "RISK_CONTROL_PAGE"


class AuthManager:
    """Determine authentication state without performing complex auto-login."""

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

        if self._is_captcha(page_url=page_url, page_title=page_title, visible_text=visible_text):
            return CAPTCHA_DETECTED

        if self._is_risk_control(
            page_url=page_url, page_title=page_title, visible_text=visible_text
        ):
            return RISK_CONTROL_PAGE

        if not need_login:
            return AUTHENTICATED

        if self.runtime.is_login_page() or self._has_login_hints(
            page_url=page_url, page_title=page_title, visible_text=visible_text
        ):
            return LOGIN_REQUIRED

        if not self.runtime.has_storage_state():
            self._logger.info("Storage state is missing while login is required.")
            return LOGIN_REQUIRED

        return AUTHENTICATED

    def _get_visible_text(self) -> str:
        if hasattr(self.runtime, "get_visible_text"):
            return str(self.runtime.get_visible_text() or "")
        # Backward compatibility for legacy runtime methods.
        if hasattr(self.runtime, "get_page_text"):
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
    def _has_login_hints(*, page_url: str, page_title: str, visible_text: str) -> bool:
        hints = (
            "login",
            "sign in",
            "account login",
            "sms login",
            "请登录",
            "账户登录",
            "验证码登录",
        )
        return any(
            hint in page_url or hint in page_title or hint in visible_text for hint in hints
        )

    @staticmethod
    def _is_captcha(*, page_url: str, page_title: str, visible_text: str) -> bool:
        hints = ("captcha", "verification", "验证码", "安全验证", "滑块")
        return any(
            hint in page_url or hint in page_title or hint in visible_text for hint in hints
        )

    @staticmethod
    def _is_risk_control(*, page_url: str, page_title: str, visible_text: str) -> bool:
        hints = ("risk", "punish", "风控", "访问受限", "异常访问")
        return any(
            hint in page_url or hint in page_title or hint in visible_text for hint in hints
        )

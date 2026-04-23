from __future__ import annotations

import logging
from typing import Any

from config import SkillConfig


AUTHENTICATED = "AUTHENTICATED"
LOGIN_REQUIRED = "LOGIN_REQUIRED"
CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
RISK_CONTROL_PAGE = "RISK_CONTROL_PAGE"


class AuthManager:
    """Check login-related states using lightweight runtime signals."""

    def __init__(self, *, runtime: Any, config: SkillConfig, task_id: str | None = None):
        self.runtime = runtime
        self.config = config
        self._logger = logging.LoggerAdapter(
            logging.getLogger(__name__), {"task_id": task_id or "-"}
        )

    def ensure_authenticated(self, *, need_login: bool) -> str:
        """Return login status without trying to perform full auto-login."""

        page_url = self.runtime.get_page_url().lower()
        page_text = self.runtime.get_page_text().lower()

        if self._is_captcha(page_url=page_url, page_text=page_text):
            return CAPTCHA_DETECTED

        if self._is_risk_control(page_url=page_url, page_text=page_text):
            return RISK_CONTROL_PAGE

        if not need_login:
            return AUTHENTICATED

        if self.runtime.is_login_page():
            return LOGIN_REQUIRED

        if not self.runtime.has_storage_state():
            self._logger.info("Storage state missing while login is required.")
            return LOGIN_REQUIRED

        if any(token in page_text for token in ("请登录", "登录后", "重新登录")):
            return LOGIN_REQUIRED

        return AUTHENTICATED

    @staticmethod
    def _is_captcha(*, page_url: str, page_text: str) -> bool:
        return any(
            token in page_url or token in page_text
            for token in ("captcha", "验证码", "滑块", "安全验证")
        )

    @staticmethod
    def _is_risk_control(*, page_url: str, page_text: str) -> bool:
        return any(
            token in page_url or token in page_text
            for token in ("punish", "risk", "风控", "访问受限", "异常访问")
        )

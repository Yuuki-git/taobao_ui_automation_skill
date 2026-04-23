from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import SkillConfig
from modules.error_codes import NETWORK_ERROR, PAGE_STRUCTURE_CHANGED, SEARCH_TIMEOUT, SkillError


SEARCH_INPUT_SELECTOR = "input[name='q']"


class BrowserRuntime:
    """Wrap Playwright lifecycle and common Taobao page operations."""

    def __init__(
        self,
        *,
        config: SkillConfig,
        playwright_factory: Callable[[], Any] = sync_playwright,
        task_id: str | None = None,
    ) -> None:
        self.config = config
        self._playwright_factory = playwright_factory
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._logger = logging.LoggerAdapter(
            logging.getLogger(__name__), {"task_id": task_id or "-"}
        )

    def has_storage_state(self) -> bool:
        """Return whether storage state file exists and contains data."""

        path = Path(self.config.storage_state_path)
        return path.exists() and path.is_file() and path.stat().st_size > 0

    def start(self) -> None:
        """Start Playwright, browser, context, and page."""

        if self._page is not None:
            return

        launcher = self._playwright_factory()
        self._playwright = launcher.start()
        self._browser = self._playwright.chromium.launch(
            headless=self.config.default_headless
        )

        context_kwargs = {}
        if self.has_storage_state():
            context_kwargs["storage_state"] = str(self.config.storage_state_path)

        # Optional flag only. We intentionally do not require any stealth plugin.
        if self.config.enable_stealth:
            self._logger.info(
                "Stealth flag is enabled but no stealth dependency is enforced in phase-2."
            )

        self._context = self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(self.config.default_timeout_ms)
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.config.default_timeout_ms)
        self._logger.info("Browser runtime started.")

    def close(self) -> None:
        """Close page/context/browser/playwright safely."""

        errors: list[str] = []

        for obj_name, close_fn in (
            ("page", getattr(self._page, "close", None)),
            ("context", getattr(self._context, "close", None)),
            ("browser", getattr(self._browser, "close", None)),
            ("playwright", getattr(self._playwright, "stop", None)),
        ):
            if close_fn is None:
                continue
            try:
                close_fn()
            except Exception as exc:  # pragma: no cover - defensive cleanup
                errors.append(f"{obj_name}:{exc}")

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

        if errors:
            self._logger.warning("Runtime close had issues: %s", "; ".join(errors))
        else:
            self._logger.info("Browser runtime closed.")

    def goto(self, url: str) -> None:
        """Navigate to target URL with timeout handling."""

        page = self._require_page()
        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.config.default_timeout_ms,
            )
        except PlaywrightTimeoutError as exc:
            raise SkillError(
                NETWORK_ERROR,
                "Page navigation timed out.",
                {"url": url, "timeout_ms": self.config.default_timeout_ms},
            ) from exc

    def open_taobao_home(self) -> None:
        """Open Taobao home page."""

        self.goto(self.config.taobao_home_url)

    def search_keyword(self, keyword: str) -> None:
        """Fill keyword in search input and submit."""

        page = self._require_page()
        try:
            page.fill(SEARCH_INPUT_SELECTOR, keyword)
            page.press(SEARCH_INPUT_SELECTOR, "Enter")
        except PlaywrightTimeoutError as exc:
            raise SkillError(
                SEARCH_TIMEOUT,
                "Search operation timed out.",
                {"keyword": keyword, "timeout_ms": self.config.default_timeout_ms},
            ) from exc
        except Exception as exc:
            raise SkillError(
                PAGE_STRUCTURE_CHANGED,
                "Search input selector is not available on current page.",
                {"selector": SEARCH_INPUT_SELECTOR},
            ) from exc

    def get_page_text(self) -> str:
        """Return current page HTML text for lightweight rule checks."""

        page = self._require_page()
        return page.content()

    def get_page_url(self) -> str:
        """Return current page URL."""

        page = self._require_page()
        return str(getattr(page, "url", "") or "")

    def screenshot(self, path: str) -> None:
        """Capture a full-page screenshot."""

        page = self._require_page()
        page.screenshot(path=path, full_page=True)

    def is_login_page(self) -> bool:
        """Detect login page from URL or page text hints."""

        url = self.get_page_url().lower()
        if any(token in url for token in ("login.taobao.com", "member/login", "login.jhtml")):
            return True

        page_text = self.get_page_text().lower()
        return any(token in page_text for token in ("请登录", "login", "账户登录", "验证码登录"))

    def _require_page(self) -> Any:
        if self._page is None:
            raise SkillError(
                NETWORK_ERROR, "Browser runtime is not started. Call start() first."
            )
        return self._page

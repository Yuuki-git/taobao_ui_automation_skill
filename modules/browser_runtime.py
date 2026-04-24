from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import SkillConfig
from modules.error_codes import (
    CAPTCHA_DETECTED,
    NETWORK_ERROR,
    PAGE_STRUCTURE_CHANGED,
    RISK_CONTROL_PAGE,
    SEARCH_TIMEOUT,
    SkillError,
)
from modules.selectors import SEARCH_INPUT_SELECTOR


_SEARCH_READY_WAIT_JS = """
() => {
  const href = window.location.href.toLowerCase();
  const urlReady = href.includes("search") || href.includes("q=");
  const hasResultContainer = Boolean(
    document.querySelector(".m-itemlist, .items, .tb-item, [data-index], .ctx-box")
  );
  const hasNoResultState = Boolean(
    document.querySelector(".no-result, .empty, .none, [class*='no-result'], [class*='empty']")
  );
  const hasSearchResultHint = /search|result|找到|相关商品|没有找到/i.test(
    document.body ? document.body.innerText : ""
  );
  return urlReady && (hasResultContainer || hasNoResultState || hasSearchResultHint);
}
"""

_CAPTCHA_TOKENS = (
    "请拖动下方滑块完成验证",
    "拖动滑块",
    "滑块完成验证",
    "安全验证",
    "验证失败",
    "验证码",
    "captcha",
    "verify",
)

_RISK_CONTROL_TOKENS = (
    "punish",
    "risk",
    "异常访问",
    "访问受限",
    "风控",
)


class BrowserRuntime:
    """Playwright runtime wrapper for lifecycle and basic page operations."""

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
        """Return whether storage-state file exists and has content."""

        path = Path(self.config.storage_state_path)
        return path.exists() and path.is_file() and path.stat().st_size > 0

    def start(self) -> None:
        """Start Playwright and initialize browser context/page."""

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

        # Optional toggle only; no stealth dependency is required.
        if self.config.enable_stealth:
            self._logger.info(
                "Stealth toggle is enabled, but stealth plugin is not required in this version."
            )

        self._context = self._browser.new_context(**context_kwargs)
        self._context.set_default_timeout(self.config.default_timeout_ms)
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.config.default_timeout_ms)
        self._logger.info("Browser runtime started.")

    def close(self) -> None:
        """Close page/context/browser/playwright safely."""

        for close_fn in (
            getattr(self._page, "close", None),
            getattr(self._context, "close", None),
            getattr(self._browser, "close", None),
            getattr(self._playwright, "stop", None),
        ):
            if close_fn is None:
                continue
            try:
                close_fn()
            except Exception:  # pragma: no cover - defensive cleanup
                pass

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def goto(self, url: str) -> None:
        """Navigate to URL and wait for DOM readiness."""

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
        """Open Taobao homepage."""

        self.goto(self.config.taobao_home_url)

    def search_keyword(self, keyword: str) -> None:
        """Submit keyword search and wait for result page readiness."""

        page = self._require_page()
        try:
            page.fill(SEARCH_INPUT_SELECTOR, keyword)
            page.press(SEARCH_INPUT_SELECTOR, "Enter")
            self.wait_for_search_results_ready()
        except PlaywrightTimeoutError as exc:
            raise SkillError(
                SEARCH_TIMEOUT,
                "Search operation timed out.",
                {"keyword": keyword, "timeout_ms": self.config.default_timeout_ms},
            ) from exc
        except SkillError:
            raise
        except Exception as exc:
            raise SkillError(
                PAGE_STRUCTURE_CHANGED,
                "Search input selector is unavailable on current page.",
                {"selector": SEARCH_INPUT_SELECTOR},
            ) from exc

    def wait_for_search_results_ready(self) -> None:
        """Wait until search results page is ready for parser consumption."""

        page = self._require_page()
        timeout = self.config.default_timeout_ms
        check_timeout_ms = 600
        deadline = time.monotonic() + (timeout / 1000)

        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            while True:
                blocking_error = self._detect_search_blocking_error()
                if blocking_error is not None:
                    raise blocking_error

                remaining_ms = int((deadline - time.monotonic()) * 1000)
                if remaining_ms <= 0:
                    break

                try:
                    page.wait_for_function(
                        _SEARCH_READY_WAIT_JS,
                        timeout=min(check_timeout_ms, remaining_ms),
                    )
                    return
                except PlaywrightTimeoutError:
                    # Keep polling in small windows so captcha/risk pages
                    # can be surfaced quickly instead of generic timeout.
                    continue
        except PlaywrightTimeoutError as exc:
            raise SkillError(
                SEARCH_TIMEOUT,
                "Search results page is not ready before timeout.",
                {
                    "timeout_ms": timeout,
                    "stage": "SEARCH_PRODUCT",
                    "current_url": self.get_page_url(),
                },
            ) from exc

        blocking_error = self._detect_search_blocking_error()
        if blocking_error is not None:
            raise blocking_error

        raise SkillError(
            SEARCH_TIMEOUT,
            "Search results page is not ready before timeout.",
            {
                "timeout_ms": timeout,
                "stage": "SEARCH_PRODUCT",
                "current_url": self.get_page_url(),
            },
        )

    def get_page_html(self) -> str:
        """Return full page HTML."""

        page = self._require_page()
        return page.content()

    def get_visible_text(self) -> str:
        """Return visible body text only."""

        page = self._require_page()
        return page.inner_text("body")

    def get_page_text(self) -> str:
        """Backward-compatible alias for visible text."""

        return self.get_visible_text()

    def get_page_title(self) -> str:
        """Return current page title."""

        page = self._require_page()
        return page.title()

    def get_page_url(self) -> str:
        """Return current page URL."""

        page = self._require_page()
        return str(getattr(page, "url", "") or "")

    def get_page(self) -> Any | None:
        """Return current page if runtime is started, otherwise None."""

        return self._page

    def require_page(self) -> Any:
        """Return current page and raise if runtime is not started."""

        return self._require_page()

    def screenshot(self, path: str) -> None:
        """Capture full-page screenshot."""

        page = self._require_page()
        page.screenshot(path=path, full_page=True)

    def is_login_page(self) -> bool:
        """Detect login page by URL, title, and visible text hints."""

        url = self.get_page_url().lower()
        if any(token in url for token in ("login.taobao.com", "member/login", "login.jhtml")):
            return True

        title = self.get_page_title().lower()
        text = self.get_visible_text().lower()
        return any(
            token in title or token in text
            for token in (
                "account login",
                "sms login",
                "scan login",
                "please sign in",
                "taobao login",
                "请登录",
                "账户登录",
                "短信登录",
                "扫码登录",
            )
        )

    def _detect_search_blocking_error(self) -> SkillError | None:
        """Detect CAPTCHA/risk pages while waiting for search results."""

        page_url = self._safe_lower(self.get_page_url())
        page_title = self._safe_lower(self.get_page_title())
        visible_text = self._safe_lower(self.get_visible_text())

        risk_match = self._find_signal_match(
            sources=(("url", page_url), ("visible_text", visible_text), ("title", page_title)),
            tokens=_RISK_CONTROL_TOKENS,
        )
        if risk_match is not None:
            source_name, token = risk_match
            return SkillError(
                RISK_CONTROL_PAGE,
                "Risk control page detected during search.",
                {
                    "stage": "SEARCH_PRODUCT",
                    "current_url": self.get_page_url(),
                    "detection_source": f"{source_name}:{token}",
                },
            )

        captcha_match = self._find_signal_match(
            sources=(("url", page_url), ("title", page_title), ("visible_text", visible_text)),
            tokens=_CAPTCHA_TOKENS,
        )
        if captcha_match is not None:
            source_name, token = captcha_match
            return SkillError(
                CAPTCHA_DETECTED,
                "Captcha challenge detected during search.",
                {
                    "stage": "SEARCH_PRODUCT",
                    "current_url": self.get_page_url(),
                    "detection_source": f"{source_name}:{token}",
                },
            )

        return None

    @staticmethod
    def _find_signal_match(
        *,
        sources: tuple[tuple[str, str], ...],
        tokens: tuple[str, ...],
    ) -> tuple[str, str] | None:
        for source_name, source_value in sources:
            if not source_value:
                continue
            for token in tokens:
                if token in source_value:
                    return source_name, token
        return None

    @staticmethod
    def _safe_lower(value: str) -> str:
        return value.lower() if isinstance(value, str) else ""

    def _require_page(self) -> Any:
        if self._page is None:
            raise SkillError(
                NETWORK_ERROR, "Browser runtime is not started. Call start() first."
            )
        return self._page

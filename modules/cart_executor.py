from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from models import ProductCandidate
from modules.error_codes import ADD_CART_FAILED, SKU_SELECTION_REQUIRED
from modules.selectors import (
    ADD_TO_CART_SELECTORS,
    ADD_TO_CART_SUCCESS_SELECTORS,
    SKU_HINT_SELECTORS,
)


@dataclass
class CartExecutor:
    """Execute minimal add-to-cart flow for a selected product."""

    runtime: Any
    config: Any
    task_id: str | None = None

    def add_to_cart(self, product: ProductCandidate) -> dict[str, Any]:
        """Try add-to-cart and return a structured execution result."""

        if self.runtime is None:
            return self._failed(
                ADD_CART_FAILED,
                "Runtime is not available for add-to-cart.",
                {"reason": "runtime_missing"},
            )

        if product.product_url:
            try:
                self.runtime.goto(product.product_url)
            except Exception as exc:
                return self._failed(
                    ADD_CART_FAILED,
                    "Failed to open product detail page.",
                    {"reason": "goto_failed", "exception": str(exc)},
                )

        page = self._get_page()
        if page is None:
            return self._failed(
                ADD_CART_FAILED,
                "Page is not available for add-to-cart.",
                {"reason": "page_missing"},
            )

        if self._requires_manual_sku_selection(page):
            return self._failed(
                SKU_SELECTION_REQUIRED,
                "SKU selection requires manual intervention.",
                {"reason": "sku_selection_required"},
            )

        button = self._find_add_to_cart_button(page)
        if button is None:
            return self._failed(
                ADD_CART_FAILED,
                "Add-to-cart button was not found.",
                {"reason": "button_not_found"},
            )

        try:
            button.click()
        except Exception as exc:
            return self._failed(
                ADD_CART_FAILED,
                "Failed to click add-to-cart button.",
                {"reason": "button_click_failed", "exception": str(exc)},
            )

        if self._confirm_success_after_click(page):
            return {
                "success": True,
                "message": "Product added to cart successfully.",
                "error_code": None,
                "error_detail": None,
            }

        return self._failed(
            ADD_CART_FAILED,
            "Add-to-cart could not be confirmed.",
            {"reason": "success_not_confirmed"},
        )

    def _confirm_success_after_click(self, page: Any) -> bool:
        """Poll success signals briefly after click to reduce premature failure."""

        attempts = 4
        sleep_seconds = 0.15
        for idx in range(attempts):
            if self._has_success_signal(page):
                return True
            if idx < attempts - 1:
                time.sleep(sleep_seconds)
        return False

    def _get_page(self) -> Any | None:
        if hasattr(self.runtime, "require_page"):
            try:
                return self.runtime.require_page()
            except Exception:
                return None
        if hasattr(self.runtime, "get_page"):
            try:
                return self.runtime.get_page()
            except Exception:
                return None
        return None

    def _requires_manual_sku_selection(self, page: Any) -> bool:
        text = self._safe_page_text(page).lower()
        sku_prompt_tokens = (
            "请选择",
            "选择规格",
            "选择颜色",
            "选择尺码",
            "select size",
            "select color",
            "select model",
            "choose options",
        )
        if any(token in text for token in sku_prompt_tokens):
            return True

        for selector in SKU_HINT_SELECTORS:
            if self._locator_has_any(page, selector):
                if "sku" in text or "规格" in text:
                    return True
        return False

    def _find_add_to_cart_button(self, page: Any) -> Any | None:
        for selector in ADD_TO_CART_SELECTORS:
            elements = self._safe_locator_all(page, selector)
            if elements:
                return elements[0]
        return None

    def _has_success_signal(self, page: Any) -> bool:
        text = self._safe_page_text(page).lower()
        success_text_tokens = (
            "已加入购物车",
            "加入购物车成功",
            "成功加入购物车",
            "added to cart",
            "added to your cart",
        )
        if any(token in text for token in success_text_tokens):
            return True

        for selector in ADD_TO_CART_SUCCESS_SELECTORS:
            if self._locator_has_any(page, selector):
                return True

        if hasattr(self.runtime, "get_page_url"):
            url = str(self.runtime.get_page_url() or "").lower()
            if "cart" in url:
                return True
        return False

    def _safe_page_text(self, page: Any) -> str:
        if hasattr(self.runtime, "get_visible_text"):
            try:
                return str(self.runtime.get_visible_text() or "")
            except Exception:
                pass
        try:
            return str(page.inner_text("body") or "")
        except Exception:
            return ""

    def _safe_locator_all(self, page: Any, selector: str) -> list[Any]:
        try:
            return list(page.locator(selector).all())
        except Exception:
            return []

    def _locator_has_any(self, page: Any, selector: str) -> bool:
        return bool(self._safe_locator_all(page, selector))

    def _failed(self, code: str, message: str, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": False,
            "message": message,
            "error_code": code,
            "error_detail": detail,
        }

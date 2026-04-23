from __future__ import annotations

from typing import Any, Callable

from models import SkillResult, TaskPayload
from modules.auth_manager import (
    AUTHENTICATED,
    CAPTCHA_DETECTED,
    LOGIN_REQUIRED,
    RISK_CONTROL_PAGE,
    AuthManager,
)
from modules.browser_runtime import BrowserRuntime
from modules.error_codes import (
    ADD_CART_FAILED,
    CAPTCHA_DETECTED as CAPTCHA_DETECTED_CODE,
    LOGIN_REQUIRED as LOGIN_REQUIRED_CODE,
    NO_MATCHED_PRODUCT,
    RISK_CONTROL_PAGE as RISK_CONTROL_PAGE_CODE,
    SKU_SELECTION_REQUIRED,
    UNKNOWN_ERROR,
    SkillError,
)
from modules.notifier import Notifier
from modules.product_parser import ProductParser


class Orchestrator:
    """Main flow coordinator.

    Keep this layer focused on orchestration and delegate page details to modules.
    """

    def __init__(
        self,
        config: Any,
        *,
        runtime_factory: Callable[..., Any] = BrowserRuntime,
        auth_manager_factory: Callable[..., Any] = AuthManager,
        product_parser_factory: Callable[..., Any] | None = None,
        cart_executor_factory: Callable[..., Any] | None = None,
        notifier_factory: Callable[..., Any] = Notifier,
    ) -> None:
        self.config = config
        self.runtime_factory = runtime_factory
        self.auth_manager_factory = auth_manager_factory
        self.product_parser_factory = product_parser_factory or ProductParser
        self.cart_executor_factory = cart_executor_factory or _DefaultCartExecutor
        self.notifier_factory = notifier_factory

    def run(self, payload: TaskPayload) -> SkillResult:
        """Execute the end-to-end flow with structured error propagation."""

        runtime = _call_factory(
            self.runtime_factory, config=self.config, task_id=payload.task_id
        )
        notifier = _call_factory(self.notifier_factory, task_id=payload.task_id)

        try:
            runtime.start()
            runtime.open_taobao_home()

            auth_manager = _call_factory(
                self.auth_manager_factory,
                runtime=runtime, config=self.config, task_id=payload.task_id
            )
            auth_status = auth_manager.ensure_authenticated(need_login=payload.need_login)
            self._raise_if_auth_not_ready(auth_status)

            runtime.search_keyword(payload.keyword)

            product_parser = _call_factory(
                self.product_parser_factory,
                runtime=runtime, config=self.config, task_id=payload.task_id
            )
            candidates = product_parser.extract_candidates(
                max_candidates=payload.max_candidates
            )
            selected = product_parser.select_best_candidate(
                candidates,
                payload.keyword,
                payload.constraints,
            )

            if selected is None:
                result = SkillResult.from_error(
                    NO_MATCHED_PRODUCT,
                    "No product matched the provided constraints.",
                    task_status="failed",
                )
                notifier.notify_failure(
                    NO_MATCHED_PRODUCT, result.message, {"action": payload.action}
                )
                return result

            if payload.action == "search_only":
                result = SkillResult(
                    success=True,
                    task_status="completed",
                    selected_product=selected,
                    message="Task completed in search-only mode.",
                    error_code=None,
                    error_detail=None,
                )
                notifier.notify_success(result)
                return result

            cart_executor = _call_factory(
                self.cart_executor_factory,
                runtime=runtime, config=self.config, task_id=payload.task_id
            )
            cart_result = cart_executor.add_to_cart(selected)
            self._validate_cart_result(cart_result)

            if not cart_result.get("success"):
                raise SkillError(
                    str(cart_result.get("error_code") or ADD_CART_FAILED),
                    str(cart_result.get("message") or "Failed to add product to cart."),
                    _detail_to_dict(cart_result.get("detail")),
                )

            result = SkillResult(
                success=True,
                task_status="completed",
                selected_product=selected,
                message="Task completed and product added to cart.",
                error_code=None,
                error_detail=None,
            )
            notifier.notify_success(result)
            return result
        except SkillError as exc:
            notifier.notify_failure(exc.code, exc.message, exc.detail)
            raise
        except Exception as exc:
            notifier.notify_failure(
                UNKNOWN_ERROR,
                "Unexpected error in orchestrator.",
                {"exception_type": type(exc).__name__, "exception": str(exc)},
            )
            raise SkillError(
                UNKNOWN_ERROR,
                "Unexpected error in orchestrator.",
                {"exception_type": type(exc).__name__, "exception": str(exc)},
            ) from exc
        finally:
            runtime.close()

    @staticmethod
    def _raise_if_auth_not_ready(status: str) -> None:
        if status == AUTHENTICATED:
            return
        if status == LOGIN_REQUIRED:
            raise SkillError(
                LOGIN_REQUIRED_CODE,
                "Login is required for this task.",
                {"auth_status": status},
            )
        if status == CAPTCHA_DETECTED:
            raise SkillError(
                CAPTCHA_DETECTED_CODE,
                "Captcha challenge detected.",
                {"auth_status": status},
            )
        if status == RISK_CONTROL_PAGE:
            raise SkillError(
                RISK_CONTROL_PAGE_CODE,
                "Risk control page detected.",
                {"auth_status": status},
            )
        raise SkillError(
            UNKNOWN_ERROR,
            "Unknown authentication status received.",
            {"auth_status": status},
        )

    @staticmethod
    def _validate_cart_result(cart_result: Any) -> None:
        if not isinstance(cart_result, dict):
            raise SkillError(
                ADD_CART_FAILED,
                "add_to_cart must return a dictionary result.",
                {"result_type": type(cart_result).__name__},
            )
        if "success" not in cart_result:
            raise SkillError(
                ADD_CART_FAILED,
                "add_to_cart result must include success field.",
                {"result_keys": sorted(cart_result.keys())},
            )


class _DefaultCartExecutor:
    """Phase-2 placeholder.

    TODO(phase-3): replace with modules.cart_executor implementation.
    """

    def __init__(self, *, runtime: Any, config: Any, task_id: str | None = None):
        self.runtime = runtime
        self.config = config
        self.task_id = task_id

    def add_to_cart(self, product: Any) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": SKU_SELECTION_REQUIRED,
            "message": "SKU selection requires human intervention in current version.",
            "detail": {"phase": "phase-3", "product_title": getattr(product, "title", None)},
        }


def _detail_to_dict(detail: Any) -> dict[str, Any] | None:
    if detail is None:
        return None
    if isinstance(detail, dict):
        return detail
    return {"detail": detail}


def _call_factory(factory: Callable[..., Any], **kwargs: Any) -> Any:
    """Call factory with task_id when supported, otherwise fallback gracefully."""

    try:
        return factory(**kwargs)
    except TypeError as exc:
        if "task_id" not in kwargs:
            raise
        if "task_id" not in str(exc):
            raise
        fallback_kwargs = dict(kwargs)
        fallback_kwargs.pop("task_id", None)
        return factory(**fallback_kwargs)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4

from modules.error_codes import INVALID_INPUT, SkillError


ALLOWED_ACTIONS = {"search_only", "add_to_cart"}
ALLOWED_TASK_STATUS = {"completed", "failed", "need_human_intervention", "partial_success"}


def _require_dict(value: Any, field_name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise SkillError(INVALID_INPUT, f"{field_name} must be an object.")
    return value


def _to_optional_float(value: Any, field_name: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SkillError(INVALID_INPUT, f"{field_name} must be a number.")
    return float(value)


def _to_optional_int(value: Any, field_name: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise SkillError(INVALID_INPUT, f"{field_name} must be an integer.")
    return value


@dataclass
class Constraints:
    """Structured search constraints from task input."""

    positive_rate_gte: Optional[float] = None
    price_lte: Optional[float] = None
    price_gte: Optional[float] = None
    shop_type: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, Any]]) -> "Constraints":
        """Build constraints from a raw input dictionary."""

        data = payload or {}
        data = _require_dict(data, "constraints")

        positive_rate_gte = _to_optional_float(
            data.get("positive_rate_gte"), "constraints.positive_rate_gte"
        )
        price_lte = _to_optional_float(data.get("price_lte"), "constraints.price_lte")
        price_gte = _to_optional_float(data.get("price_gte"), "constraints.price_gte")

        shop_type_raw = data.get("shop_type")
        if shop_type_raw is None:
            shop_type = None
        elif isinstance(shop_type_raw, str):
            normalized = shop_type_raw.strip()
            shop_type = normalized or None
        else:
            raise SkillError(INVALID_INPUT, "constraints.shop_type must be a string.")

        if price_gte is not None and price_lte is not None and price_gte > price_lte:
            raise SkillError(
                INVALID_INPUT,
                "constraints.price_gte cannot be greater than constraints.price_lte.",
            )

        return cls(
            positive_rate_gte=positive_rate_gte,
            price_lte=price_lte,
            price_gte=price_gte,
            shop_type=shop_type,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize constraints to a JSON-compatible dictionary."""

        return {
            "positive_rate_gte": self.positive_rate_gte,
            "price_lte": self.price_lte,
            "price_gte": self.price_gte,
            "shop_type": self.shop_type,
        }


@dataclass
class TaskPayload:
    """Validated skill input payload."""

    platform: str
    keyword: str
    constraints: Constraints
    action: str
    notify_channel: str = "feishu"
    max_candidates: int = 5
    need_login: bool = True
    task_id: str = field(default_factory=lambda: uuid4().hex)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TaskPayload":
        """Validate and construct task payload from raw input."""

        data = _require_dict(payload, "payload")

        platform = data.get("platform", "taobao")
        if not isinstance(platform, str) or not platform.strip():
            raise SkillError(INVALID_INPUT, "platform must be a non-empty string.")
        platform = platform.strip().lower()
        if platform != "taobao":
            raise SkillError(INVALID_INPUT, "platform must be taobao.")

        keyword = data.get("keyword")
        if not isinstance(keyword, str) or not keyword.strip():
            raise SkillError(INVALID_INPUT, "keyword is required and cannot be empty.")
        keyword = keyword.strip()

        constraints = Constraints.from_dict(data.get("constraints", {}))

        action = data.get("action")
        if not isinstance(action, str) or not action.strip():
            raise SkillError(INVALID_INPUT, "action is required.")
        action = action.strip().lower()
        if action not in ALLOWED_ACTIONS:
            raise SkillError(
                INVALID_INPUT,
                f"action must be one of: {', '.join(sorted(ALLOWED_ACTIONS))}.",
            )

        notify_channel = data.get("notify_channel", "feishu")
        if not isinstance(notify_channel, str) or not notify_channel.strip():
            raise SkillError(INVALID_INPUT, "notify_channel must be a non-empty string.")
        notify_channel = notify_channel.strip()

        max_candidates = data.get("max_candidates", 5)
        if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
            raise SkillError(INVALID_INPUT, "max_candidates must be an integer.")
        if max_candidates <= 0:
            raise SkillError(INVALID_INPUT, "max_candidates must be greater than 0.")

        need_login = data.get("need_login", True)
        if not isinstance(need_login, bool):
            raise SkillError(INVALID_INPUT, "need_login must be a boolean.")

        task_id_raw = data.get("task_id")
        if task_id_raw is None:
            task_id = uuid4().hex
        elif isinstance(task_id_raw, str) and task_id_raw.strip():
            task_id = task_id_raw.strip()
        else:
            raise SkillError(INVALID_INPUT, "task_id must be a non-empty string.")

        return cls(
            platform=platform,
            keyword=keyword,
            constraints=constraints,
            action=action,
            notify_channel=notify_channel,
            max_candidates=max_candidates,
            need_login=need_login,
            task_id=task_id,
        )

    def to_dict(self, include_task_id: bool = False) -> Dict[str, Any]:
        """Serialize the validated payload for downstream modules."""

        payload: Dict[str, Any] = {
            "platform": self.platform,
            "keyword": self.keyword,
            "constraints": self.constraints.to_dict(),
            "action": self.action,
            "notify_channel": self.notify_channel,
            "max_candidates": self.max_candidates,
            "need_login": self.need_login,
        }
        if include_task_id:
            payload["task_id"] = self.task_id
        return payload


@dataclass
class ProductCandidate:
    """Structured product candidate extracted from a result page."""

    title: str
    price: Optional[float] = None
    positive_rate: Optional[float] = None
    shop_name: Optional[str] = None
    product_url: Optional[str] = None
    comment_count: Optional[int] = None
    confidence: Optional[float] = None
    source_page: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ProductCandidate":
        """Build a product candidate from raw data."""

        data = _require_dict(payload, "selected_product")

        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise SkillError(INVALID_INPUT, "selected_product.title is required.")

        shop_name = data.get("shop_name")
        if shop_name is not None and not isinstance(shop_name, str):
            raise SkillError(INVALID_INPUT, "selected_product.shop_name must be a string.")

        product_url = data.get("product_url")
        if product_url is not None and not isinstance(product_url, str):
            raise SkillError(
                INVALID_INPUT, "selected_product.product_url must be a string."
            )

        source_page = data.get("source_page")
        if source_page is not None and not isinstance(source_page, str):
            raise SkillError(
                INVALID_INPUT, "selected_product.source_page must be a string."
            )

        return cls(
            title=title.strip(),
            price=_to_optional_float(data.get("price"), "selected_product.price"),
            positive_rate=_to_optional_float(
                data.get("positive_rate"), "selected_product.positive_rate"
            ),
            shop_name=shop_name.strip() if isinstance(shop_name, str) else None,
            product_url=product_url.strip() if isinstance(product_url, str) else None,
            comment_count=_to_optional_int(
                data.get("comment_count"), "selected_product.comment_count"
            ),
            confidence=_to_optional_float(
                data.get("confidence"), "selected_product.confidence"
            ),
            source_page=source_page.strip() if isinstance(source_page, str) else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize product candidate to a JSON-compatible dictionary."""

        return {
            "title": self.title,
            "price": self.price,
            "positive_rate": self.positive_rate,
            "shop_name": self.shop_name,
            "product_url": self.product_url,
            "comment_count": self.comment_count,
            "confidence": self.confidence,
            "source_page": self.source_page,
        }


@dataclass
class SkillResult:
    """Standardized skill output structure."""

    success: bool
    task_status: str
    selected_product: Optional[ProductCandidate]
    message: str
    error_code: Optional[str]
    error_detail: Optional[Dict[str, Any]]

    def __post_init__(self) -> None:
        if self.task_status not in ALLOWED_TASK_STATUS:
            raise SkillError(
                INVALID_INPUT,
                f"task_status must be one of: {', '.join(sorted(ALLOWED_TASK_STATUS))}.",
            )
        if not isinstance(self.message, str) or not self.message.strip():
            raise SkillError(INVALID_INPUT, "message must be a non-empty string.")

    @classmethod
    def from_error(
        cls,
        error_code: str,
        message: str,
        *,
        detail: Optional[Dict[str, Any]] = None,
        task_status: str = "failed",
    ) -> "SkillResult":
        """Create a standardized error result."""

        return cls(
            success=False,
            task_status=task_status,
            selected_product=None,
            message=message,
            error_code=error_code,
            error_detail=detail,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to the standard output schema."""

        return {
            "success": self.success,
            "task_status": self.task_status,
            "selected_product": (
                self.selected_product.to_dict() if self.selected_product else None
            ),
            "message": self.message,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
        }

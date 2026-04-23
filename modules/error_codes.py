from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


INVALID_INPUT = "INVALID_INPUT"
LOGIN_REQUIRED = "LOGIN_REQUIRED"
CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
RISK_CONTROL_PAGE = "RISK_CONTROL_PAGE"
SEARCH_TIMEOUT = "SEARCH_TIMEOUT"
NO_SEARCH_RESULT = "NO_SEARCH_RESULT"
NO_MATCHED_PRODUCT = "NO_MATCHED_PRODUCT"
DETAIL_PARSE_FAILED = "DETAIL_PARSE_FAILED"
ADD_CART_FAILED = "ADD_CART_FAILED"
SKU_SELECTION_REQUIRED = "SKU_SELECTION_REQUIRED"
PAGE_STRUCTURE_CHANGED = "PAGE_STRUCTURE_CHANGED"
NETWORK_ERROR = "NETWORK_ERROR"
UNKNOWN_ERROR = "UNKNOWN_ERROR"


HUMAN_INTERVENTION_CODES = {
    LOGIN_REQUIRED,
    CAPTCHA_DETECTED,
    RISK_CONTROL_PAGE,
    SKU_SELECTION_REQUIRED,
}


@dataclass
class SkillError(Exception):
    """Structured business exception used by the skill pipeline."""

    code: str
    message: str
    detail: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

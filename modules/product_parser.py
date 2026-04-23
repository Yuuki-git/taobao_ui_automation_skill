from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import Constraints, ProductCandidate


_SHOP_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "flagship": ("flagship", "旗舰店", "旗舰"),
    "official": ("official", "官方"),
    "enterprise": ("enterprise", "企业"),
    "personal": ("personal", "个人"),
}


@dataclass
class ProductParser:
    """Pure parsing/filtering facade for product candidates.

    This phase only implements deterministic filtering/ranking logic.
    Browser extraction stays as a placeholder for later phases.
    """

    runtime: Any | None = None
    config: Any | None = None
    task_id: str | None = None

    def extract_candidates(self, max_candidates: int = 5) -> list[ProductCandidate]:
        """Placeholder for phase3B+ browser extraction logic."""

        _ = max_candidates
        return []

    def select_best_candidate(
        self,
        candidates: list[ProductCandidate],
        keyword: str,
        constraints: Constraints,
    ) -> ProductCandidate | None:
        """Filter candidates by keyword/constraints and return the best ranked one."""

        if not candidates:
            return None

        normalized_keyword = (keyword or "").strip()
        if not normalized_keyword:
            return None

        matched = [
            candidate
            for candidate in candidates
            if self._matches_keyword(candidate, normalized_keyword)
            and self._matches_constraints(candidate, constraints)
        ]
        if not matched:
            return None

        return sorted(matched, key=self._score_candidate)[0]

    def _matches_keyword(self, candidate: ProductCandidate, keyword: str) -> bool:
        title = (candidate.title or "").strip()
        if not title:
            return False
        return keyword.casefold() in title.casefold()

    def _matches_constraints(
        self, candidate: ProductCandidate, constraints: Constraints
    ) -> bool:
        if constraints.positive_rate_gte is not None:
            if candidate.positive_rate is None:
                return False
            if candidate.positive_rate < constraints.positive_rate_gte:
                return False

        if constraints.price_lte is not None:
            if candidate.price is None:
                return False
            if candidate.price > constraints.price_lte:
                return False

        if constraints.price_gte is not None:
            if candidate.price is None:
                return False
            if candidate.price < constraints.price_gte:
                return False

        if constraints.shop_type is not None:
            if not self._matches_shop_type(candidate, constraints.shop_type):
                return False

        return True

    def _matches_shop_type(self, candidate: ProductCandidate, shop_type: str) -> bool:
        shop_name = (candidate.shop_name or "").strip()
        required = (shop_type or "").strip()
        if not required:
            return True
        if not shop_name:
            return False

        shop_name_folded = shop_name.casefold()
        required_folded = required.casefold()

        known_hints = self._expand_shop_type_hints(required_folded)
        if known_hints:
            return any(hint in shop_name_folded for hint in known_hints)

        return required_folded in shop_name_folded

    def _score_candidate(self, candidate: ProductCandidate) -> tuple[float, float, float, float]:
        positive_rate = (
            candidate.positive_rate if candidate.positive_rate is not None else float("-inf")
        )
        confidence = candidate.confidence if candidate.confidence is not None else float("-inf")
        comment_count = (
            float(candidate.comment_count)
            if candidate.comment_count is not None
            else float("-inf")
        )
        price = candidate.price if candidate.price is not None else float("inf")
        return (-positive_rate, -confidence, -comment_count, price)

    def _expand_shop_type_hints(self, required_shop_type: str) -> tuple[str, ...]:
        matched_hints: list[str] = []
        for semantic_key, hints in _SHOP_TYPE_HINTS.items():
            if semantic_key in required_shop_type or any(
                hint.casefold() in required_shop_type for hint in hints
            ):
                matched_hints.extend(hint.casefold() for hint in hints)
        return tuple(dict.fromkeys(matched_hints))

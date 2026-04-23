from __future__ import annotations

from dataclasses import dataclass
import re
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
        """Extract product candidates from visible page text using a basic parser.

        TODO(phase-3B+): replace text-block parsing with stable DOM/locator parsing.
        """

        if max_candidates <= 0:
            return []
        if self.runtime is None or not hasattr(self.runtime, "get_visible_text"):
            return []

        raw_text = str(self.runtime.get_visible_text() or "")
        if not raw_text.strip():
            return []

        candidates: list[ProductCandidate] = []
        for block in self._split_candidate_blocks(raw_text):
            parsed = self._parse_candidate_block(block)
            if parsed is None:
                continue
            candidates.append(parsed)
            if len(candidates) >= max_candidates:
                break
        return candidates

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

    def _split_candidate_blocks(self, text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n")
        blocks = re.split(r"\n\s*\n+", normalized)
        return [block.strip() for block in blocks if block.strip()]

    def _parse_candidate_block(self, block: str) -> ProductCandidate | None:
        title: str | None = None
        price: float | None = None
        positive_rate: float | None = None
        shop_name: str | None = None
        comment_count: int | None = None
        confidence: float | None = None

        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            lower = line.casefold()
            if lower.startswith(("title:", "title：", "标题:", "标题：")):
                title = self._extract_text_value(line)
                continue
            if lower.startswith(("price:", "price：", "价格:", "价格：", "￥", "$")):
                price = self._extract_float_value(line)
                continue
            if lower.startswith(
                (
                    "positive rate:",
                    "positive rate：",
                    "positive_rate:",
                    "positive_rate：",
                    "好评率:",
                    "好评率：",
                )
            ):
                positive_rate = self._extract_float_value(line)
                continue
            if lower.startswith(("shop:", "shop：", "shop name:", "shop name：", "店铺:", "店铺：")):
                shop_name = self._extract_text_value(line)
                continue
            if lower.startswith(
                (
                    "comments:",
                    "comments：",
                    "comment count:",
                    "comment count：",
                    "comment_count:",
                    "comment_count：",
                    "评论:",
                    "评论：",
                    "评价:",
                    "评价：",
                )
            ):
                comment_count = self._extract_int_value(line)
                continue
            if lower.startswith(
                ("confidence:", "confidence：", "置信度:", "置信度：")
            ):
                confidence = self._extract_float_value(line)
                continue

            if title is None and not self._looks_like_key_value_line(line):
                title = line

        if title is None or not title.strip():
            return None

        return ProductCandidate(
            title=title.strip(),
            price=price,
            positive_rate=positive_rate,
            shop_name=shop_name.strip() if isinstance(shop_name, str) else None,
            product_url=None,
            comment_count=comment_count,
            confidence=confidence,
            source_page="search",
        )

    def _extract_text_value(self, line: str) -> str:
        _, _, value = line.partition(":")
        if not value:
            _, _, value = line.partition("：")
        return value.strip()

    def _extract_float_value(self, line: str) -> float | None:
        cleaned = line.replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if match is None:
            return None
        return float(match.group(0))

    def _extract_int_value(self, line: str) -> int | None:
        value = self._extract_float_value(line)
        if value is None:
            return None
        return int(value)

    def _looks_like_key_value_line(self, line: str) -> bool:
        return ":" in line or "：" in line

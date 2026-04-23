from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from models import Constraints, ProductCandidate
from modules.selectors import SEARCH_RESULT_CARD_SELECTORS


_SHOP_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "flagship": ("flagship", "\u65d7\u8230\u5e97", "\u65d7\u8230"),
    "official": ("official", "\u5b98\u65b9"),
    "enterprise": ("enterprise", "\u4f01\u4e1a"),
    "personal": ("personal", "\u4e2a\u4eba"),
}


@dataclass
class ProductParser:
    """Product parsing and filtering facade.

    Current phase:
    - `extract_candidates` uses DOM card locators with lightweight text parsing.
    - `select_best_candidate` stays pure and deterministic.
    """

    runtime: Any | None = None
    config: Any | None = None
    task_id: str | None = None

    def extract_candidates(self, max_candidates: int = 5) -> list[ProductCandidate]:
        """Extract product candidates from search-result cards.

        The implementation is intentionally lightweight and replaceable.
        TODO(phase-3C+): use more stable card-field locators per page variant.
        """

        if max_candidates <= 0:
            return []
        if self.runtime is None:
            return []

        if hasattr(self.runtime, "get_visible_text"):
            visible_text = str(self.runtime.get_visible_text() or "").strip()
            if not visible_text:
                return []

        page = self._get_runtime_page()
        if page is None:
            return []

        for selector in SEARCH_RESULT_CARD_SELECTORS:
            cards = self._safe_locator_all(page, selector)
            if not cards:
                continue
            if not self._looks_like_product_card_group(cards):
                continue

            extracted: list[ProductCandidate] = []
            for card in cards:
                candidate = self._extract_candidate_from_card(card)
                if candidate is None:
                    continue
                extracted.append(candidate)
                if len(extracted) >= max_candidates:
                    break
            if extracted:
                return extracted
            # Cards were found but nothing parsable was extracted; try next selector.
            continue
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

    def _get_runtime_page(self) -> Any | None:
        if self.runtime is None:
            return None
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

    def _safe_locator_all(self, page: Any, selector: str) -> list[Any]:
        try:
            locator_group = page.locator(selector)
            cards = locator_group.all()
        except Exception:
            return []
        if not isinstance(cards, list):
            return []
        return cards

    def _looks_like_product_card_group(self, cards: Iterable[Any]) -> bool:
        for card in list(cards)[:3]:
            text = self._safe_inner_text(card)
            if not text:
                continue
            if self._extract_price(text) is not None:
                return True
            if re.search(r"(sold|review|comment|\u9500\u91cf|\u8bc4\u4ef7|\u5e97)", text, re.I):
                return True
        return False

    def _extract_candidate_from_card(self, card: Any) -> ProductCandidate | None:
        text = self._safe_inner_text(card)
        if not text:
            return None

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        title = self._extract_title(lines)
        if not title:
            return None

        return ProductCandidate(
            title=title,
            price=self._extract_price("\n".join(lines)),
            positive_rate=self._extract_positive_rate("\n".join(lines)),
            shop_name=self._extract_shop_name(lines),
            product_url=None,
            comment_count=self._extract_comment_count("\n".join(lines)),
            confidence=self._extract_confidence("\n".join(lines)),
            source_page="search_result",
        )

    def _safe_inner_text(self, locator: Any) -> str:
        try:
            return str(locator.inner_text() or "").strip()
        except Exception:
            return ""

    def _extract_title(self, lines: list[str]) -> str | None:
        for line in lines:
            lower = line.casefold()
            if self._is_price_line(lower):
                continue
            if self._is_rate_line(lower):
                continue
            if self._is_comment_line(lower):
                continue
            if self._is_shop_line(lower):
                continue
            if len(line) < 2:
                continue
            return line
        return None

    def _extract_price(self, text: str) -> float | None:
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if self._is_price_line(cleaned.casefold()):
                match = re.search(r"(?:\u00a5|\uffe5|\$)?\s*(\d+(?:\.\d+)?)", cleaned)
                if match:
                    return float(match.group(1))
        return None

    def _extract_positive_rate(self, text: str) -> float | None:
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            lower = cleaned.casefold()
            if "%" not in cleaned:
                continue
            if "positive" not in lower and "rate" not in lower and "\u597d\u8bc4" not in cleaned:
                continue
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", cleaned)
            if match:
                value = float(match.group(1))
                if 0 <= value <= 100:
                    return value
        return None

    def _extract_shop_name(self, lines: list[str]) -> str | None:
        for line in lines:
            lower = line.casefold()
            if self._is_shop_line(lower):
                return line
        return None

    def _extract_comment_count(self, text: str) -> int | None:
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if not self._is_comment_line(cleaned.casefold()):
                continue
            parsed = self._parse_count_with_units(cleaned)
            if parsed is not None:
                return parsed
        return None

    def _extract_confidence(self, text: str) -> float | None:
        for line in text.splitlines():
            match = re.search(r"confidence\s*[:=]\s*(\d+(?:\.\d+)?)", line, re.I)
            if not match:
                continue
            value = float(match.group(1))
            if 0 <= value <= 1:
                return value
        return None

    def _parse_count_with_units(self, text: str) -> int | None:
        normalized = text.casefold().replace(",", "").replace("+", "")
        match = re.search(r"(\d+(?:\.\d+)?)\s*(\u4e07|\u5343|w|k)?", normalized)
        if not match:
            return None
        value = float(match.group(1))
        unit = match.group(2)
        if unit in ("\u4e07", "w"):
            value *= 10000
        elif unit in ("\u5343", "k"):
            value *= 1000
        return int(value)

    def _is_price_line(self, lower_line: str) -> bool:
        return (
            "\u00a5" in lower_line
            or "\uffe5" in lower_line
            or "$" in lower_line
            or "price" in lower_line
            or "\u4ef7\u683c" in lower_line
        )

    def _is_rate_line(self, lower_line: str) -> bool:
        return "%" in lower_line and (
            "positive" in lower_line or "rate" in lower_line or "\u597d\u8bc4" in lower_line
        )

    def _is_comment_line(self, lower_line: str) -> bool:
        if any(
            token in lower_line
            for token in (
                "sold",
                "review",
                "comment",
                "\u4ed8\u6b3e",
                "\u4eba\u4ed8\u6b3e",
                "\u9500\u91cf",
                "\u8bc4\u8bba",
                "\u8bc4\u4ef7",
            )
        ):
            return True
        if ("pay" in lower_line or "paid" in lower_line) and re.search(r"\d", lower_line):
            return True
        return False

    def _is_shop_line(self, lower_line: str) -> bool:
        return any(
            token in lower_line
            for token in ("shop", "store", "\u5e97", "\u65d7\u8230", "\u5b98\u65b9")
        )

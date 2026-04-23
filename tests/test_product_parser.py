from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import Constraints, ProductCandidate
from modules.product_parser import ProductParser
from modules.selectors import SEARCH_RESULT_CARD_SELECTORS


def _candidate(
    *,
    title: str,
    price: float | None = None,
    positive_rate: float | None = None,
    shop_name: str | None = None,
    comment_count: int | None = None,
    confidence: float | None = None,
) -> ProductCandidate:
    return ProductCandidate(
        title=title,
        price=price,
        positive_rate=positive_rate,
        shop_name=shop_name,
        product_url=None,
        comment_count=comment_count,
        confidence=confidence,
        source_page="search",
    )


def test_keyword_match_success_returns_best_candidate() -> None:
    parser = ProductParser()
    candidates = [
        _candidate(
            title="wireless bluetooth headset",
            positive_rate=98.5,
            confidence=0.8,
            comment_count=80,
            price=200.0,
        )
    ]

    selected = parser.select_best_candidate(
        candidates, "Bluetooth", Constraints.from_dict({})
    )

    assert selected is not None
    assert selected.title == "wireless bluetooth headset"


def test_keyword_mismatch_returns_none() -> None:
    parser = ProductParser()
    candidates = [_candidate(title="wired keyboard", price=99.0, positive_rate=99.0)]

    selected = parser.select_best_candidate(
        candidates, "headset", Constraints.from_dict({})
    )

    assert selected is None


def test_positive_rate_gte_filters_candidates() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({"positive_rate_gte": 99})
    candidates = [
        _candidate(title="headset alpha", positive_rate=None, price=100.0),
        _candidate(title="headset beta", positive_rate=98.9, price=120.0),
        _candidate(title="headset gamma", positive_rate=99.2, price=140.0),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is not None
    assert selected.title == "headset gamma"


def test_price_lte_filters_candidates() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({"price_lte": 200})
    candidates = [
        _candidate(title="headset expensive", price=260.0, positive_rate=99.1),
        _candidate(title="headset budget", price=180.0, positive_rate=99.0),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is not None
    assert selected.title == "headset budget"


def test_price_gte_filters_candidates() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({"price_gte": 1000})
    candidates = [
        _candidate(title="headset entry", price=899.0, positive_rate=99.0),
        _candidate(title="headset premium", price=1299.0, positive_rate=98.8),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is not None
    assert selected.title == "headset premium"


def test_shop_type_loose_matching_supports_common_semantics() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({"shop_type": "flagship"})
    candidates = [
        _candidate(title="headset personal", shop_name="personal store", positive_rate=99.5),
        _candidate(
            title="headset official",
            shop_name="official flagship store",
            positive_rate=99.2,
        ),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is not None
    assert selected.shop_name == "official flagship store"


def test_unknown_shop_type_without_loose_match_returns_none() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({"shop_type": "campus"})
    candidates = [
        _candidate(title="headset one", shop_name="flagship store", positive_rate=99.1),
        _candidate(title="headset two", shop_name="personal shop", positive_rate=99.0),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is None


def test_multi_candidate_ranking_priority() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({})
    candidates = [
        _candidate(
            title="headset p1",
            positive_rate=99.1,
            confidence=0.95,
            comment_count=900,
            price=100.0,
        ),
        _candidate(
            title="headset p2",
            positive_rate=99.3,
            confidence=0.10,
            comment_count=5,
            price=999.0,
        ),
        _candidate(
            title="headset p3",
            positive_rate=99.3,
            confidence=0.95,
            comment_count=100,
            price=500.0,
        ),
        _candidate(
            title="headset p4",
            positive_rate=99.3,
            confidence=0.95,
            comment_count=100,
            price=300.0,
        ),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is not None
    assert selected.title == "headset p4"


def test_missing_fields_are_worse_and_constraint_missing_field_fails() -> None:
    parser = ProductParser()
    candidates = [
        _candidate(
            title="headset missing",
            positive_rate=None,
            confidence=None,
            comment_count=None,
            price=None,
        ),
        _candidate(
            title="headset complete",
            positive_rate=98.0,
            confidence=0.6,
            comment_count=10,
            price=200.0,
        ),
    ]

    selected_without_constraints = parser.select_best_candidate(
        candidates, "headset", Constraints.from_dict({})
    )
    selected_with_price_constraint = parser.select_best_candidate(
        candidates, "headset", Constraints.from_dict({"price_lte": 300})
    )

    assert selected_without_constraints is not None
    assert selected_without_constraints.title == "headset complete"
    assert selected_with_price_constraint is not None
    assert selected_with_price_constraint.title == "headset complete"


def test_empty_candidates_returns_none() -> None:
    parser = ProductParser()

    selected = parser.select_best_candidate([], "headset", Constraints.from_dict({}))

    assert selected is None


class _FakeCard:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self) -> str:
        return self._text


class _FakeLocatorGroup:
    def __init__(self, cards: list[_FakeCard]) -> None:
        self._cards = cards

    def all(self) -> list[_FakeCard]:
        return self._cards


class _FakePage:
    def __init__(self, selector_cards: dict[str, list[_FakeCard]]) -> None:
        self.selector_cards = selector_cards
        self.locator_calls: list[str] = []

    def locator(self, selector: str) -> _FakeLocatorGroup:
        self.locator_calls.append(selector)
        return _FakeLocatorGroup(self.selector_cards.get(selector, []))


class _FakeRuntime:
    def __init__(self, page: _FakePage, visible_text: str = "ready") -> None:
        self._page = page
        self._visible_text = visible_text

    def get_visible_text(self) -> str:
        return self._visible_text

    def require_page(self) -> _FakePage:
        return self._page


def test_extract_candidates_returns_empty_when_page_text_is_empty() -> None:
    page = _FakePage({})
    parser = ProductParser(runtime=_FakeRuntime(page=page, visible_text=""))

    extracted = parser.extract_candidates(max_candidates=5)

    assert extracted == []


def test_extract_candidates_selector_fallback_stops_on_first_usable_group() -> None:
    first_selector = SEARCH_RESULT_CARD_SELECTORS[0]
    second_selector = SEARCH_RESULT_CARD_SELECTORS[1]
    third_selector = SEARCH_RESULT_CARD_SELECTORS[2]

    page = _FakePage(
        {
            first_selector: [],
            second_selector: [
                _FakeCard(
                    "\n".join(
                        [
                            "Wireless Headset Alpha",
                            "¥1999",
                            "Official Store",
                            "99.2% positive",
                            "1.2万 reviews",
                        ]
                    )
                )
            ],
            third_selector: [
                _FakeCard(
                    "\n".join(
                        [
                            "Should Not Be Read",
                            "¥1",
                        ]
                    )
                )
            ],
        }
    )
    parser = ProductParser(runtime=_FakeRuntime(page=page))

    extracted = parser.extract_candidates(max_candidates=5)

    assert len(extracted) == 1
    assert extracted[0].title == "Wireless Headset Alpha"
    assert page.locator_calls == [first_selector, second_selector]


def test_extract_candidates_parses_multiple_candidates_from_card_texts() -> None:
    selector = SEARCH_RESULT_CARD_SELECTORS[0]
    page = _FakePage(
        {
            selector: [
                _FakeCard(
                    "\n".join(
                        [
                            "Wireless Headset Alpha",
                            "¥1999",
                            "Official Store",
                            "99.2% positive",
                            "1.2万 reviews",
                        ]
                    )
                ),
                _FakeCard(
                    "\n".join(
                        [
                            "Bluetooth Headset Beta",
                            "$899",
                            "Brand Flagship Store",
                            "98.6% positive",
                            "340 reviews",
                        ]
                    )
                ),
            ]
        }
    )
    parser = ProductParser(runtime=_FakeRuntime(page=page))

    extracted = parser.extract_candidates(max_candidates=5)

    assert len(extracted) == 2
    assert extracted[0].title == "Wireless Headset Alpha"
    assert extracted[0].price == 1999.0
    assert extracted[0].shop_name == "Official Store"
    assert extracted[0].positive_rate == 99.2
    assert extracted[0].comment_count == 12000
    assert extracted[0].source_page == "search_result"
    assert extracted[1].title == "Bluetooth Headset Beta"


def test_extract_candidates_skips_card_without_title() -> None:
    selector = SEARCH_RESULT_CARD_SELECTORS[0]
    page = _FakePage(
        {
            selector: [
                _FakeCard(
                    "\n".join(
                        [
                            "¥1999",
                            "Official Store",
                            "99.2% positive",
                            "500 reviews",
                        ]
                    )
                ),
                _FakeCard(
                    "\n".join(
                        [
                            "Candidate With Title",
                            "¥1099",
                            "220 reviews",
                        ]
                    )
                ),
            ]
        }
    )
    parser = ProductParser(runtime=_FakeRuntime(page=page))

    extracted = parser.extract_candidates(max_candidates=5)

    assert len(extracted) == 1
    assert extracted[0].title == "Candidate With Title"


def test_extract_candidates_respects_max_candidates() -> None:
    selector = SEARCH_RESULT_CARD_SELECTORS[0]
    page = _FakePage(
        {
            selector: [
                _FakeCard("Candidate A\n¥100"),
                _FakeCard("Candidate B\n¥200"),
                _FakeCard("Candidate C\n¥300"),
            ]
        }
    )
    parser = ProductParser(runtime=_FakeRuntime(page=page))

    extracted = parser.extract_candidates(max_candidates=2)

    assert len(extracted) == 2
    assert [item.title for item in extracted] == ["Candidate A", "Candidate B"]


def test_extract_candidates_keeps_none_for_missing_optional_fields() -> None:
    selector = SEARCH_RESULT_CARD_SELECTORS[0]
    page = _FakePage({selector: [_FakeCard("Candidate Minimal\n500 reviews")]})
    parser = ProductParser(runtime=_FakeRuntime(page=page))

    extracted = parser.extract_candidates(max_candidates=5)

    assert len(extracted) == 1
    candidate = extracted[0]
    assert candidate.title == "Candidate Minimal"
    assert candidate.price is None
    assert candidate.positive_rate is None
    assert candidate.shop_name is None
    assert candidate.comment_count == 500
    assert candidate.confidence is None


def test_extract_candidates_returns_empty_when_no_selector_has_cards() -> None:
    page = _FakePage({selector: [] for selector in SEARCH_RESULT_CARD_SELECTORS})
    parser = ProductParser(runtime=_FakeRuntime(page=page))

    extracted = parser.extract_candidates(max_candidates=5)

    assert extracted == []

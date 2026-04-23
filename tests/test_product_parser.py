from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import Constraints, ProductCandidate
from modules.product_parser import ProductParser


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
        _candidate(title="headset personal", shop_name="个人卖家", positive_rate=99.5),
        _candidate(title="headset official", shop_name="品牌官方旗舰店", positive_rate=99.2),
    ]

    selected = parser.select_best_candidate(candidates, "headset", constraints)

    assert selected is not None
    assert selected.shop_name == "品牌官方旗舰店"


def test_unknown_shop_type_without_loose_match_returns_none() -> None:
    parser = ProductParser()
    constraints = Constraints.from_dict({"shop_type": "campus"})
    candidates = [
        _candidate(title="headset one", shop_name="旗舰店", positive_rate=99.1),
        _candidate(title="headset two", shop_name="校园二手店", positive_rate=99.0),
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

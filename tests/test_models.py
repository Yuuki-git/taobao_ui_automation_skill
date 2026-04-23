from pathlib import Path
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import Constraints, ProductCandidate, TaskPayload
from modules.error_codes import INVALID_INPUT, SkillError


def test_task_payload_defaults_are_applied() -> None:
    payload = TaskPayload.from_dict({"keyword": "蓝牙耳机", "action": "search_only"})
    assert payload.platform == "taobao"
    assert payload.notify_channel == "feishu"
    assert payload.max_candidates == 5
    assert payload.need_login is True
    assert payload.task_id


def test_task_payload_rejects_non_taobao_platform() -> None:
    with pytest.raises(SkillError) as exc_info:
        TaskPayload.from_dict(
            {"platform": "jd", "keyword": "蓝牙耳机", "action": "search_only"}
        )

    assert exc_info.value.code == INVALID_INPUT


def test_constraints_rejects_conflicting_price_range() -> None:
    with pytest.raises(SkillError) as exc_info:
        Constraints.from_dict({"price_gte": 2000, "price_lte": 1000})

    assert exc_info.value.code == INVALID_INPUT


def test_constraints_accepts_free_shop_type_string() -> None:
    constraints = Constraints.from_dict({"shop_type": "my-custom-shop-tag"})
    assert constraints.shop_type == "my-custom-shop-tag"


def test_task_payload_dict_does_not_expose_task_id_by_default() -> None:
    payload = TaskPayload.from_dict({"keyword": "蓝牙耳机", "action": "search_only"})
    payload_dict = payload.to_dict()
    assert "task_id" not in payload_dict


def test_product_candidate_round_trip() -> None:
    candidate = ProductCandidate.from_dict(
        {
            "title": "测试商品",
            "price": 1999.0,
            "positive_rate": 99.5,
            "shop_name": "官方旗舰店",
            "product_url": "https://example.com/item/1",
            "comment_count": 1234,
            "confidence": 0.9,
            "source_page": "search",
        }
    )

    assert candidate.to_dict()["title"] == "测试商品"

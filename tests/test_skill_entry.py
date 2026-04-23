from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main
from models import ProductCandidate, SkillResult
from modules.error_codes import INVALID_INPUT, LOGIN_REQUIRED, SkillError, UNKNOWN_ERROR


def _valid_payload() -> dict:
    return {
        "platform": "taobao",
        "keyword": "蓝牙耳机",
        "constraints": {"positive_rate_gte": 99},
        "action": "search_only",
        "notify_channel": "feishu",
        "max_candidates": 5,
        "need_login": True,
    }


def test_run_skill_invalid_input_returns_standard_error() -> None:
    result = main.run_skill({"action": "search_only"})
    assert result["success"] is False
    assert result["task_status"] == "failed"
    assert result["error_code"] == INVALID_INPUT
    assert result["selected_product"] is None
    assert "task_id" not in result


def test_run_skill_maps_login_required_to_human_intervention(monkeypatch) -> None:
    class FakeOrchestrator:
        def run(self, _payload):
            raise SkillError(LOGIN_REQUIRED, "需要登录")

    monkeypatch.setattr(main, "_build_orchestrator", lambda _config: FakeOrchestrator())

    result = main.run_skill(_valid_payload())
    assert result["success"] is False
    assert result["task_status"] == "need_human_intervention"
    assert result["error_code"] == LOGIN_REQUIRED


def test_run_skill_handles_unknown_exception(monkeypatch) -> None:
    class FakeOrchestrator:
        def run(self, _payload):
            raise RuntimeError("unexpected boom")

    monkeypatch.setattr(main, "_build_orchestrator", lambda _config: FakeOrchestrator())

    result = main.run_skill(_valid_payload())
    assert result["success"] is False
    assert result["task_status"] == "failed"
    assert result["error_code"] == UNKNOWN_ERROR
    assert isinstance(result["error_detail"], dict)


def test_run_skill_smoke_search_only_success(monkeypatch) -> None:
    class FakeOrchestrator:
        def run(self, _payload):
            return SkillResult(
                success=True,
                task_status="completed",
                selected_product=ProductCandidate(
                    title="测试商品",
                    price=1999.0,
                    positive_rate=99.8,
                    shop_name="官方旗舰店",
                    product_url="https://example.com/item/1",
                    comment_count=100,
                    confidence=0.95,
                    source_page="search",
                ),
                message="任务执行完成",
                error_code=None,
                error_detail=None,
            )

    monkeypatch.setattr(main, "_build_orchestrator", lambda _config: FakeOrchestrator())

    result = main.run_skill(_valid_payload())
    assert result["success"] is True
    assert result["task_status"] == "completed"
    assert result["selected_product"]["title"] == "测试商品"
    assert result["error_code"] is None
    assert "task_id" not in result

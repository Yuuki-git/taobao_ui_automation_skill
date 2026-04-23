from pathlib import Path
import sys

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import SkillConfig
from models import ProductCandidate, SkillResult, TaskPayload
from modules.auth_manager import AUTHENTICATED, LOGIN_REQUIRED
from modules.error_codes import LOGIN_REQUIRED as LOGIN_REQUIRED_CODE
from modules.error_codes import NO_MATCHED_PRODUCT, SkillError
from modules.orchestrator import Orchestrator


class _FakeRuntime:
    def __init__(self, config):
        self.config = config
        self.started = False
        self.closed = False
        self.open_home_called = False
        self.searched_keyword = None

    def start(self) -> None:
        self.started = True

    def close(self) -> None:
        self.closed = True

    def open_taobao_home(self) -> None:
        self.open_home_called = True

    def search_keyword(self, keyword: str) -> None:
        self.searched_keyword = keyword


class _FakeAuthManager:
    def __init__(self, runtime, config, status):
        self.runtime = runtime
        self.config = config
        self.status = status
        self.need_login_calls = []

    def ensure_authenticated(self, *, need_login: bool) -> str:
        self.need_login_calls.append(need_login)
        return self.status


class _FakeProductParser:
    def __init__(self, runtime, config, candidates, selected):
        self.runtime = runtime
        self.config = config
        self._candidates = candidates
        self._selected = selected

    def extract_candidates(self, max_candidates: int = 5):
        return self._candidates[:max_candidates]

    def select_best_candidate(self, candidates, keyword, constraints):
        return self._selected


class _FakeCartExecutor:
    def __init__(self, runtime, config):
        self.runtime = runtime
        self.config = config

    def add_to_cart(self, product):
        return {"success": True}


class _FakeNotifier:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.success_calls = 0
        self.failure_calls = []

    def notify_success(self, result: SkillResult) -> None:
        self.success_calls += 1

    def notify_failure(self, error_code: str, message: str, detail=None) -> None:
        self.failure_calls.append((error_code, message, detail))


def _payload(action: str = "search_only", need_login: bool = True) -> TaskPayload:
    return TaskPayload.from_dict(
        {
            "platform": "taobao",
            "keyword": "蓝牙耳机",
            "constraints": {"positive_rate_gte": 99},
            "action": action,
            "need_login": need_login,
        }
    )


def test_orchestrator_search_only_success_returns_completed() -> None:
    selected = ProductCandidate(title="测试商品", price=1999.0, positive_rate=99.5)
    notifier_ref = {}
    runtime_ref = {}

    def runtime_factory(config):
        runtime = _FakeRuntime(config)
        runtime_ref["runtime"] = runtime
        return runtime

    def auth_factory(runtime, config):
        return _FakeAuthManager(runtime, config, AUTHENTICATED)

    def parser_factory(runtime, config):
        return _FakeProductParser(runtime, config, [selected], selected)

    def notifier_factory(task_id: str):
        notifier = _FakeNotifier(task_id)
        notifier_ref["notifier"] = notifier
        return notifier

    orchestrator = Orchestrator(
        config=SkillConfig(),
        runtime_factory=runtime_factory,
        auth_manager_factory=auth_factory,
        product_parser_factory=parser_factory,
        cart_executor_factory=_FakeCartExecutor,
        notifier_factory=notifier_factory,
    )

    result = orchestrator.run(_payload(action="search_only"))

    assert result.success is True
    assert result.task_status == "completed"
    assert result.selected_product is not None
    assert result.selected_product.title == "测试商品"
    assert runtime_ref["runtime"].closed is True
    assert notifier_ref["notifier"].success_calls == 1


def test_orchestrator_need_login_true_and_not_logged_in_raises_login_required() -> None:
    runtime_ref = {}

    def runtime_factory(config):
        runtime = _FakeRuntime(config)
        runtime_ref["runtime"] = runtime
        return runtime

    def auth_factory(runtime, config):
        return _FakeAuthManager(runtime, config, LOGIN_REQUIRED)

    orchestrator = Orchestrator(
        config=SkillConfig(),
        runtime_factory=runtime_factory,
        auth_manager_factory=auth_factory,
    )

    with pytest.raises(SkillError) as exc_info:
        orchestrator.run(_payload(action="search_only", need_login=True))

    assert exc_info.value.code == LOGIN_REQUIRED_CODE
    assert runtime_ref["runtime"].closed is True


def test_orchestrator_search_only_no_matched_product_returns_no_matched_result() -> None:
    def runtime_factory(config):
        return _FakeRuntime(config)

    def auth_factory(runtime, config):
        return _FakeAuthManager(runtime, config, AUTHENTICATED)

    def parser_factory(runtime, config):
        return _FakeProductParser(runtime, config, [], None)

    orchestrator = Orchestrator(
        config=SkillConfig(),
        runtime_factory=runtime_factory,
        auth_manager_factory=auth_factory,
        product_parser_factory=parser_factory,
        cart_executor_factory=_FakeCartExecutor,
    )

    result = orchestrator.run(_payload(action="search_only"))

    assert result.success is False
    assert result.task_status == "failed"
    assert result.error_code == NO_MATCHED_PRODUCT


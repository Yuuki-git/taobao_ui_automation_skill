from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import SkillConfig
from models import Constraints, ProductCandidate
from modules.cart_executor import CartExecutor
from modules.orchestrator import Orchestrator
from modules.product_parser import ProductParser
from tools.run_mock_smoke import (
    MOCK_SEARCH_PAGE,
    MockHtmlRuntime,
    build_mock_payload,
    build_mock_runtime_factory,
)


def _config() -> SkillConfig:
    return SkillConfig(default_headless=True)


def test_mock_parser_extracts_candidates_from_local_search_page() -> None:
    runtime = MockHtmlRuntime(
        config=_config(),
        mock_search_url=MOCK_SEARCH_PAGE.resolve().as_uri(),
    )
    runtime.start()
    try:
        runtime.open_taobao_home()
        runtime.search_keyword("蓝牙耳机")

        parser = ProductParser(runtime=runtime, config=_config())
        candidates = parser.extract_candidates(max_candidates=5)
        assert len(candidates) == 3

        selected = parser.select_best_candidate(
            candidates,
            "蓝牙耳机",
            Constraints.from_dict({"positive_rate_gte": 99}),
        )
        assert selected is not None
        assert selected.title == "蓝牙耳机 B"
        assert selected.product_url is not None
        assert "product_detail.html" in selected.product_url
    finally:
        runtime.close()


def test_mock_cart_executor_detects_success_on_local_detail_page() -> None:
    runtime = MockHtmlRuntime(
        config=_config(),
        mock_search_url=MOCK_SEARCH_PAGE.resolve().as_uri(),
    )
    runtime.start()
    try:
        detail_url = (ROOT_DIR / "mock_pages" / "product_detail.html").resolve().as_uri()
        runtime.goto(detail_url)
        executor = CartExecutor(runtime=runtime, config=_config())
        product = ProductCandidate(title="蓝牙耳机 B", product_url=detail_url)

        result = executor.add_to_cart(product)

        assert result["success"] is True
        assert result["error_code"] is None
    finally:
        runtime.close()


def test_mock_orchestrator_search_only_returns_selected_product() -> None:
    orchestrator = Orchestrator(
        config=_config(),
        runtime_factory=build_mock_runtime_factory(MOCK_SEARCH_PAGE.resolve().as_uri()),
    )

    result = orchestrator.run(build_mock_payload(action="search_only"))

    assert result.success is True
    assert result.task_status == "completed"
    assert result.selected_product is not None
    assert result.selected_product.title == "蓝牙耳机 B"


def test_mock_orchestrator_add_to_cart_returns_completed() -> None:
    orchestrator = Orchestrator(
        config=_config(),
        runtime_factory=build_mock_runtime_factory(MOCK_SEARCH_PAGE.resolve().as_uri()),
    )

    result = orchestrator.run(build_mock_payload(action="add_to_cart"))

    assert result.success is True
    assert result.task_status == "completed"
    assert result.selected_product is not None
    assert result.selected_product.title == "蓝牙耳机 B"

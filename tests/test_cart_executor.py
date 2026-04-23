from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import ProductCandidate
from modules.cart_executor import CartExecutor
from modules.error_codes import ADD_CART_FAILED, SKU_SELECTION_REQUIRED


class _FakeElement:
    def __init__(self, text: str = "") -> None:
        self._text = text
        self.clicked = False

    def inner_text(self) -> str:
        return self._text

    def click(self) -> None:
        self.clicked = True


class _FakeLocatorGroup:
    def __init__(self, elements: list[_FakeElement]) -> None:
        self._elements = elements

    def all(self) -> list[_FakeElement]:
        return self._elements


class _FakePage:
    def __init__(self, *, url: str, body_text: str, selector_map: dict[str, list[_FakeElement]]):
        self.url = url
        self.body_text = body_text
        self.selector_map = selector_map
        self.locator_calls: list[str] = []

    def locator(self, selector: str) -> _FakeLocatorGroup:
        self.locator_calls.append(selector)
        return _FakeLocatorGroup(self.selector_map.get(selector, []))

    def inner_text(self, selector: str) -> str:
        assert selector == "body"
        return self.body_text


class _FakeRuntime:
    def __init__(self, page: _FakePage) -> None:
        self._page = page
        self.goto_calls: list[str] = []

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)
        self._page.url = url

    def require_page(self) -> _FakePage:
        return self._page

    def get_visible_text(self) -> str:
        return self._page.body_text

    def get_page_url(self) -> str:
        return self._page.url


def _product(product_url: str | None = None) -> ProductCandidate:
    return ProductCandidate(
        title="candidate",
        price=1999.0,
        positive_rate=99.2,
        shop_name="official store",
        product_url=product_url,
        comment_count=1200,
        confidence=0.9,
        source_page="search_result",
    )


def test_add_to_cart_navigates_to_product_url_when_present() -> None:
    button = _FakeElement("加入购物车")
    page = _FakePage(
        url="https://example.com/search",
        body_text="已加入购物车",
        selector_map={"button:has-text('加入购物车')": [button]},
    )
    runtime = _FakeRuntime(page)
    executor = CartExecutor(runtime=runtime, config=None)

    result = executor.add_to_cart(_product(product_url="https://example.com/item/1"))

    assert runtime.goto_calls == ["https://example.com/item/1"]
    assert result["success"] is True


def test_add_to_cart_clicks_button_and_returns_success_when_feedback_detected() -> None:
    button = _FakeElement("加入购物车")
    page = _FakePage(
        url="https://example.com/item/1",
        body_text="商品已加入购物车",
        selector_map={"button:has-text('加入购物车')": [button]},
    )
    runtime = _FakeRuntime(page)
    executor = CartExecutor(runtime=runtime, config=None)

    result = executor.add_to_cart(_product(product_url=None))

    assert button.clicked is True
    assert result["success"] is True
    assert result["error_code"] is None


def test_add_to_cart_returns_sku_selection_required_for_complex_sku_hint() -> None:
    button = _FakeElement("加入购物车")
    page = _FakePage(
        url="https://example.com/item/1",
        body_text="请选择 颜色 分类 尺码",
        selector_map={"button:has-text('加入购物车')": [button]},
    )
    runtime = _FakeRuntime(page)
    executor = CartExecutor(runtime=runtime, config=None)

    result = executor.add_to_cart(_product(product_url=None))

    assert result["success"] is False
    assert result["error_code"] == SKU_SELECTION_REQUIRED


def test_add_to_cart_returns_add_cart_failed_when_button_not_found() -> None:
    page = _FakePage(
        url="https://example.com/item/1",
        body_text="普通详情页文本",
        selector_map={},
    )
    runtime = _FakeRuntime(page)
    executor = CartExecutor(runtime=runtime, config=None)

    result = executor.add_to_cart(_product(product_url=None))

    assert result["success"] is False
    assert result["error_code"] == ADD_CART_FAILED


def test_add_to_cart_returns_add_cart_failed_when_success_cannot_be_confirmed() -> None:
    button = _FakeElement("加入购物车")
    page = _FakePage(
        url="https://example.com/item/1",
        body_text="点击后页面无明显反馈",
        selector_map={"button:has-text('加入购物车')": [button]},
    )
    runtime = _FakeRuntime(page)
    executor = CartExecutor(runtime=runtime, config=None)

    result = executor.add_to_cart(_product(product_url=None))

    assert button.clicked is True
    assert result["success"] is False
    assert result["error_code"] == ADD_CART_FAILED

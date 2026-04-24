from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import SkillConfig
from models import TaskPayload
from modules.error_codes import NETWORK_ERROR, SkillError
from modules.orchestrator import Orchestrator
from modules.selectors import ADD_TO_CART_SELECTORS, ADD_TO_CART_SUCCESS_SELECTORS


MOCK_SEARCH_PAGE = PROJECT_ROOT / "mock_pages" / "search_result.html"


def _strip_tags(raw_html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", raw_html or "")).strip()


def _norm_text(raw_html: str) -> str:
    return re.sub(r"\s+", " ", _strip_tags(raw_html))


def _parse_file_url(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme != "file":
        raise SkillError(
            NETWORK_ERROR,
            "Mock runtime only supports local file URLs.",
            {"url": url},
        )
    if parsed.scheme == "file":
        return Path(unquote(parsed.path.lstrip("/")))
    return Path(url)


def _matches_has_text_selector(selector: str, tag: str, text: str) -> bool:
    match = re.match(r"^(?P<tag>[a-zA-Z]+):has-text\('(?P<text>.*)'\)$", selector)
    if not match:
        return False
    return match.group("tag").lower() == tag.lower() and match.group("text").casefold() in text.casefold()


class _MockLocatorGroup:
    def __init__(self, elements: list[Any]) -> None:
        self._elements = elements

    def all(self) -> list[Any]:
        return list(self._elements)


class _MockLink:
    def __init__(self, href: str) -> None:
        self._href = href

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self._href
        return None

    def inner_text(self) -> str:
        return ""


class _MockSearchCard:
    def __init__(
        self,
        *,
        title: str,
        price_line: str,
        meta_lines: list[str],
        href: str | None,
    ) -> None:
        self.title = title
        self.price_line = price_line
        self.meta_lines = meta_lines
        self.href = href

    def inner_text(self) -> str:
        lines = [self.title, self.price_line, *self.meta_lines]
        return "\n".join(line for line in lines if line)

    def locator(self, selector: str) -> _MockLocatorGroup:
        if selector == "a[href]" and self.href:
            return _MockLocatorGroup([_MockLink(self.href)])
        return _MockLocatorGroup([])


class _MockSearchPage:
    CARD_SELECTORS = {
        ".item",
        ".ctx-box",
        ".card",
        "[data-index]",
        ".m-itemlist .items .item",
        ".mock-product-card",
    }

    def __init__(self, *, html_text: str, url: str) -> None:
        self._html_text = html_text
        self.url = url
        self._cards = self._parse_cards(html_text)

    def locator(self, selector: str) -> _MockLocatorGroup:
        if selector in self.CARD_SELECTORS:
            return _MockLocatorGroup(self._cards)
        return _MockLocatorGroup([])

    def inner_text(self, selector: str) -> str:
        if selector != "body":
            return ""
        blocks = [card.inner_text() for card in self._cards]
        return "\n".join(blocks)

    def content(self) -> str:
        return self._html_text

    def title(self) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", self._html_text, re.S | re.I)
        return _norm_text(match.group(1)) if match else "Mock Search"

    def wait_for_load_state(self, state: str, timeout: int) -> None:
        _ = (state, timeout)

    def wait_for_function(self, script: str, timeout: int) -> None:
        _ = (script, timeout)

    @staticmethod
    def _parse_cards(html_text: str) -> list[_MockSearchCard]:
        cards: list[_MockSearchCard] = []
        for block in re.findall(
            r"<article[^>]*class=\"[^\"]*item[^\"]*\"[^>]*>(.*?)</article>",
            html_text,
            re.S | re.I,
        ):
            title_match = re.search(
                r"<div[^>]*class=\"[^\"]*title[^\"]*\"[^>]*>(.*?)</div>",
                block,
                re.S | re.I,
            )
            price_match = re.search(
                r"<div[^>]*class=\"[^\"]*price[^\"]*\"[^>]*>(.*?)</div>",
                block,
                re.S | re.I,
            )
            meta_matches = re.findall(
                r"<div[^>]*class=\"[^\"]*meta[^\"]*\"[^>]*>(.*?)</div>",
                block,
                re.S | re.I,
            )
            href_match = re.search(r"<a[^>]*href=\"([^\"]+)\"[^>]*>", block, re.S | re.I)

            title = _norm_text(title_match.group(1)) if title_match else ""
            if not title:
                continue

            cards.append(
                _MockSearchCard(
                    title=title,
                    price_line=_norm_text(price_match.group(1)) if price_match else "",
                    meta_lines=[_norm_text(item) for item in meta_matches if _norm_text(item)],
                    href=href_match.group(1).strip() if href_match else None,
                )
            )
        return cards


class _MockAddButton:
    def __init__(self, page: "_MockDetailPage", text: str) -> None:
        self._page = page
        self._text = text

    def inner_text(self) -> str:
        return self._text

    def click(self) -> None:
        self._page.success_shown = True


class _MockDetailSuccess:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self) -> str:
        return self._text


class _MockDetailPage:
    def __init__(self, *, html_text: str, url: str) -> None:
        self._html_text = html_text
        self.url = url
        self.success_shown = False
        self.title_text = self._extract_by_class("title")
        self.price_text = self._extract_by_class("price")
        self.meta_text = self._extract_by_class("meta")
        self.button_text = self._extract_button_text() or "Add to cart"
        self.success_text = "加入购物车成功 / Added to cart"

    def locator(self, selector: str) -> _MockLocatorGroup:
        if _matches_has_text_selector(selector, "button", self.button_text):
            return _MockLocatorGroup([_MockAddButton(self, self.button_text)])
        if _matches_has_text_selector(selector, "a", self.button_text):
            return _MockLocatorGroup([])
        if selector in ADD_TO_CART_SUCCESS_SELECTORS and self.success_shown:
            return _MockLocatorGroup([_MockDetailSuccess(self.success_text)])
        if selector == ".mock-add-to-cart":
            return _MockLocatorGroup([_MockAddButton(self, self.button_text)])
        return _MockLocatorGroup([])

    def inner_text(self, selector: str) -> str:
        if selector != "body":
            return ""
        lines = [self.title_text, self.price_text, self.meta_text, self.button_text]
        if self.success_shown:
            lines.append(self.success_text)
        return "\n".join(line for line in lines if line)

    def content(self) -> str:
        return self._html_text

    def title(self) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", self._html_text, re.S | re.I)
        return _norm_text(match.group(1)) if match else "Mock Detail"

    def _extract_by_class(self, class_name: str) -> str:
        match = re.search(
            rf"<[^>]*class=\"[^\"]*{re.escape(class_name)}[^\"]*\"[^>]*>(.*?)</[^>]+>",
            self._html_text,
            re.S | re.I,
        )
        return _norm_text(match.group(1)) if match else ""

    def _extract_button_text(self) -> str:
        match = re.search(
            r"<button[^>]*>(.*?)</button>",
            self._html_text,
            re.S | re.I,
        )
        return _norm_text(match.group(1)) if match else ""


@dataclass
class MockHtmlRuntime:
    """Runtime used by local mock smoke demonstration without real browser."""

    config: SkillConfig
    mock_search_url: str
    task_id: str | None = None

    def __post_init__(self) -> None:
        self._page: Any | None = None
        self._started = False

    def start(self) -> None:
        self._started = True

    def close(self) -> None:
        self._page = None
        self._started = False

    def has_storage_state(self) -> bool:
        return False

    def open_taobao_home(self) -> None:
        self.goto(self.mock_search_url)

    def search_keyword(self, keyword: str) -> None:
        _ = keyword
        self.goto(self.mock_search_url)

    def goto(self, url: str) -> None:
        path = _parse_file_url(url)
        if not path.is_absolute():
            base = _parse_file_url(self.get_page_url()) if self.get_page_url() else PROJECT_ROOT
            path = (base.parent / path).resolve()
        if not path.exists():
            raise SkillError(
                NETWORK_ERROR,
                "Mock page not found.",
                {"url": url, "resolved_path": str(path)},
            )
        html_text = path.read_text(encoding="utf-8")
        page_url = path.as_uri()
        if path.name == "search_result.html":
            self._page = _MockSearchPage(html_text=html_text, url=page_url)
            return
        if path.name == "product_detail.html":
            self._page = _MockDetailPage(html_text=html_text, url=page_url)
            return
        raise SkillError(
            NETWORK_ERROR,
            "Unsupported mock page type.",
            {"url": url, "resolved_path": str(path)},
        )

    def get_page_html(self) -> str:
        return self.require_page().content()

    def get_visible_text(self) -> str:
        return self.require_page().inner_text("body")

    def get_page_text(self) -> str:
        return self.get_visible_text()

    def get_page_title(self) -> str:
        return self.require_page().title()

    def get_page_url(self) -> str:
        page = self._page
        if page is None:
            return ""
        return str(getattr(page, "url", "") or "")

    def get_page(self) -> Any | None:
        return self._page

    def require_page(self) -> Any:
        if not self._started or self._page is None:
            raise SkillError(
                NETWORK_ERROR,
                "Mock runtime page is not available.",
                {"started": self._started},
            )
        return self._page

    def screenshot(self, path: str) -> None:
        Path(path).write_text(self.get_page_html(), encoding="utf-8")

    def is_login_page(self) -> bool:
        return False


def build_mock_payload(action: str = "add_to_cart") -> TaskPayload:
    return TaskPayload.from_dict(
        {
            "platform": "taobao",
            "keyword": "蓝牙耳机",
            "constraints": {
                "positive_rate_gte": 99,
            },
            "action": action,
            "notify_channel": "feishu",
            "max_candidates": 3,
            "need_login": False,
        }
    )


def build_mock_runtime_factory(mock_search_url: str):
    def factory(*, config: SkillConfig, task_id: str | None = None):
        return MockHtmlRuntime(
            config=config,
            task_id=task_id,
            mock_search_url=mock_search_url,
        )

    return factory


def main() -> None:
    if not MOCK_SEARCH_PAGE.exists():
        raise FileNotFoundError(f"Mock search page not found: {MOCK_SEARCH_PAGE}")

    config = SkillConfig(default_headless=True)
    orchestrator = Orchestrator(
        config=config,
        runtime_factory=build_mock_runtime_factory(MOCK_SEARCH_PAGE.resolve().as_uri()),
    )
    result = orchestrator.run(build_mock_payload(action="add_to_cart"))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

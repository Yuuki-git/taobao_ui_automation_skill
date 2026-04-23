"""Centralized selector constants.

Selectors remain intentionally minimal and can be refined in later phases.
"""

SEARCH_INPUT_SELECTOR = "input[name='q']"

# Candidate selectors used by product-parser fallback extraction.
SEARCH_RESULT_CARD_SELECTORS = (
    ".item",
    ".ctx-box",
    ".card",
    "[data-index]",
    ".m-itemlist .items .item",
)

# Detail-page add-to-cart button selectors.
ADD_TO_CART_SELECTORS = (
    "button:has-text('加入购物车')",
    "a:has-text('加入购物车')",
    "button:has-text('Add to cart')",
    "a:has-text('Add to cart')",
)

# Lightweight success feedback selectors.
ADD_TO_CART_SUCCESS_SELECTORS = (
    ".cart-success",
    ".add-cart-success",
    "[class*='cart-success']",
    ".success-msg",
)

# Simple SKU hint selectors used to identify likely manual-selection pages.
SKU_HINT_SELECTORS = (
    ".sku",
    ".sku-list",
    ".tb-sku",
    "[class*='sku']",
)

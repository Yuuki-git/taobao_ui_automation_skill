"""Centralized selector constants.

These selectors are intentionally minimal and designed to be replaced iteratively
as parser/cart implementations mature.
"""

SEARCH_INPUT_SELECTOR = "input[name='q']"

# Candidate selectors used by phase-3 parser fallback extraction.
SEARCH_RESULT_CARD_SELECTORS = (
    ".item",
    ".ctx-box",
    ".card",
    "[data-index]",
    ".m-itemlist .items .item",
)

# Candidate selectors for add-to-cart actions.
ADD_TO_CART_SELECTORS = (
    "button:has-text('加入购物车')",
    "a:has-text('加入购物车')",
    "button:has-text('Add to cart')",
    "a:has-text('Add to cart')",
)

---
name: taobao-ui-automation-skill
description: execute or demonstrate a taobao browser automation workflow for product search, constraint-based candidate filtering, optional add-to-cart, captcha/risk-control detection, and structured result reporting. use when the user asks to run, test, review, or explain the taobao ui automation skill, including local mock smoke tests, search_only flows, add_to_cart flows, and human-in-the-loop handling for login, captcha, risk-control, or complex sku cases.
---

# Taobao UI Automation Skill

## Core Behavior

This skill provides a reusable Taobao UI automation workflow that:
- validates normalized input payloads
- performs keyword search
- extracts and filters product candidates with deterministic rules
- optionally executes add-to-cart
- returns a stable structured result schema

## Expected Input

Input is a JSON object with fields such as:
- `platform`
- `keyword`
- `constraints`
- `action`
- `notify_channel`
- `max_candidates`
- `need_login`

Example (sample only, not capability boundary):

```json
{
  "platform": "taobao",
  "keyword": "蓝牙耳机",
  "constraints": {
    "positive_rate_gte": 99,
    "price_lte": 300
  },
  "action": "search_only",
  "notify_channel": "feishu",
  "max_candidates": 5,
  "need_login": false
}
```

## Output Format

Standard response fields:
- `success`
- `task_status`
- `selected_product`
- `message`
- `error_code`
- `error_detail`

Internal `task_id` is used for tracing and logging, and is not part of the standard output schema.

## Standard Workflow

1. Validate payload and normalize constraints.
2. Start runtime and open target page.
3. Check login/captcha/risk-control status.
4. Execute search and wait for parse-ready state.
5. Extract product candidates.
6. Filter and rank with constraints.
7. Return selected product for `search_only`, or continue with add-to-cart for `add_to_cart`.

## Login / Captcha / Risk-Control Policy

- The skill does not implement captcha bypass.
- Login, captcha, risk-control, and complex SKU cases are handled with human-in-the-loop semantics.
- When login is required and unavailable, return `LOGIN_REQUIRED`.
- When captcha signals are detected, return `CAPTCHA_DETECTED`.
- When risk-control signals are detected, return `RISK_CONTROL_PAGE`.
- These human-required states should map to `task_status=need_human_intervention`.

## Candidate Extraction Policy

- Candidate extraction is modular and replaceable.
- The current implementation favors deterministic DOM/locator parsing with safe fallbacks.
- Missing optional fields are allowed and represented as `None`.
- Title is required for a valid candidate.

## Filtering Policy

- Filtering is driven by `keyword` and `constraints`.
- Keyword match is case-insensitive substring matching on candidate title.
- Constraint checks include positive rate, price range, and shop-type matching.
- No matched candidate should return `NO_MATCHED_PRODUCT`.

## Add-to-Cart Policy

- Add-to-cart runs only for `action=add_to_cart`.
- The executor uses centralized selectors and success signals.
- For complex SKU pages requiring manual decision, return `SKU_SELECTION_REQUIRED`.
- If success cannot be confirmed after click + short polling, return `ADD_CART_FAILED`.

## Error Codes

Typical structured codes include:
- `INVALID_INPUT`
- `LOGIN_REQUIRED`
- `CAPTCHA_DETECTED`
- `RISK_CONTROL_PAGE`
- `SEARCH_TIMEOUT`
- `NO_MATCHED_PRODUCT`
- `ADD_CART_FAILED`
- `SKU_SELECTION_REQUIRED`
- `PAGE_STRUCTURE_CHANGED`
- `NETWORK_ERROR`
- `UNKNOWN_ERROR`

## Boundaries

- Platform scope is currently `taobao` only.
- No stealth or anti-bot plugin is required or enabled by default.
- No attempt is made to bypass captcha or risk-control restrictions.
- Complex SKU automation is intentionally limited and may require manual intervention.

## Local Mock Smoke Usage

Use local mock pages for stable end-to-end demonstration without relying on the real Taobao website:

- From workspace parent:
  - `python taobao_ui_automation_skill/tools/run_mock_smoke.py`
- From project root:
  - `python tools/run_mock_smoke.py`

The mock smoke path validates:
- candidate extraction from local search page
- deterministic filtering and best-candidate selection
- add-to-cart execution and success confirmation on local detail page

---
name: taobao-ui-automation-skill
description: taobao skill for product search, constraint filtering, optional add-to-cart, structured result reporting, and designing/executing the related browser automation workflow
---

# Taobao UI Automation Skill

## Core Behavior

This skill provides a reusable Taobao automation workflow that:
- accepts normalized task input
- performs keyword-based product search
- applies constraint-based candidate filtering
- optionally executes add-to-cart action
- returns standardized structured output for downstream use

It is a general Taobao product-search and filtering skill, not a single-item script.

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
  "keyword": "索尼耳机",
  "constraints": {
    "positive_rate_gte": 99,
    "price_lte": 3000,
    "shop_type": "flagship"
  },
  "action": "search_only",
  "notify_channel": "feishu",
  "max_candidates": 5,
  "need_login": true
}
```

## Standard Workflow

1. Validate and normalize payload.
2. Initialize browser runtime and open Taobao home.
3. Check auth state.
4. Run keyword search and wait for a parse-ready search page.
5. Extract and filter candidates.
6. Return best match for `search_only`, or continue to add-to-cart for `add_to_cart`.
7. Return standardized result and emit notifier events.

## Login-State Policy

- No complex automatic login is performed.
- Session reuse relies on persisted storage state when available.
- If login is required and not satisfied, return `LOGIN_REQUIRED`.
- Captcha and risk-control signals are surfaced as structured statuses.
- Human intervention is expected for login/captcha/risk-control cases.

## Candidate Extraction Policy

- Candidate extraction is modular and replaceable.
- Extraction should return normalized `ProductCandidate` objects.
- Parsing should prefer deterministic selectors and stable field mapping.
- Uncertain extraction should fail with explicit structured errors.

## Filtering Policy

- Filtering is driven by `keyword` and `constraints`, not hardcoded item names.
- Keyword matching is case-insensitive substring matching in the current version.
- Supported constraints include positive rate threshold, price bounds, and shop-type preference.
- No matched candidate must return `NO_MATCHED_PRODUCT`.

## Add-to-Cart Policy

- Add-to-cart is optional and only executed for `action=add_to_cart`.
- Complex SKU selection is not guaranteed in current scope.
- SKU ambiguity should return structured failure (for example `SKU_SELECTION_REQUIRED`).

## Output Format

Standard response fields:
- `success`
- `task_status`
- `selected_product`
- `message`
- `error_code`
- `error_detail`

Internal `task_id` is for logging/tracing and is not part of the standard output schema.

## Error Codes

Common codes include:
- `INVALID_INPUT`
- `LOGIN_REQUIRED`
- `CAPTCHA_DETECTED`
- `RISK_CONTROL_PAGE`
- `SEARCH_TIMEOUT`
- `NO_SEARCH_RESULT`
- `NO_MATCHED_PRODUCT`
- `DETAIL_PARSE_FAILED`
- `ADD_CART_FAILED`
- `SKU_SELECTION_REQUIRED`
- `PAGE_STRUCTURE_CHANGED`
- `NETWORK_ERROR`
- `UNKNOWN_ERROR`

## Failure-Handling Rules

- Use structured exceptions and structured result mapping.
- Do not swallow exceptions silently.
- Preserve stable output contract on both success and failure.
- Prefer explicit error code + message + detail over ambiguous fallback text.

## Non-Functional Rules

- Keep modules focused and loosely coupled.
- Preserve deterministic behavior where possible.
- Use logging with internal task correlation.
- Avoid unnecessary heavy dependencies.

## Reporting Rules

- Always return standardized output object.
- Ensure result is human-readable (`message`) and machine-readable (`error_code`, `error_detail`).
- Keep notifier behavior replaceable; current implementation may be log-first.

## Boundaries

- Current platform scope is Taobao only.
- No captcha bypass guarantees.
- No guarantee for fully automated complex SKU flows.
- Do not hardcode sample keyword/brand terms into business logic.

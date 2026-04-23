---
name: taobao_ui_automation_skill
description: General Taobao product search and filtering skill scaffold with structured outputs.
version: 0.2.0-phase2
status: phase2
---

# Skill Contract

## Inputs

```json
{
  "platform": "taobao",
  "keyword": "bluetooth headset",
  "constraints": {
    "positive_rate_gte": 99,
    "price_lte": 3000,
    "price_gte": 1000,
    "shop_type": "flagship"
  },
  "action": "search_only",
  "notify_channel": "feishu",
  "max_candidates": 5,
  "need_login": true
}
```

Notes:
- `platform` currently supports only `taobao`
- `shop_type` is free-form in validation, with loose matching planned in parser logic

## Outputs

```json
{
  "success": true,
  "task_status": "completed",
  "selected_product": {
    "title": "Example Product",
    "price": 2399.0,
    "positive_rate": 99.4,
    "shop_name": "Example Shop",
    "product_url": "https://example.com/product/123",
    "comment_count": 12000,
    "confidence": 0.88,
    "source_page": "search"
  },
  "message": "Task completed",
  "error_code": null,
  "error_detail": null
}
```

## Phase 2 Execution Flow

1. `run_skill(payload)` validates payload and initializes `task_id`
2. orchestrator starts browser runtime and opens Taobao home
3. auth manager checks login/captcha/risk states
4. runtime performs keyword search and waits for search-result page readiness
5. parser/cart modules are still basic placeholders until phase3 completion
6. notifier logs success/failure events

## Failure Cases

- `INVALID_INPUT`
- `LOGIN_REQUIRED`
- `CAPTCHA_DETECTED`
- `RISK_CONTROL_PAGE`
- `NO_SEARCH_RESULT`
- `NO_MATCHED_PRODUCT`
- `ADD_CART_FAILED`
- `SKU_SELECTION_REQUIRED`
- `UNKNOWN_ERROR`

---
title: taobao_ui_automation_skill
status: phase2
last_updated: 2026-04-23
---

# taobao_ui_automation_skill

Taobao UI automation skill scaffold for standardized input/output, flow orchestration,
and incremental module evolution.

## Current Status (Phase 2)

Implemented:
- standardized dataclass models and input validation
- unified error codes and `SkillError`
- `run_skill(payload)` entry with structured error mapping
- orchestrator-level flow coordination
- Playwright runtime lifecycle wrapper
- authentication status checks (no complex auto-login)
- notifier interface with log output

Not implemented yet:
- robust product candidate extraction/parsing
- advanced filter scoring policy refinements
- full add-to-cart action automation across complex SKU flows

## Environment

- Python 3.10+
- Playwright

## Install

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

```python
from main import run_skill

payload = {
    "platform": "taobao",
    "keyword": "bluetooth headset",
    "constraints": {"positive_rate_gte": 99},
    "action": "search_only",
    "notify_channel": "feishu",
    "max_candidates": 5,
    "need_login": True,
}

result = run_skill(payload)
print(result)
```

## Validation Rules

- `platform` must be `taobao`
- `keyword` is required and cannot be empty
- `action` must be `search_only` or `add_to_cart`
- conflicting price constraints (`price_gte > price_lte`) are rejected as `INVALID_INPUT`
- `shop_type` accepts free-form strings (no strict enum validation)

## Runtime Notes

- `task_id` is generated internally for logs/tracing and is not returned in standard output
- captcha/risk pages are detected and surfaced as structured statuses
- no captcha bypass or stealth plugin dependency is required

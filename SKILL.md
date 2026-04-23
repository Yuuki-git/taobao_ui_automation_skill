# Skill Metadata

- name: `taobao_ui_automation_test_skill`
- description: 通用商品搜索与筛选的淘宝 UI 自动化 Skill 骨架
- version: `0.1.0-phase1`

## Inputs

```json
{
  "platform": "taobao",
  "keyword": "索尼耳机",
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

说明：
- `platform` 目前仅支持 `taobao`
- `shop_type` 当前允许自由字符串，做宽松约束

## Outputs

```json
{
  "success": true,
  "task_status": "completed",
  "selected_product": {
    "title": "示例商品",
    "price": 2399,
    "positive_rate": 99.4,
    "shop_name": "示例店铺",
    "product_url": "https://example.com/product/123",
    "comment_count": 12000,
    "confidence": 0.88,
    "source_page": "search"
  },
  "message": "任务执行完成",
  "error_code": null,
  "error_detail": null
}
```

## Execution Flow

1. `run_skill(payload)` 执行输入校验并生成 `task_id`
2. 初始化 orchestrator（第一阶段为占位实现）
3. 返回标准化结构结果（成功或结构化错误）

## Failure Cases

- 输入不合法：`INVALID_INPUT`
- 未登录：`LOGIN_REQUIRED`
- 验证码：`CAPTCHA_DETECTED`
- 风控页：`RISK_CONTROL_PAGE`
- 无搜索结果：`NO_SEARCH_RESULT`
- 无匹配商品：`NO_MATCHED_PRODUCT`
- 加购失败：`ADD_CART_FAILED` / `SKU_SELECTION_REQUIRED`
- 未知异常：`UNKNOWN_ERROR`

# Taobao UI Automation Test Skill

一个面向淘宝场景的 UI 自动化测试 Skill 工程骨架。当前目标是提供统一输入输出契约、错误码体系、入口调用方式和可扩展模块边界。

## 当前阶段

当前为第一阶段：
- 已完成：目录结构、输入模型、错误码、统一入口、基础文档、测试骨架
- 待完成：Orchestrator 流程、Playwright 运行时封装、认证/候选提取/加购等业务模块

## 环境要求

- Python 3.10+
- Playwright（后续阶段用于浏览器自动化）

## 安装

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 调用方式

```python
from main import run_skill

payload = {
    "platform": "taobao",
    "keyword": "索尼耳机",
    "constraints": {"positive_rate_gte": 99},
    "action": "search_only",
    "notify_channel": "feishu",
    "max_candidates": 5,
    "need_login": True,
}

result = run_skill(payload)
print(result)
```

## 输入校验规则（第一阶段已生效）

- `platform` 仅支持 `taobao`，其他值返回 `INVALID_INPUT`
- `keyword` 必填，且不能是空字符串
- `action` 必填，仅支持 `search_only` / `add_to_cart`
- `constraints.price_gte > constraints.price_lte` 时返回 `INVALID_INPUT`
- `shop_type` 接受自由字符串，不做强枚举校验

## 返回约定

- 返回结构遵循标准 schema：`success/task_status/selected_product/message/error_code/error_detail`
- 内部会生成 `task_id` 用于日志追踪，但不会加入标准返回体

## 已知限制

- 当前版本不会绕过验证码与风控页
- 当前版本不会实现复杂自动登录与复杂 SKU 自动选择
- 第一阶段的业务编排模块仍为占位实现（会在后续阶段补齐）

# Taobao UI Automation Skill

## 项目概览
本项目是一个面向 OpenClaw Skill 形态的淘宝 UI 自动化工程，核心能力包括：
- 关键词搜索
- 基于约束的候选商品筛选
- 可选的加入购物车动作
- 结构化结果返回

项目目标是提供可测试、可复用、可稳定演示的自动化流程，而不是一次性脚本。

## 当前实现状态
已实现模块：
- `main.py`
- `models.py`
- `config.py`
- `modules/browser_runtime.py`
- `modules/auth_manager.py`
- `modules/product_parser.py`
- `modules/cart_executor.py`
- `modules/orchestrator.py`
- `modules/notifier.py`
- `modules/error_codes.py`
- `modules/selectors.py`
- `tools/run_mock_smoke.py`
- `mock_pages/*`
- `tests/*`

## OpenClaw 兼容性
- 本项目按 OpenClaw 风格组织为 Skill 工程。
- 根目录的 `SKILL.md` 提供 skill 元数据与使用说明。
- 本地 mock smoke 脚本可在不依赖真实淘宝站点的前提下验证完整执行闭环。

## 输入 / 输出契约
输入字段（核心）：
- `platform`
- `keyword`
- `constraints`
- `action`
- `notify_channel`
- `max_candidates`
- `need_login`

输出字段（最小稳定 schema）：
- `success`
- `task_status`
- `selected_product`
- `message`
- `error_code`
- `error_detail`

## 本地 Mock Smoke 演示
在工作区上级目录运行：

```bash
python taobao_ui_automation_skill/tools/run_mock_smoke.py
```

在项目根目录运行：

```bash
python tools/run_mock_smoke.py
```

示例输出：

```json
{
  "success": true,
  "task_status": "completed",
  "selected_product": {
    "title": "蓝牙耳机 B",
    "price": 299.0,
    "positive_rate": 99.3,
    "shop_name": "官方旗舰店",
    "product_url": "file:///.../mock_pages/product_detail.html?sku=b",
    "comment_count": 12000,
    "confidence": null,
    "source_page": "search_result"
  },
  "message": "Task completed and product added to cart.",
  "error_code": null,
  "error_detail": null
}
```

## 真实淘宝联调说明
- 真实淘宝链路已验证到验证码/风控边界。
- 支持通过 `storage_state` 做会话复用，但真实联调中仍可能触发验证页。
- 项目当前策略是结构化识别并返回边界状态，而不是尝试绕过风控。

## 验证码 / 风控边界
- 检测到验证码信号（如滑块验证）时，返回 `CAPTCHA_DETECTED`。
- 检测到风控或访问受限信号时，返回 `RISK_CONTROL_PAGE`。
- 上述情况统一映射为 `task_status=need_human_intervention`。
- 不实现验证码或风控绕过逻辑。

## 测试命令

```bash
python -m pytest -q
```

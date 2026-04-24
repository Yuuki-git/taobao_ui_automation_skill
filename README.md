# Taobao UI Automation Skill

## 项目简介
`Taobao UI Automation Skill` 是一个面向 Skill 化调用的淘宝自动化工程骨架。  
项目目标是提供稳定的输入输出契约、可测试的模块边界和可迭代的自动化流程，而不是一次性脚本。

## 当前实现状态
已完成核心模块：
- `models.py`
- `main.py`
- `modules/error_codes.py`
- `modules/orchestrator.py`
- `modules/browser_runtime.py`
- `modules/auth_manager.py`
- `modules/notifier.py`
- `modules/product_parser.py`
- `modules/cart_executor.py`
- `modules/selectors.py`

## 输入输出契约概览
输入字段（核心）：
- `platform`
- `keyword`
- `constraints`
- `action`
- `notify_channel`
- `max_candidates`
- `need_login`

标准输出最小集合：
- `success`
- `task_status`
- `selected_product`
- `message`
- `error_code`
- `error_detail`

## 本地 Mock 闭环演示
为了稳定演示完整流程，项目提供本地 mock 页面与 smoke 脚本，不依赖真实淘宝页面：

运行命令：

```bash
python taobao_ui_automation_skill/tools/run_mock_smoke.py
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
    "product_url": "file:///D:/taobao-ui-automation-test/taobao_ui_automation_skill/mock_pages/product_detail.html?sku=b",
    "comment_count": 12000,
    "confidence": null,
    "source_page": "search_result"
  },
  "message": "Task completed and product added to cart.",
  "error_code": null,
  "error_detail": null
}
```

说明：
- 真实淘宝联调可能在搜索阶段触发验证码或风控页（例如滑块验证）。
- mock 闭环用于稳定演示“搜索提取 -> 约束筛选 -> 加购执行 -> 标准结果返回”的完整路径。

## 运行与测试
安装依赖：

```bash
pip install -r taobao_ui_automation_skill/requirements.txt
```

运行测试：

```bash
python -m pytest -q
```

## 当前边界
- 不尝试绕过验证码或风控机制。
- 不承诺复杂 SKU 的全自动决策。
- 当前平台范围仅支持 `taobao`。
- 保持既有标准输出 schema，不额外添加破坏性字段。

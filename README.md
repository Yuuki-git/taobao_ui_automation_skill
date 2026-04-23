# Taobao UI Automation Skill

## 项目简介

`Taobao UI Automation Skill` 是一个兼容 skill 思路的 Taobao 浏览器自动化工程骨架。  
目标是提供标准化输入输出、清晰模块边界、可持续迭代的自动化流程，而不是一次性脚本。

## 当前实现状态

已完成：
- `models.py`
- `main.py`
- `modules/error_codes.py`
- `modules/orchestrator.py`
- `modules/browser_runtime.py`
- `modules/auth_manager.py`
- `modules/notifier.py`

未完成 / 占位：
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

标准输出最小集：
- `success`
- `task_status`
- `selected_product`
- `message`
- `error_code`
- `error_detail`

## 关键设计原则

- 通用商品搜索 skill，不是单商品脚本
- human-in-the-loop（登录、验证码、风控等人工介入场景可被结构化返回）
- session reuse（优先复用 storage state）
- deterministic parsing first（优先稳定、可测、可维护的解析路径）

## 运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

安装 Playwright 浏览器：

```bash
python -m playwright install chromium
```

运行测试：

```bash
python -m pytest -q
```

## 当前边界说明

- 不自动绕过验证码
- 不承诺复杂 SKU 全自动化
- 当前仅支持 `taobao`

## 测试状态

phase1 + phase2 的测试已建立并持续验证核心契约与流程行为，包括：
- 输入校验与标准输出
- runtime 生命周期与基础操作
- auth 状态判定行为
- orchestrator 编排层关键路径

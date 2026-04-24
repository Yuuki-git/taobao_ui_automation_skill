# 设计与效果评估

## 背景
本项目在真实淘宝联调中已验证到登录/验证码/风控边界，同时已补充本地 mock 闭环用于稳定演示完整流程。

## 效果评估

### 真实淘宝联调结果
- 联调阶段在搜索流程触发滑动验证码页面，出现“请拖动下方滑块完成验证”等提示。
- 人工验证操作失败时，流程不应继续落为通用超时。
- 当前策略为结构化返回人工介入状态：
  - `error_code = CAPTCHA_DETECTED`
  - `task_status = need_human_intervention`
- 若命中风控访问限制页，则返回：
  - `error_code = RISK_CONTROL_PAGE`
  - `task_status = need_human_intervention`

### Mock 完整闭环验证
- 使用本地 `mock_pages/search_result.html` 和 `mock_pages/product_detail.html` 进行稳定演示。
- 已验证 `search_only` 路径：可完成候选提取与筛选，并返回 `selected_product`。
- 已验证 `add_to_cart` 路径：可打开本地详情页、执行加购并识别成功信号，最终返回 `completed`。

## 结论
- 真实淘宝路径已明确验证码/风控边界并采用 human-in-the-loop 返回。
- 本地 mock 路径可稳定复现完整业务闭环，适合作为演示与回归验证基线。

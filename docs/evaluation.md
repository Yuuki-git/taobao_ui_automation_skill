# Design And Evaluation

## Real Taobao Integration Result
- Storage state was generated and loaded for session reuse.
- During real Taobao search stage, slider captcha was triggered.
- Manual slider verification attempt failed.
- The system behavior expectation is:
  - `error_code = CAPTCHA_DETECTED`
  - `task_status = need_human_intervention`
- For risk-control / restricted access pages, the system behavior expectation is:
  - `error_code = RISK_CONTROL_PAGE`
  - `task_status = need_human_intervention`
- The project explicitly does not attempt to bypass captcha or risk-control.

## Mock End-To-End Verification
- Local mock pages are used to validate a complete stable loop without real Taobao dependency.
- `search_only` flow is validated end-to-end and returns `selected_product`.
- `add_to_cart` flow is validated end-to-end and returns `completed`.
- `ProductParser` successfully extracts candidates from local mock search result cards.
- `CartExecutor` successfully identifies add-to-cart success signals on mock detail page.
- Full test suite passes (`python -m pytest -q`).

## Conclusion
- Real Taobao boundary handling is confirmed (captcha/risk-control -> human-in-the-loop).
- Local mock smoke path is confirmed as the reliable demo and regression baseline for the complete skill workflow.

# 接口自动化（Day 2 产出）

- 技术栈：Python + requests + pytest
- 结构：
  - `conftest.py` — 登录态 fixture（session / token 复用）
  - `test_*.py` — 测试用例
  - `data/` — 参数化数据（csv / yaml）
- 运行：`pytest -v --html=reports/report.html`

## 待填（Day 2 完成后补）
1. 被测接口清单（URL / 方法 / 参数 / 预期）
2. 覆盖场景：正常流程、参数异常、未登录、越权
3. 运行结果截图

# UI 自动化（Day 3 产出）

- 技术栈：Selenium + Page Object
- 结构：
  - `pages/` — 页面对象（元素定位 + 操作封装）
  - `tests/` — 用例层只调用页面对象方法
  - `conftest.py` — driver 初始化与退出
- 要点：显式等待替代 sleep；定位优先 id / css，避免绝对 xpath 和动态 id

## 待填（Day 3 完成后补）
1. 覆盖流程：登录 → 主功能 → 断言
2. 稳定性处理：显式等待、失败截图
3. 运行录屏 / 结果截图

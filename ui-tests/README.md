# UI 自动化 · course-rag-agent 前端

Selenium + Page Object，只覆盖主干冒烟，用于验证"用户真的点得动"。

## 运行方式

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 前置：前端已启动
cd <course-rag-agent>/frontend
npm install && npm run dev        # http://localhost:5173

# 跑
pytest
set HEADLESS=1 && pytest          # 无头模式（Windows PowerShell: $env:HEADLESS=1）
```

环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `FRONTEND_URL` | `http://localhost:5173` | 前端地址 |
| `TEST_DOCX` | 无 | 上传用例的课件绝对路径，不设则该用例 skip |
| `HEADLESS` | 无 | 设为 `1` 走无头 |

## 目录结构

```
ui-tests/
├── conftest.py                     # driver 生命周期 + 前端不通则 skip + 失败自动截图
├── pages/
│   ├── base_page.py                # 显式等待、多候选定位、等文本出现
│   ├── chat_page.py                # 问答页
│   └── knowledge_base_page.py      # 知识库管理页
└── tests/test_ui_smoke.py          # 4 条冒烟
```

## 必读：定位器要自己校准

`pages/*.py` 里的选择器是**按 Vue + Element Plus 的常见结构写的候选列表**，不是从你的页面里抓的真实值。
第一次跑之前必须做这一步：

1. 浏览器打开前端 → F12 → 用选择工具点中目标元素
2. 右键 → Copy → Copy selector
3. 把真实选择器**加到候选列表第一位**（保留原有候选，提高稳定性）

Element Plus 的两个坑：
- 输入框真实输入节点是 `.el-textarea__inner`，外面套 `el-textarea`，且部分版本 class 带随机后缀 → 用 `[class^='el-textarea']` 前缀匹配更稳
- 按钮常无稳定 id → 用 `//button[contains(., '发送')]` 文本匹配

## 稳定性设计（面试可以直接讲）

- **显式等待替代 sleep**：等到"可点击/可见"就返回，最多等 15s（问答区等 90s）
- **多候选定位**：`find_first(*locators)` 依次尝试，降低改版即挂的概率
- **失败自动截图**：`pytest_runtest_makereport` 钩子，截图存 `screenshots/`
- **前端不通整体 skip**：不让环境问题伪装成用例失败

## 为什么不铺更多 UI 用例

同一个流程：接口层 3 秒、UI 层 25 秒。**回归主力放接口层，UI 只保主干**——这是 ROI 的选择，不是偷懒。

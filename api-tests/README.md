# 接口自动化 · course-rag-agent

Python + requests + pytest 实现的接口自动化，覆盖被测系统 6 个接口。

## 运行方式

```bash
# 1) 装依赖（首次）
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2) 启动被测系统（另一个终端）
cd <course-rag-agent>/backend
uvicorn main:app --port 8000

# 3) 跑测试
pytest                            # 全量
pytest -m smoke                   # 只跑冒烟
pytest -m negative                # 只跑负向用例
pytest -k chat                    # 只跑问答
pytest --html=reports/report.html --self-contained-html   # 出 HTML 报告
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `BASE_URL` | `http://127.0.0.1:8000` | 被测服务地址 |
| `TEST_DOCX` | 自动查找 | 测试课件路径（自动找 `data/`、同级 `course-rag-agent/backend/`） |

## 目录结构

```
api-tests/
├── config.py                # 地址、超时、契约常量（拒答话术、错误提示关键字）
├── conftest.py              # fixture：session 复用、课件前置、服务不可用则整体 skip
├── utils/
│   ├── api_client.py        # 接口封装：把"怎么调"和"断言什么"分开
│   └── assert_helper.py     # 统一断言：失败时带 URL / 请求体 / 响应体
├── data/questions.json      # 测试数据：课内 / 课外 / 非法入参 / 注入用例
├── test_health.py
├── test_documents.py
├── test_chat.py
└── test_evaluations.py
```

## 覆盖清单（共 25 条，以 `pytest --collect-only -q` 实测为准）

| 文件 | 条数 | 覆盖点 |
|---|---|---|
| test_health.py | 3 | 存活、响应时间、依赖状态（默认 skip，需人为制造故障） |
| test_documents.py | 10 | 上传正向、不支持格式、空文件、扩展名伪装、伪造 pdf 头、缺字段、路径穿越、列表、删除（存在/不存在） |
| test_chat.py | 10 | 课内作答（5）、课外拒答（4）、非法入参（5）、Prompt 注入、响应时间、并发不串台 |
| test_evaluations.py | 2 | 返回结构、提问后记录增长 |

## 断言原则（这是这套脚本和"能跑就行"的区别）

1. **按需求写断言，不按实际返回写。** 例如"删除不存在的文档应返回 404"——如果实现返回 500，这条就失败，而**失败本身就是缺陷证据**。
2. **断言四件套**：状态码 + 关键业务字段 + 错误提示语义 + 响应时间。
3. **数据自造自清**：`temp_doc` fixture 造的文档，用例结束自动删除；`uploaded_doc` 是会话级前置，不删（问答依赖它）。
4. **失败信息要自带现场**：URL、请求体、响应体都打出来，不用重跑去复现。

## 已知会失败的用例（失败 = 缺陷线索，不是脚本写错）

| 用例 | 预期失败原因 | 对应缺陷线索 |
|---|---|---|
| `test_upload_invalid_file[扩展名伪装被拒绝]` | 后端只校验扩展名不校验内容，可能返回 500 而非 400 | 线索 2 |
| `test_upload_path_traversal_filename` | 文件名直接拼路径，未拒绝 `../` | 线索 3 |
| `test_delete_nonexistent_document` | 未做存在性校验，可能返回 500 而非 404 | 线索 1 |
| `test_chat_invalid_input[纯空格]` | `min_length=1` 挡不住空白字符 | 线索 6 |

跑完后请把结果填进 `../test-cases/course-rag-agent-接口测试用例.csv` 的"执行结果"列，并把确认的缺陷写成报告（模板见 `../bug-reports/`）。

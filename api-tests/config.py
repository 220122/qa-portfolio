"""全局配置：环境地址、超时、契约常量。

BASE_URL 支持用环境变量覆盖，方便从本地切到测试环境：
    $env:BASE_URL="http://192.168.1.10:8000"; pytest
"""
import os

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# 普通接口超时（秒）
TIMEOUT = 30
# 大模型问答超时：真实耗时常在几十秒，给 30s 会全是误报
CHAT_TIMEOUT = 120
# 文件上传（首次会下载向量化模型，给足时间）
UPLOAD_TIMEOUT = 600

# ---- 契约常量：来自 README 与被测系统实际返回 ----
HEALTH_OK = {"status": "ok"}
UPLOAD_ERROR_KEYWORD = "仅支持"          # detail 提示含"仅支持 PDF / DOCX 格式文件"
REFUSAL_KEYWORD = "没有该知识点"          # 课外问题的固定拒答话术
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# 已知接口清单，用于契约连通性检查
ENDPOINTS = [
    ("GET", "/api/health"),
    ("GET", "/api/documents"),
    ("POST", "/api/documents/upload"),
    ("DELETE", "/api/documents/{doc_id}"),
    ("POST", "/api/chat"),
    ("GET", "/api/evaluations"),
]

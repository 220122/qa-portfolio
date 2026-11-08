"""pytest 共享 fixture。

设计原则
1. 贵的前置用 session scope（上传课件要解析 + 向量化，一次就够）
2. 会改数据的用 function scope，用完自清理（避免用例互相污染）
3. 环境没准备好时显式 skip，而不是让整套用例一片红
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import requests

from config import BASE_URL, TIMEOUT
from utils.api_client import list_documents, upload_docx

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_DOCX_NAMES = ["操作系统课程知识库.docx", "测试课件.docx"]


def _find_docx() -> "Path | None":
    """按 环境变量 → data 目录 → 上级目录 的顺序找测试课件。"""
    env_path = os.getenv("TEST_DOCX", "").strip()
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    for name in DEFAULT_DOCX_NAMES:
        p = DATA_DIR / name
        if p.is_file():
            return p

    # 常见情况：course-rag-agent 克隆在本仓库的同级或附近目录
    patterns = [
        "course-rag-agent/backend/*.docx",
        "*course-rag-agent*/backend/*.docx",
        "new-chat/course-rag-agent/backend/*.docx",
        "*/course-rag-agent/backend/*.docx",
    ]
    for base in list(Path(__file__).resolve().parents)[:3]:
        for pat in patterns:
            hits = sorted(base.glob(pat))
            if hits:
                return hits[0]
    return None


@pytest.fixture(scope="session")
def api():
    """整个会话复用一个 Session：复用连接，统一请求头。"""
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    yield s
    s.close()


@pytest.fixture(scope="session")
def test_data():
    with open(DATA_DIR / "questions.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def docx_path():
    p = _find_docx()
    if p is None:
        pytest.skip(
            "未找到测试课件：请设置环境变量 TEST_DOCX 指向 .docx 文件，"
            "或把课件放进 api-tests/data/ 目录"
        )
    return p


@pytest.fixture(scope="session")
def uploaded_doc(api):
    """保证知识库非空：已有文档就复用，没有才上传。

    注意：这里**不依赖 docx_path**——知识库已有文档时，不该因为本地找不到课件
    就把整个问答/评测组都 skip 掉（这是第一版 fixture 的设计缺陷，已修正）。
    """
    r = list_documents(api)
    existing = r.json() if r.status_code == 200 else []
    if existing:
        return existing[0]

    p = _find_docx()
    if p is None:
        pytest.skip(
            "知识库为空且未找到测试课件：设置 TEST_DOCX 指向 .docx，"
            "或把课件放进 api-tests/data/"
        )
    return upload_docx(api, p)


@pytest.fixture
def temp_doc(api, docx_path):
    """function 级：上传一份临时文档，用例结束自动删除（用于验证删除接口）。"""
    doc = upload_docx(api, docx_path)
    yield doc
    api.delete(f"{BASE_URL}/api/documents/{doc['doc_id']}", timeout=TIMEOUT)


@pytest.fixture(scope="session", autouse=True)
def _health_gate(api):
    """会话开始前确认服务可用，不可用就整体 skip 并给出启动命令。"""
    try:
        r = api.get(f"{BASE_URL}/api/health", timeout=5)
        ok = r.status_code == 200
    except requests.exceptions.RequestException:
        ok = False
    if not ok:
        pytest.skip(
            f"后端不可用：{BASE_URL}/api/health 不通。\n"
            f"启动方式：cd backend && uvicorn main:app --port 8000"
        )

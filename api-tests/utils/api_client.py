"""被测系统的最小 API 客户端封装。

把"怎么调"和"断言什么"分开：接口变更只改这里，用例层不动。
"""
from pathlib import Path

from config import BASE_URL, CHAT_TIMEOUT, DOCX_MIME, TIMEOUT, UPLOAD_TIMEOUT


def health(session):
    return session.get(f"{BASE_URL}/api/health", timeout=5)


def upload_docx(session, path: Path) -> dict:
    """上传 .docx，返回 document 字典。上传失败会抛 AssertionError 带响应体。"""
    with open(path, "rb") as f:
        files = {"file": (path.name, f, DOCX_MIME)}
        r = session.post(
            f"{BASE_URL}/api/documents/upload", files=files, timeout=UPLOAD_TIMEOUT
        )
    assert r.status_code == 200, f"上传失败 {r.status_code}: {r.text[:300]}"
    return r.json()["document"]


def upload_raw(session, filename: str, content: bytes, mime: str):
    """上传任意内容（用于格式伪装、空文件等负向用例）。"""
    return session.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": (filename, content, mime)},
        timeout=UPLOAD_TIMEOUT,
    )


def list_documents(session):
    return session.get(f"{BASE_URL}/api/documents", timeout=TIMEOUT)


def delete_document(session, doc_id: str):
    return session.delete(f"{BASE_URL}/api/documents/{doc_id}", timeout=TIMEOUT)


def chat(session, question):
    return session.post(
        f"{BASE_URL}/api/chat", json={"question": question}, timeout=CHAT_TIMEOUT
    )


def chat_raw(session, payload: dict):
    """发送任意请求体（用于校验非法入参、缺字段）。"""
    return session.post(f"{BASE_URL}/api/chat", json=payload, timeout=TIMEOUT)


def evaluations(session):
    return session.get(f"{BASE_URL}/api/evaluations", timeout=TIMEOUT)

"""文档管理接口用例：上传 / 列表 / 删除。

负向用例的断言是**按需求与 HTTP 语义**写的，不是按当前实现写的：
如果跑出来是 500 而断言要 4xx，这条失败就是缺陷证据（见 docs/风险点排查-course-rag-agent.md）。
"""
import pytest

from config import BASE_URL, DOCX_MIME, UPLOAD_ERROR_KEYWORD
from utils.api_client import (
    delete_document,
    list_documents,
    upload_docx,
    upload_raw,
)
from utils.assert_helper import assert_contains, assert_fields, assert_status


# ---------------- 上传：正向 ----------------

@pytest.mark.smoke
def test_upload_docx_success(api, docx_path):
    doc = upload_docx(api, docx_path)
    assert_fields(doc, ["doc_id", "filename", "chunk_count"], "上传响应 document")
    assert doc["chunk_count"] > 0, f"切块数为 0，说明解析或入库失败: {doc}"
    assert doc["filename"], "filename 为空"


# ---------------- 上传：负向 ----------------

@pytest.mark.negative
@pytest.mark.parametrize(
    "filename, content, mime, case",
    [
        ("测试.txt", b"hello", "text/plain", "不支持的扩展名"),
        ("空文件.docx", b"", DOCX_MIME, "空文件"),
        ("伪装.docx", "这是纯文本，不是真正的 docx".encode("utf-8"), DOCX_MIME, "扩展名伪装"),
        ("伪装.pdf", b"%PDF-1.4 fake", "application/pdf", "伪造 pdf 文件头"),
    ],
    ids=["txt被拒绝", "空文件被拒绝", "扩展名伪装被拒绝", "伪造pdf头被拒绝"],
)
def test_upload_invalid_file(api, filename, content, mime, case):
    """用户输入错误应该是 4xx（客户端错误），不是 500（服务端故障）。

    若实际返回 500，说明后端把"用户传错文件"当成了"服务异常"——
    上游无法区分该重试还是该改参数，这就是缺陷。
    """
    r = upload_raw(api, filename, content, mime)
    assert r.status_code == 400, (
        f"[{case}] 期望 400（客户端错误），实际 {r.status_code}\n"
        f"响应体: {r.text[:300]}"
    )
    assert_contains(r.text, UPLOAD_ERROR_KEYWORD, f"[{case}] 错误提示应可读")


@pytest.mark.negative
def test_upload_missing_file_field(api):
    """缺 file 字段应在参数校验层被拦截（FastAPI 默认 422）。"""
    r = api.post(f"{BASE_URL}/api/documents/upload", files={}, timeout=30)
    assert r.status_code in (400, 422), f"缺 file 字段应被参数校验拦截，实际 {r.status_code}"


@pytest.mark.negative
def test_upload_path_traversal_filename(api, docx_path):
    """文件名路径穿越：filename 里带 ../ 时不应写到 upload_dir 之外。

    这条用例对应风险评估项 R-03（见 docs/风险点排查-course-rag-agent.md）。
    """
    with open(docx_path, "rb") as f:
        r = api.post(
            f"{BASE_URL}/api/documents/upload",
            files={"file": ("../../evil.docx", f, DOCX_MIME)},
            timeout=120,
        )
    # 期望：拒绝（400）或安全地重命名落盘；不接受 200 且文件名保留 ../
    assert r.status_code in (400, 422), (
        f"文件名含路径穿越未被拒绝，实际 {r.status_code}: {r.text[:200]}\n"
        f"需检查是否被写到 upload_dir 之外"
    )


# ---------------- 列表 ----------------

@pytest.mark.smoke
def test_list_documents(api, uploaded_doc):
    r = list_documents(api)
    assert_status(r, 200, "文档列表")
    docs = r.json()
    assert isinstance(docs, list), f"返回应为数组，实际: {type(docs)}"
    assert docs, "知识库应至少有 1 份文档（uploaded_doc 前置保证）"
    for d in docs:
        assert_fields(d, ["doc_id", "filename", "chunk_count"], "文档列表元素")


# ---------------- 删除 ----------------

@pytest.mark.smoke
def test_delete_existing_document(api, temp_doc):
    doc_id = temp_doc["doc_id"]
    r = delete_document(api, doc_id)
    assert_status(r, 200, "删除已有文档")

    after = list_documents(api).json()
    assert doc_id not in [d.get("doc_id") for d in after], "删除后列表仍包含该文档"


@pytest.mark.negative
def test_delete_nonexistent_document(api):
    """REST 语义：资源不存在应返回 404，而不是 500。

    当前实现未做存在性校验，可能返回 500（对应 R-01）。
    """
    r = delete_document(api, "not_exist_123456")
    assert r.status_code == 404, (
        f"删除不存在的文档：期望 404，实际 {r.status_code}\n响应体: {r.text[:300]}"
    )

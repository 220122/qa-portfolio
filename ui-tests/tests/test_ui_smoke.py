"""UI 冒烟用例：只覆盖主干（打开 → 提问 → 看到回答），不追求全覆盖。

为什么不铺开：UI 自动化慢且脆，回归主力应该放接口层。
这里保留 3 条冒烟用例，价值在于证明"用户真的点得动"，
以及做接口层覆盖不到的事：前端渲染、提示文案、交互态。
"""
import os

import pytest

from pages.chat_page import ChatPage
from pages.knowledge_base_page import KnowledgeBasePage

pytestmark = pytest.mark.ui


def test_open_home(driver, base_url):
    """首页能打开，且渲染出标题（最基本的可用性）。"""
    driver.get(base_url)
    assert "课程" in driver.title or "知识问答" in driver.page_source, (
        f"页面未正确渲染，title={driver.title!r}"
    )


def test_chat_page_has_input(driver, base_url):
    """问答页的输入框与发送按钮存在（元素存在性检查，先于交互）。"""
    page = ChatPage(driver)
    page.open_page(base_url)
    box = page.find_first(*page.INPUT)
    assert box.is_displayed(), "输入框不可见"
    page.find_first(*page.SEND)


def test_ask_question_shows_answer(driver, base_url):
    """提问后回答区出现文字。

    前置：知识库里已有课件（否则会得到拒答话术，这也算通过——
    只要"有输出"，说明前后端链路通）。
    """
    page = ChatPage(driver)
    page.open_page(base_url)
    answer = page.ask("文件的物理结构有哪几种？")
    assert answer.strip(), "回答区没有出现任何文字"


def test_upload_docx(driver, base_url):
    """上传课件：直接给 input[type=file] 发路径，绕过系统弹窗。"""
    path = os.getenv("TEST_DOCX", "")
    if not path or not os.path.isfile(path):
        pytest.skip("未设置 TEST_DOCX 或文件不存在")

    page = KnowledgeBasePage(driver)
    page.open_page(base_url)
    page.upload(path)
    # 上传后列表应出现该文件名（等待向量化可能需要几十秒）
    rows = page.row_texts()
    assert any(os.path.basename(path) in r for r in rows), (
        f"上传后列表未出现该文件，当前列表: {rows}"
    )

"""智能问答页（ChatView.vue）的页面对象。

⚠️ 定位器需要你按实际页面校准：打开 F12 → 选中元素 → 右键 Copy selector，
   把下面候选列表里的第一个换成真实选择器（保留多个候选更稳）。
"""
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class ChatPage(BasePage):
    # 输入框候选：Element Plus 的 textarea 真实输入节点常在 .el-textarea__inner 上
    INPUT = (
        (By.CSS_SELECTOR, ".el-textarea__inner"),
        (By.CSS_SELECTOR, "textarea"),
    )
    # 发送按钮候选：文本匹配最稳（Element Plus 按钮常无稳定 id）
    SEND = (
        (By.XPATH, "//button[contains(., '发送')]"),
        (By.CSS_SELECTOR, "button.el-button--primary"),
    )
    # 回答区候选
    ANSWER = (
        (By.CSS_SELECTOR, ".markdown-body"),
        (By.CSS_SELECTOR, ".answer"),
        (By.CSS_SELECTOR, ".el-card__body"),
    )
    # 导航入口（App.vue 里两个页面切换）
    NAV_KB = (
        (By.XPATH, "//*[contains(text(), '知识库')]"),
        (By.CSS_SELECTOR, ".el-menu-item"),
    )

    def open_page(self, url: str):
        self.open(url)

    def ask(self, question: str) -> str:
        """提问并返回回答文本（等到有内容为止）。"""
        box = self.find_first(*self.INPUT)
        box.clear()
        box.send_keys(question)
        btn = self.find_first(*self.SEND)
        btn.click()
        return self.wait_any_text(*self.ANSWER, timeout=90)

    def go_knowledge_base(self):
        self.find_first(*self.NAV_KB).click()

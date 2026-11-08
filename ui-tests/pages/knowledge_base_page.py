"""知识库管理页（KnowledgeBase.vue）的页面对象。"""
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class KnowledgeBasePage(BasePage):
    # 上传控件：隐藏的 input[type=file]，直接用 send_keys 发路径，不需要点弹窗
    FILE_INPUT = (By.CSS_SELECTOR, "input[type=file]")
    UPLOAD_BTN = (
        (By.XPATH, "//button[contains(., '上传')]"),
        (By.CSS_SELECTOR, "button.el-button--primary"),
    )
    # 文档列表行
    DOC_ROWS = (
        (By.CSS_SELECTOR, ".el-table__row"),
        (By.CSS_SELECTOR, ".doc-item"),
    )
    EMPTY_TIP = (
        (By.XPATH, "//*[contains(text(), '暂无')]"),
        (By.CSS_SELECTOR, ".el-empty"),
    )

    def upload(self, abs_path: str):
        """上传文件：直接给 input[type=file] 发绝对路径，绕过系统文件选择框。"""
        el = self.find(self.FILE_INPUT)
        el.send_keys(abs_path)

    def row_texts(self) -> list:
        return [row.text for row in self.driver.find_elements(*self.DOC_ROWS)]

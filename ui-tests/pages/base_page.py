"""页面基类：封装显式等待与常用操作。

原则：所有元素查找都走显式等待，禁止 time.sleep。
前端是 Vue + Element Plus，class 常带随机后缀，所以定位优先用
稳定属性（id / placeholder / 文本），必要时用 [class^='xxx'] 前缀匹配。
"""
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    timeout = 15

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, self.timeout)

    def open(self, url: str):
        self.driver.get(url)

    def find(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def click(self, locator):
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def type_text(self, locator, text: str):
        el = self.find(locator)
        el.clear()
        el.send_keys(text)

    def text_of(self, locator) -> str:
        return self.wait.until(EC.visibility_of_element_located(locator)).text

    def find_first(self, *locators, timeout: float = 10):
        """在多个候选定位器里找出**第一个**真正存在的元素。

        为什么需要它：Element Plus 的 class 带随机后缀、不同版本结构会变，
        写死一个选择器很容易挂。用候选列表可以提高稳定性。
        """
        end = time.time() + timeout
        while time.time() < end:
            for loc in locators:
                els = self.driver.find_elements(*loc)
                if els:
                    return els[0]
            time.sleep(0.3)
        raise TimeoutException(f"候选定位器均未命中: {locators}")

    def wait_any_text(self, *locators, timeout: float = 60) -> str:
        """等到任意候选元素出现且有文本（用于等大模型生成完成）。"""
        end = time.time() + timeout
        while time.time() < end:
            for loc in locators:
                for el in self.driver.find_elements(*loc):
                    if el.text.strip():
                        return el.text
            time.sleep(0.5)
        raise TimeoutException(f"等待文本超时: {locators}")

    def screenshot(self, name: str):
        self.driver.save_screenshot(f"screenshots/{name}.png")

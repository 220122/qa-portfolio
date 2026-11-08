"""UI 自动化 fixture。

前提：本机装了 Chrome；被测前端已启动（默认 http://localhost:5173）。
Selenium 4.6+ 自带 driver 管理，无需手动下载 chromedriver。
"""
import os

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@pytest.fixture(scope="session")
def base_url():
    return FRONTEND_URL


@pytest.fixture(scope="session")
def driver():
    opt = Options()
    opt.add_argument("--start-maximized")
    opt.add_argument("--disable-gpu")
    if os.getenv("HEADLESS") == "1":
        opt.add_argument("--headless=new")

    d = webdriver.Chrome(options=opt)
    # 关掉隐式等待，统一用显式等待，避免两种等待混用造成"莫名等很久"
    d.implicitly_wait(0)
    yield d
    d.quit()


@pytest.fixture(scope="session", autouse=True)
def _frontend_gate(driver, base_url):
    """前端不通就整体 skip，避免引擎报一堆看不懂的错。"""
    try:
        driver.get(base_url)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"前端不可用 {base_url}：{e}（先 cd frontend && npm run dev）")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """用例失败时自动截图，文件名带用例名——失败现场比日志值钱。"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    if rep.when == "call" and rep.failed:
        drv = item.funcargs.get("driver")
        if drv is not None:
            os.makedirs("screenshots", exist_ok=True)
            drv.save_screenshot(f"screenshots/{item.name}.png")

"""评测记录接口用例。"""
import pytest

from utils.api_client import chat, evaluations
from utils.assert_helper import assert_status


@pytest.mark.smoke
def test_evaluations_returns_list(api, uploaded_doc):
    r = evaluations(api)
    assert_status(r, 200, "评测记录")
    assert isinstance(r.json(), list), f"返回应为数组，实际: {type(r.json())}"


@pytest.mark.smoke
def test_evaluations_grows_after_chat(api, uploaded_doc):
    """每次问答都应落一条评测记录（否则线上无法回溯答得好不好）。"""
    before = len(evaluations(api).json())
    chat(api, "什么是虚拟内存？")
    after = len(evaluations(api).json())
    assert after == before + 1, f"评测记录未增长：{before} -> {after}"

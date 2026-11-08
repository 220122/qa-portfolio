"""健康检查接口用例。"""
import pytest

from config import HEALTH_OK
from utils.api_client import health
from utils.assert_helper import assert_faster_than, assert_status


@pytest.mark.smoke
def test_health_returns_ok(api):
    r = health(api)
    assert_status(r, 200, "健康检查")
    assert r.json() == HEALTH_OK, f"返回体不符合契约: {r.text[:200]}"


@pytest.mark.smoke
def test_health_response_time(api):
    r = health(api)
    assert_faster_than(r, 2, "健康检查应在 2s 内返回（否则存活探针会不稳）")


@pytest.mark.negative
def test_health_reflects_dependency_failure(api):
    """健康检查应能反映下游依赖状态。

    当前实现是硬编码 return {"status": "ok"}，依赖挂了也会说 ok（对应 R-04）。
    需要人为制造故障才有意义，默认 skip，避免制造误报：
      1. 把 backend/.env 的 CHROMA_DIR 改到不可写目录，或让 DEEPSEEK_API_KEY 失效
      2. 重启后端后执行：pytest test_health.py -k dependency -m negative
    """
    pytest.skip("需先人为制造依赖故障后再执行，详见 docs/风险点排查-course-rag-agent.md 的 R-04")

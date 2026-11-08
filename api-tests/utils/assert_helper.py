"""统一断言工具：失败时打印足够定位问题的上下文。

为什么需要它：默认的 assert 失败只告诉你 Expected/Actual，没有 URL、没有响应体，
排查时要手动重跑一遍。封装后失败信息自带现场。
"""


def assert_status(r, expect: int, note: str = ""):
    """断言状态码，失败时打印 URL / 请求体 / 响应体。"""
    assert r.status_code == expect, (
        f"{note}\n"
        f"期望状态码: {expect}\n"
        f"实际状态码: {r.status_code}\n"
        f"请求: {r.request.method} {r.request.url}\n"
        f"请求体: {getattr(r.request, 'body', None)}\n"
        f"响应体: {r.text[:500]}"
    )


def assert_contains(text: str, keyword: str, note: str = ""):
    """断言文本包含关键字（用于校验提示文案、拒答话术）。"""
    assert keyword in text, (
        f"{note}\n期望包含: {keyword}\n实际内容: {str(text)[:300]}"
    )


def assert_not_contains(text: str, keyword: str, note: str = ""):
    """断言文本不包含关键字（用于校验"不该说的话"：幻觉、系统提示词泄露）。"""
    assert keyword not in text, (
        f"{note}\n不应包含: {keyword}\n实际内容: {str(text)[:300]}"
    )


def assert_faster_than(r, limit_seconds: float, note: str = ""):
    """断言响应时间（性能基线）。"""
    cost = r.elapsed.total_seconds()
    assert cost < limit_seconds, (
        f"{note}\n期望 < {limit_seconds}s，实际 {cost:.2f}s\nURL: {r.request.url}"
    )
    return cost


def assert_fields(obj: dict, fields, note: str = ""):
    """断言 dict 包含指定字段（校验契约字段是否缺失）。"""
    missing = [f for f in fields if f not in obj]
    assert not missing, f"{note}\n缺少字段: {missing}\n实际字段: {list(obj.keys())}"

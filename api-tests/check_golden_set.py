"""评测集（Golden Dataset）回归：AI 应用质量的核心度量。

用法（在 api-tests 目录下，且被测服务已启动）：
    python check_golden_set.py

两个关键指标：
    误拒答率 = 课内问题被拒答的比例  → 阈值调太小会升高（用户问自己的资料却被告知"没有"）
    漏拒率   = 课外问题被作答的比例  → 阈值调太大 / 提示词太松会升高（模型开始编造）

什么时候跑：改切块参数、换 embedding 模型、调 RELEVANCE_THRESHOLD、换对话模型之后。
"""
import datetime
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import BASE_URL, CHAT_TIMEOUT, REFUSAL_KEYWORD  # noqa: E402

GOLDEN = ROOT / "data" / "golden_set.json"
REPORT_DIR = ROOT / "reports"


def load_cases():
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return data["cases"]


def ask(question: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/chat", json={"question": question}, timeout=CHAT_TIMEOUT
    )
    r.raise_for_status()
    return r.json().get("answer", "")


def main() -> int:
    cases = load_cases()
    print(f"评测集共 {len(cases)} 条，目标服务 {BASE_URL}\n")

    try:
        requests.get(f"{BASE_URL}/api/health", timeout=5).raise_for_status()
    except Exception:  # noqa: BLE001
        print("后端不可用，先启动：cd backend && uvicorn main:app --port 8000")
        return 2

    wrong_refuse, missed_refuse, rows = [], [], []
    for c in cases:
        try:
            answer = ask(c["question"])
        except Exception as e:  # noqa: BLE001
            rows.append((c["id"], c["category"], "ERROR", str(e)[:80]))
            continue

        refused = REFUSAL_KEYWORD in answer
        if c["category"] == "in_scope" and refused:
            wrong_refuse.append(c["id"])
            verdict = "误拒答"
        elif c["category"] == "out_of_scope" and not refused:
            missed_refuse.append(c["id"])
            verdict = "漏拒（可能编造）"
        else:
            verdict = "符合预期"
        rows.append((c["id"], c["category"], verdict, answer[:60].replace("\n", " ")))
        print(f"  {c['id']:>5} {verdict:<12} {c['question'][:24]}")

    n_in = sum(1 for c in cases if c["category"] == "in_scope")
    n_out = len(cases) - n_in
    wrate = len(wrong_refuse) / n_in * 100 if n_in else 0
    mrate = len(missed_refuse) / n_out * 100 if n_out else 0

    print("\n" + "=" * 52)
    print(f"误拒答率：{len(wrong_refuse)}/{n_in} = {wrate:.1f}%   误拒项：{wrong_refuse or '无'}")
    print(f"漏拒率　：{len(missed_refuse)}/{n_out} = {mrate:.1f}%   漏拒项：{missed_refuse or '无'}")
    print("=" * 52)

    REPORT_DIR.mkdir(exist_ok=True)
    ts = datetime.datetime.now()
    out = REPORT_DIR / f"评测集结果-{ts:%Y%m%d-%H%M}.md"
    lines = [
        f"# 评测集回归结果（{ts:%Y-%m-%d %H:%M}）",
        "",
        f"- 评测集：`data/golden_set.json`，共 {len(cases)} 条（课内 {n_in} / 课外 {n_out}）",
        f"- 误拒答率：**{wrate:.1f}%**（{len(wrong_refuse)}/{n_in}）",
        f"- 漏拒率：**{mrate:.1f}%**（{len(missed_refuse)}/{n_out}）",
        "",
        "| 用例 | 类别 | 结论 | 回答摘要 |",
        "|---|---|---|---|",
    ]
    for cid, cat, verdict, ans in rows:
        lines.append(f"| {cid} | {cat} | {verdict} | {ans} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n报告已生成：{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

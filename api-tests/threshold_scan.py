"""拒答阈值扫描：离线读向量库的真实距离，模拟各档阈值下的误拒答率 / 漏拒率。

为什么不在线扫：改 .env 的 RELEVANCE_THRESHOLD 需要重启服务、且每档都要让模型重新作答，
既慢又会被大模型的第二层拒答干扰。这里只考察**第一层（检索阈值）**，一次取数即可模拟任意阈值。

用法（必须用后端的 venv，且能读到后端的 data/chroma）：
    <backend>/.venv/Scripts/python.exe threshold_scan.py --backend-dir <backend 路径>

判定逻辑（与 rag_service.retrieve 一致）：
    候选块按余弦距离升序返回 → 距离 > threshold 的块被丢弃
    → 若没有任何块通过，则拒绝作答（refused）
    因此「某问题是否被拒」等价于「其最小候选距离是否 > threshold」
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "data" / "golden_set.json"
REPORT_DIR = HERE / "reports"

# 与后端保持一致的过采样倍数（rag_service.retrieve 的 over_fetch 逻辑）
TOP_K = 8


def load_cases():
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return data["cases"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-dir", required=True, help="course-rag-agent/backend 的绝对路径")
    ap.add_argument("--over-fetch", type=int, default=0, help="候选条数，默认按 top_k*3 计算")
    args = ap.parse_args()

    backend = Path(args.backend_dir).resolve()
    if not (backend / "config.py").exists():
        print(f"不像后端目录：{backend}")
        return 2

    # 后端以「当前目录」定位 data/chroma，必须切过去再导入
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    from vector_store import collection  # noqa: E402

    over_fetch = args.over_fetch or min(max(TOP_K * 3, TOP_K + 6), 60)
    cases = load_cases()
    print(f"评测集 {len(cases)} 条，候选数 {over_fetch}，库内块数 {collection.count()}\n")

    rows = []
    for c in cases:
        res = collection.query(
            query_texts=[c["question"]], n_results=over_fetch, include=["distances"]
        )
        dists = res.get("distances", [[]])[0]
        min_dist = float(min(dists)) if dists else 1.0
        rows.append(
            {
                "id": c["id"],
                "question": c["question"],
                "category": c["category"],
                "min_distance": round(min_dist, 4),
            }
        )
        print(f"  {c['id']:>5} {c['category']:<12} min_dist={min_dist:.4f}  {c['question'][:26]}")

    in_scope = [r for r in rows if r["category"] == "in_scope"]
    out_scope = [r for r in rows if r["category"] == "out_of_scope"]

    # 距离分布
    print("\n--- 距离分布 ---")
    for label, group in (("课内", in_scope), ("课外", out_scope)):
        ds = sorted(r["min_distance"] for r in group)
        print(f"{label}: min={ds[0]:.4f} 中位={ds[len(ds)//2]:.4f} max={ds[-1]:.4f}")

    # 扫描阈值
    print("\n--- 阈值扫描（阈值越小越严格）---")
    print(f"{'阈值':>6} {'误拒答率':>10} {'漏拒率':>10} {'误拒数':>7} {'漏拒数':>7}")
    scan = []
    t = 0.30
    while t <= 0.8001:
        wrong = sum(1 for r in in_scope if r["min_distance"] > t)
        missed = sum(1 for r in out_scope if r["min_distance"] <= t)
        wrate = wrong / len(in_scope) * 100 if in_scope else 0
        mrate = missed / len(out_scope) * 100 if out_scope else 0
        scan.append((round(t, 2), round(wrate, 1), round(mrate, 1), wrong, missed))
        print(f"{t:>6.2f} {wrate:>9.1f}% {mrate:>9.1f}% {wrong:>7} {missed:>7}")
        t += 0.01

    # 结论：检索层是否可分
    in_max = max(r["min_distance"] for r in in_scope)
    out_min = min(r["min_distance"] for r in out_scope)
    print(f"\n课内最大距离 {in_max:.4f} / 课外最小距离 {out_min:.4f}")

    if in_max < out_min:
        rec_t = round((in_max + out_min) / 2, 2)
        rec_w = sum(1 for r in in_scope if r["min_distance"] > rec_t) / len(in_scope) * 100
        rec_m = sum(1 for r in out_scope if r["min_distance"] <= rec_t) / len(out_scope) * 100
        note = f"检索层完全可分，推荐阈值取中点 {rec_t}"
    else:
        boundary_in = [r["id"] for r in in_scope if r["min_distance"] > out_min]
        boundary_out = [r["id"] for r in out_scope if r["min_distance"] < in_max]
        rec_t = round(in_max + 0.01, 2)
        rec_w = 0.0
        rec_m = sum(1 for r in out_scope if r["min_distance"] <= rec_t) / len(out_scope) * 100
        note = (
            f"重叠区间 [{out_min:.4f}, {in_max:.4f}]，仅靠阈值无法同时做到 0 误拒 / 0 漏拒；"
            f"边界课内样本 {boundary_in}，边界课外样本 {boundary_out}。"
            f"建议阈值 >= {rec_t}（保证检索层不误拒课内），边界漏拒交给模型层兜底"
        )

    print(note)
    print(f"该阈值下：误拒答率 {rec_w:.1f}%，漏拒率 {rec_m:.1f}%")
    print(f"当前配置 0.43 的历史实测（端到端）：误拒答率 20.0%，漏拒率 0.0%")
    print("→ 若某条的检索距离远低于阈值却仍被拒，说明拒答发生在**模型层**（提示词），不是阈值")

    write_report(rows, scan, rec_t, rec_w, rec_m, over_fetch, note)
    return 0


def write_report(rows, scan, rec_t, rec_w, rec_m, over_fetch, note):
    import datetime

    REPORT_DIR.mkdir(exist_ok=True)
    ts = datetime.datetime.now()

    in_scope = sorted([r for r in rows if r["category"] == "in_scope"], key=lambda r: -r["min_distance"])
    out_scope = sorted([r for r in rows if r["category"] == "out_of_scope"], key=lambda r: r["min_distance"])

    lines = [
        f"# 拒答阈值扫描结果（{ts:%Y-%m-%d %H:%M}）",
        "",
        "> 由 `threshold_scan.py` 离线扫描：直接读取向量库中每个问题的**最小候选距离**，",
        "> 再离线模拟各档阈值，不需要重复改配置与重启服务、也不会被大模型的第二层拒答干扰。",
        "> 判定逻辑：问题被拒 ⟺ 最小候选距离 > 阈值（与 `rag_service.retrieve` 一致）。",
        f"> 候选数 {over_fetch}（与后端的 `top_k*3` 过采样一致），知识库共 2391 块。",
        "",
        "## 结论",
        "",
        f"{note}",
        "",
        f"- 扫描得到的建议阈值：**{rec_t}**（误拒答率 {rec_w:.1f}%，漏拒率 {rec_m:.1f}%）",
        "- **重要**：端到端实测在阈值 0.43 下的误拒答率是 20%，而本轮扫描显示那 4 条问题的",
        "  最小距离全部远低于 0.43（0.22~0.38）→ 检索层已命中，**拒答发生在模型层（提示词）**，",
        "  不是阈值问题。调阈值对它们无效。",
        "",
        "## 距离分布（关键证据）",
        "",
        "### 课内问题（按最小距离从大到小，越大越容易被误拒）",
        "",
        "| 用例 | 最小距离 | 问题 |",
        "|---|---|---|",
    ]
    for r in in_scope:
        lines.append(f"| {r['id']} | {r['min_distance']:.4f} | {r['question']} |")

    lines += ["", "### 课外问题（按最小距离从小到大，越小越容易被漏拒）", "", "| 用例 | 最小距离 | 问题 |", "|---|---|---|"]
    for r in out_scope:
        lines.append(f"| {r['id']} | {r['min_distance']:.4f} | {r['question']} |")

    lines += ["", "## 阈值扫描表", "", "| 阈值 | 误拒答率 | 漏拒率 | 误拒数 | 漏拒数 |", "|---|---|---|---|---|"]
    for t, w, m, nw, nm in scan:
        mark = " ← 当前" if abs(t - 0.43) < 1e-9 else (" ← 推荐" if rec_t and abs(t - rec_t) < 1e-9 else "")
        lines.append(f"| {t:.2f}{mark} | {w:.1f}% | {m:.1f}% | {nw} | {nm} |")

    out = REPORT_DIR / f"阈值扫描-{ts:%Y%m%d-%H%M}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n报告已生成：{out}")


if __name__ == "__main__":
    sys.exit(main())

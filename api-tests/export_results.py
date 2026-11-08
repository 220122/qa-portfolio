"""跑一遍接口自动化，把真实结果导出为可直接提交的报告。

用法（在 api-tests 目录下）：
    python export_results.py

产出：
    reports/junit.xml                 原始结果（不提交）
    reports/执行结果-YYYYmmdd-HHMM.md   提交用（自动生成，含失败清单与耗时）

为什么要有这个脚本：
    手工把 25 条结果抄进表格既慢又容易抄错，而且"抄一个好看的数字"没有任何意义——
    面试官一追问"怎么复现的"就露馅。跑一次自动生成，结果天然可信。
"""
import datetime
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
JUNIT = REPORT_DIR / "junit.xml"


def run_pytest() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", f"--junitxml={JUNIT}"]
    print(">>>", " ".join(cmd), "\n")
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def parse_junit():
    if not JUNIT.exists():
        print("未生成 junit.xml，pytest 可能没跑起来（先确认依赖已安装）")
        sys.exit(1)

    rows = []
    for tc in ET.parse(JUNIT).getroot().iter("testcase"):
        status, detail = "通过", ""
        for child in tc:
            if child.tag in ("failure", "error"):
                status = "失败" if child.tag == "failure" else "错误"
                detail = " ".join((child.get("message") or "").split())[:300]
            elif child.tag == "skipped":
                status = "跳过"
                detail = " ".join((child.get("message") or "").split())[:300]
        rows.append(
            {
                "class": tc.get("classname", ""),
                "name": tc.get("name", ""),
                "time": tc.get("time", "0"),
                "status": status,
                "detail": detail,
            }
        )
    return rows


def write_markdown(rows, exit_code):
    ts = datetime.datetime.now()
    total = len(rows)
    ok = sum(1 for r in rows if r["status"] == "通过")
    bad = [r for r in rows if r["status"] in ("失败", "错误")]
    skipped = [r for r in rows if r["status"] == "跳过"]
    cost = sum(float(r["time"] or 0) for r in rows)

    lines = [
        f"# 接口自动化执行结果（{ts:%Y-%m-%d %H:%M}）",
        "",
        "> 由 `export_results.py` 自动生成，数字直接取自 pytest 的 junit 结果，未做任何人工修改。",
        "",
        "## 汇总",
        "",
        "| 指标 | 数值 |",
        "|---|---|",
        f"| 用例总数 | {total} |",
        f"| 通过 | {ok} |",
        f"| 失败 / 错误 | {len(bad)} |",
        f"| 跳过 | {len(skipped)} |",
        f"| 总耗时 | {cost:.1f}s |",
        f"| pytest 退出码 | {exit_code} |",
        "",
        "## 明细",
        "",
        "| 模块 | 用例 | 结果 | 耗时(s) |",
        "|---|---|---|---|",
    ]
    for r in rows:
        mark = {"通过": "✅", "失败": "❌", "错误": "⚠️", "跳过": "⏭️"}[r["status"]]
        lines.append(
            f"| {r['class'].split('.')[0]} | {r['name']} | {mark} {r['status']} | {float(r['time'] or 0):.2f} |"
        )

    if bad:
        lines += ["", "## 失败清单（每条都是候选缺陷，需按模板复现并定级）", ""]
        for r in bad:
            lines += [
                f"### {r['class'].split('.')[0]}::{r['name']}",
                "",
                "```",
                r["detail"] or "(无错误信息)",
                "```",
                "",
            ]

    if skipped:
        lines += ["", "## 跳过项（需人工构造条件后单独执行）", ""]
        for r in skipped:
            lines.append(f"- `{r['name']}`：{r['detail'][:120] or '无说明'}")

    out = REPORT_DIR / f"执行结果-{ts:%Y%m%d-%H%M}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out, total, ok, len(bad)


def main():
    code = run_pytest()
    rows = parse_junit()
    out, total, ok, bad = write_markdown(rows, code)
    print("\n" + "=" * 52)
    print(f"用例 {total} 条：通过 {ok}，失败/错误 {bad}")
    print(f"报告已生成：{out}")
    print("=" * 52)
    print("\n下一步：")
    print("  1) 失败项 → 按 bug-reports/缺陷报告模板.md 写缺陷报告")
    print("  2) 把 reports/ 里这份结果一起提交，作为真实执行记录")
    if code != 0:
        print("\n注意：pytest 退出码非 0，说明有用例失败——这是发现缺陷的正常结果，不是脚本问题。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

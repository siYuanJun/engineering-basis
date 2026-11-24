#!/usr/bin/env python3
"""合入前审查判定器 · 最小切片。

从完整工程中抽出「清单校验 → 三态结论」这一段，用于公开复现。
不包含轮次台账、指标统计、交接单，也不读写任何文件。

用法：
    python3 check.py <fixtures/xxx.json> [--round N]

退出码：0 = APPROVE；1 = 清单不合法；3 = BLOCK 或 ESCALATE。
"""

import argparse
import json
import re
import sys

SEVERITIES = {"Important", "Nit", "Pre-existing"}
STATUSES = {"open", "fixed", "rejected", "accepted"}
STYLE_WORDS = [
    r"\bnaming\b", r"\bstyle\b", r"\bformat", r"\bindent", r"缩进", r"命名", r"格式",
    r"注释", r"\bcomment\b", r"变量名", r"函数名", r"引号", r"换行", r"import 顺序",
]


def text(v):
    if isinstance(v, list):
        return "；".join(str(x) for x in v if str(x).strip())
    return "" if v is None else str(v).strip()


def line_ok(v):
    if isinstance(v, int):
        return v > 0
    if isinstance(v, str) and v.strip():
        return bool(re.match(r"^\d+(\s*[-–,，]\s*\d+)?$", v.strip()))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--round", type=int, default=1)
    a = ap.parse_args()

    with open(a.path, encoding="utf-8") as fh:
        data = json.load(fh)
    findings = data.get("findings", []) if isinstance(data, dict) else data

    if not isinstance(findings, list):
        print("findings 必须是数组，或 {\"findings\": [...]}", file=sys.stderr)
        return 1

    errors = []
    seen = {}

    for i, f in enumerate(findings, 1):
        tag = f.get("id") or f"#{i}"
        if not isinstance(f, dict):
            errors.append(f"{tag}: 不是对象")
            continue
        for key in ("id", "severity", "file", "line", "claim", "evidence", "verify", "status"):
            if key == "line":
                if not line_ok(f.get(key)):
                    errors.append(f"{tag}: line 必须是行号或行号区间")
            elif not text(f.get(key)):
                errors.append(f"{tag}: 缺字段 {key}")

        sev, st = text(f.get("severity")), text(f.get("status"))
        if sev and sev not in SEVERITIES:
            errors.append(f"{tag}: severity 非法（{sev}）")
        if st and st not in STATUSES:
            errors.append(f"{tag}: status 非法（{st}）")
        if sev == "Important" and st == "accepted":
            errors.append(f"{tag}: Important 不允许 accepted，只能 fixed 或 rejected")
        if st == "rejected" and not text(f.get("response")):
            errors.append(f"{tag}: rejected 必须写 response（为什么不成立）")

        claim = text(f.get("claim"))
        if claim and any(re.search(p, claim, re.I) for p in STYLE_WORDS):
            errors.append(f"{tag}: 疑似风格/命名类意见，按规则应丢弃，不进清单")

        key = (text(f.get("file")), str(f.get("line")).strip())
        if key in seen:
            errors.append(f"{tag}: 与 {seen[key]} 重复（同文件同行）；确为两个问题请合并一条或拆到不同行")
        else:
            seen[key] = tag

    if errors:
        print("清单不合法：", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        print("不生成结论。先修清单。", file=sys.stderr)
        return 1

    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        if isinstance(f, dict) and f.get("severity") in counts:
            counts[f["severity"]] += 1

    open_items = [f for f in findings if isinstance(f, dict) and f.get("status") == "open"]
    open_important = [f for f in open_items if f.get("severity") == "Important"]
    invalid = [f for f in findings if isinstance(f, dict) and f.get("status") in ("rejected", "accepted")]
    invalid_rate = round(len(invalid) / len(findings), 3) if findings else 0.0

    blocking = [f for f in open_items if f.get("severity") != "Pre-existing"]
    stale_open = [f for f in open_items if f.get("severity") == "Pre-existing" and not text(f.get("response"))]

    if open_important and a.round > 3:
        verdict = "ESCALATE"
        reason = f"第 {a.round} 轮仍有 {len(open_important)} 条 Important 未关闭，停手重想方案"
    elif blocking or stale_open:
        verdict = "BLOCK"
        reason = f"{len(blocking)} 条未关闭（Important {len(open_important)}），另有 {len(stale_open)} 条历史问题未给处置说明"
    else:
        verdict = "APPROVE"
        reason = "无阻塞项" + (f"；{len(open_items)} 条历史问题已注明另开单" if open_items else "")

    print(json.dumps({
        "verdict": verdict,
        "reason": reason,
        "round": a.round,
        "total": len(findings),
        "counts": counts,
        "open": len(open_items),
        "open_important": len(open_important),
        "invalid": len(invalid),
        "invalid_rate": invalid_rate,
    }, ensure_ascii=False, indent=2))
    return 0 if verdict == "APPROVE" else 3


if __name__ == "__main__":
    sys.exit(main())

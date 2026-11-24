#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""差距台账确定性检查（Python 3.9，零依赖）。

四条检查：
  R1 条目对账：PRD 条目与台账行双向差集
  R2 证据与必填：判定值域、证据可复核、P0 运行态证据
  R3 验收独立性：已闭环行 verified_by 不得等于 owner
  R4 待决策阻塞：冲突行必须停在待决策

退出码：0 全部通过；1 有违规；2 输入或解析错误。
"""

import argparse
import json
import os
import re
import sys

VERDICTS = {"一致", "部分", "缺失", "多做", "冲突", "不适用", "待验证"}
EVIDENCE_TYPES = {"真跑", "接口", "数据库", "代码静态", "文档"}
BEHAVIOR_EVIDENCE = {"真跑", "接口", "数据库"}
PRIORITIES = {"P0", "P1", "P2", "待定"}
STATUSES = {"待取证", "待处理", "处理中", "待验收", "待决策", "已闭环", "挂账"}
GENERIC_ROLES = {"决策人", "拆单方", "开发方", "验收方", "待指派"}
CLOSED_STATUS = "已闭环"
PENDING = "待验证"
EMPTY_MARKS = {"", "—", "-", "无", "N/A", "n/a"}

REQUIRED_COLUMNS = [
    "id",
    "source",
    "requirement",
    "verdict",
    "evidence_type",
    "evidence_ref",
    "gap",
    "action",
    "priority",
    "owner",
    "status",
    "verified_by",
    "notes",
]

STATUS_BY_VERDICT = {
    "一致": {"待验收", "已闭环"},
    "部分": {"待处理", "处理中", "待验收", "已闭环", "挂账"},
    "缺失": {"待处理", "处理中", "待验收", "已闭环", "挂账"},
    "多做": {"待处理", "处理中", "待验收", "已闭环", "挂账"},
    "不适用": {"待验收", "已闭环", "挂账"},
    "待验证": {"待取证"},
}


class InputError(Exception):
    """输入或解析错误，对应退出码 2。"""


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("无法读取文件 %s: %s" % (path, exc))


def strip_cell_marks(value):
    value = (value or "").strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    return value


def split_row(line):
    text = line.rstrip("\n")
    text = text.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    cells = []
    current = []
    escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def is_separator(cells):
    if not cells:
        return False
    for cell in cells:
        value = cell.strip()
        if not re.match(r"^:?-{3,}:?$", value):
            return False
    return True


def normalize_header(cell):
    return strip_cell_marks(cell).lower()


def parse_ledger(path):
    text = read_text(path)
    lines = text.splitlines()
    header = None
    rows = []
    header_line_no = 0
    for index, line in enumerate(lines, 1):
        if not line.strip().startswith("|"):
            continue
        cells = split_row(line)
        normalized = [normalize_header(cell) for cell in cells]
        if all(column in normalized for column in REQUIRED_COLUMNS):
            header = normalized
            header_line_no = index
            break
    if header is None:
        raise InputError(
            "未找到台账主表：表头必须同时包含 %s"
            % ", ".join(REQUIRED_COLUMNS)
        )
    index = header_line_no
    while index < len(lines):
        line = lines[index]
        if not line.strip().startswith("|"):
            break
        cells = split_row(line)
        index += 1
        if is_separator(cells):
            continue
        if len(cells) != len(header):
            raise InputError(
                "台账第 %d 行列数为 %d，表头为 %d 列；请转义单元格内的竖线"
                % (index, len(cells), len(header))
            )
        record = {}
        for column, cell in zip(header, cells):
            record[column] = strip_cell_marks(cell)
        if record.get("id"):
            rows.append(record)
    return rows


def read_ids(path):
    text = read_text(path)
    ids = []
    seen = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split()[0]
        if line in seen:
            continue
        seen.add(line)
        ids.append(line)
    if not ids:
        raise InputError("条目清单为空: %s" % path)
    return ids


def valid_ref(ref):
    if ref in EMPTY_MARKS:
        return False
    if any(token in ref for token in (":", "#", "§")):
        return True
    lowered = ref.lower()
    for suffix in (".md", ".json", ".log", ".txt", ".csv", ".png", ".jpg", ".jpeg"):
        if lowered.endswith(suffix):
            return True
    return False


def row_violation(code, row_id, message):
    return {"check": code, "id": row_id, "message": message}


def check_r1(required_ids, rows):
    violations = []
    required = set(required_ids)
    ledger_ids = []
    seen = set()
    for row in rows:
        row_id = row.get("id", "")
        if row_id in seen:
            violations.append(row_violation("R1", row_id, "台账 id 重复"))
        seen.add(row_id)
        ledger_ids.append(row_id)
    ledger = set(ledger_ids)
    missing = sorted(required - ledger)
    extra = sorted(ledger - required)
    extras_allowed = []
    extras_unexpected = []
    for row in rows:
        row_id = row.get("id", "")
        if row_id in extra:
            if row.get("verdict") == "多做":
                extras_allowed.append(row_id)
            else:
                extras_unexpected.append(row_id)
    for row_id in missing:
        violations.append(row_violation("R1", row_id, "PRD 条目在台账中缺失"))
    for row_id in sorted(set(extras_unexpected)):
        violations.append(
            row_violation("R1", row_id, "台账多出条目，但判定不是「多做」")
        )
    summary = {
        "required": len(required),
        "ledger": len(ledger),
        "missing": missing,
        "extra_allowed": sorted(set(extras_allowed)),
        "extra_unexpected": sorted(set(extras_unexpected)),
    }
    return violations, summary


def check_r2(rows, allow_pending, strict):
    violations = []
    pending_count = 0
    p0_count = 0
    for row in rows:
        row_id = row.get("id", "")
        verdict = row.get("verdict", "")
        if verdict not in VERDICTS:
            violations.append(
                row_violation("R2", row_id, "判定值非法: %s" % (verdict or "空"))
            )
            continue
        for column in ("source", "requirement"):
            if row.get(column, "") in EMPTY_MARKS:
                violations.append(
                    row_violation("R2", row_id, "必填字段为空: %s" % column)
                )
        priority = row.get("priority", "")
        owner = row.get("owner", "")
        status = row.get("status", "")
        evidence_type = row.get("evidence_type", "")
        evidence_ref = row.get("evidence_ref", "")
        gap = row.get("gap", "")
        action = row.get("action", "")
        verified_by = row.get("verified_by", "")

        if verdict == PENDING:
            pending_count += 1
            if strict:
                violations.append(
                    row_violation("R2", row_id, "收口模式不允许待验证")
                )
            elif not allow_pending:
                violations.append(
                    row_violation("R2", row_id, "待验证需要 --allow-pending")
                )
            if status != "待取证":
                violations.append(
                    row_violation("R2", row_id, "待验证行的 status 必须是待取证")
                )
            if verified_by not in EMPTY_MARKS:
                violations.append(
                    row_violation("R2", row_id, "待验证行不得签 verified_by")
                )
            if evidence_type not in EMPTY_MARKS:
                violations.append(
                    row_violation("R2", row_id, "待验证行 evidence_type 必须为空或 —")
                )
            if evidence_ref != "待取证":
                violations.append(
                    row_violation("R2", row_id, "待验证行 evidence_ref 必须是待取证")
                )
            if priority not in PRIORITIES:
                violations.append(
                    row_violation("R2", row_id, "priority 非法: %s" % (priority or "空"))
                )
            if owner not in GENERIC_ROLES:
                violations.append(
                    row_violation("R2", row_id, "owner 必须是通用角色: %s" % (owner or "空"))
                )
            continue

        if priority not in PRIORITIES or priority == "待定":
            violations.append(
                row_violation("R2", row_id, "非待验证行的 priority 必须是 P0/P1/P2")
            )
        if priority == "P0":
            p0_count += 1
        if owner not in GENERIC_ROLES or owner == "待指派":
            violations.append(
                row_violation("R2", row_id, "非待验证行的 owner 必须是通用角色")
            )
        if status not in STATUSES or status == "待取证":
            violations.append(
                row_violation("R2", row_id, "status 非法: %s" % (status or "空"))
            )
        allowed_statuses = STATUS_BY_VERDICT.get(verdict)
        if verdict != "冲突" and allowed_statuses and status not in allowed_statuses:
            violations.append(
                row_violation(
                    "R2",
                    row_id,
                    "判定 %s 不允许 status=%s" % (verdict, status or "空"),
                )
            )
        if status != CLOSED_STATUS and verified_by not in EMPTY_MARKS:
            violations.append(
                row_violation("R2", row_id, "未闭环行不应签 verified_by")
            )
        if evidence_type not in EVIDENCE_TYPES:
            violations.append(
                row_violation("R2", row_id, "evidence_type 非法: %s" % (evidence_type or "空"))
            )
        if not valid_ref(evidence_ref):
            violations.append(
                row_violation("R2", row_id, "evidence_ref 不可复核: %s" % (evidence_ref or "空"))
            )
        if priority == "P0" and evidence_type not in BEHAVIOR_EVIDENCE:
            violations.append(
                row_violation(
                    "R2",
                    row_id,
                    "P0 缺少运行态证据（仅限真跑/接口/数据库）",
                )
            )
        if verdict in {"部分", "缺失", "多做", "冲突"}:
            if gap in EMPTY_MARKS:
                violations.append(row_violation("R2", row_id, "该判定必须写 gap"))
            if action in EMPTY_MARKS:
                violations.append(row_violation("R2", row_id, "该判定必须写 action"))
        if verdict == "多做":
            if "保留" not in action and "下线" not in action:
                violations.append(
                    row_violation("R2", row_id, "多做行的 action 必须含「保留」或「下线」")
                )
        if verdict == "不适用" and gap in EMPTY_MARKS:
            violations.append(
                row_violation("R2", row_id, "不适用行必须在 gap 写明范围依据")
            )
    summary = {"rows": len(rows), "pending": pending_count, "p0": p0_count}
    return violations, summary


def check_r3(rows):
    violations = []
    closed = 0
    for row in rows:
        if row.get("status") != CLOSED_STATUS:
            continue
        closed += 1
        row_id = row.get("id", "")
        owner = row.get("owner", "")
        verified_by = row.get("verified_by", "")
        if verified_by in EMPTY_MARKS:
            violations.append(
                row_violation("R3", row_id, "已闭环行缺少 verified_by")
            )
        elif verified_by not in GENERIC_ROLES or verified_by == "待指派":
            violations.append(
                row_violation("R3", row_id, "verified_by 必须是通用角色")
            )
        elif verified_by == owner:
            violations.append(
                row_violation("R3", row_id, "verified_by 不得等于 owner")
            )
    return violations, {"closed": closed}


def check_r4(rows):
    violations = []
    conflicts = 0
    for row in rows:
        if row.get("verdict") != "冲突":
            continue
        conflicts += 1
        row_id = row.get("id", "")
        status = row.get("status", "")
        notes = row.get("notes", "")
        if status != "待决策":
            violations.append(
                row_violation("R4", row_id, "冲突行必须停在待决策")
            )
        if "决策人" not in notes:
            violations.append(
                row_violation("R4", row_id, "冲突行 notes 必须写「决策人」")
            )
        if "待裁决" not in notes:
            violations.append(
                row_violation("R4", row_id, "冲突行 notes 必须写「待裁决」")
            )
    return violations, {"conflicts": conflicts}


def extract_prd(path, patterns):
    text = read_text(path)
    ids = []
    seen = set()
    for pattern in patterns:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise InputError("条目正则非法 %s: %s" % (pattern, exc))
        for match in compiled.finditer(text):
            value = match.group(1) if match.groups() else match.group(0)
            if value and value not in seen:
                seen.add(value)
                ids.append(value)
    return ids


def emit_text(results, summaries, counts, ok):
    for code in ("R1", "R2", "R3", "R4"):
        violations = results[code]
        state = "PASS" if not violations else "FAIL"
        print("[%s] %s" % (code, state))
        for item in violations:
            print("  - %s: %s" % (item["id"], item["message"]))
    print(
        "统计: 行=%d, 一致=%d, 部分=%d, 缺失=%d, 多做=%d, 冲突=%d, 不适用=%d, 待验证=%d"
        % (
            counts["rows"],
            counts["一致"],
            counts["部分"],
            counts["缺失"],
            counts["多做"],
            counts["冲突"],
            counts["不适用"],
            counts["待验证"],
        )
    )
    if "R1" in summaries:
        r1 = summaries["R1"]
        print(
            "对账: required=%d, ledger=%d, 漏项=%d, 未声明多出=%d, 允许多做=%d"
            % (
                r1["required"],
                r1["ledger"],
                len(r1["missing"]),
                len(r1["extra_unexpected"]),
                len(r1["extra_allowed"]),
            )
        )
    print("结果: %s" % ("PASS" if ok else "FAIL"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="检查 PRD × 实现差距台账的四条确定性规则。",
        epilog="退出码：0 通过；1 有违规；2 输入或解析错误。",
    )
    parser.add_argument("--required", help="PRD 条目清单文件")
    parser.add_argument("--ledger", help="差距台账 Markdown 文件")
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="允许待验证行（骨架模式）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="收口模式：待验证行也判失败",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--extract-prd", help="从 PRD Markdown 提取条目号")
    parser.add_argument("--out", help="提取结果写入文件")
    parser.add_argument(
        "--id-pattern",
        action="append",
        default=None,
        help="条目正则，可重复；默认 FR/AC 两段或三段数字",
    )
    args = parser.parse_args(argv)

    try:
        if args.extract_prd:
            patterns = args.id_pattern or [
                r"(?<![A-Za-z0-9-])FR-\d{2,3}(?!\d)",
                r"(?<![A-Za-z0-9-])AC-\d{2,3}(?!\d)",
            ]
            ids = extract_prd(args.extract_prd, patterns)
            if not ids:
                raise InputError("未从 PRD 提取到条目号: %s" % args.extract_prd)
            if args.out:
                try:
                    with open(args.out, "w", encoding="utf-8") as handle:
                        handle.write("\n".join(ids) + "\n")
                except OSError as exc:
                    raise InputError("无法写入 %s: %s" % (args.out, exc))
                print("已提取 %d 条，写入 %s" % (len(ids), args.out))
            else:
                print("\n".join(ids))
            return 0

        if not args.required or not args.ledger:
            raise InputError("需要同时提供 --required 与 --ledger（或使用 --extract-prd）")

        required_ids = read_ids(args.required)
        rows = parse_ledger(args.ledger)
        if not rows:
            raise InputError("台账主表没有数据行: %s" % args.ledger)

        r1, r1_summary = check_r1(required_ids, rows)
        r2, r2_summary = check_r2(rows, args.allow_pending, args.strict)
        r3, r3_summary = check_r3(rows)
        r4, r4_summary = check_r4(rows)
        results = {"R1": r1, "R2": r2, "R3": r3, "R4": r4}
        summaries = {"R1": r1_summary, "R2": r2_summary, "R3": r3_summary, "R4": r4_summary}
        counts = {
            "rows": len(rows),
            "一致": 0,
            "部分": 0,
            "缺失": 0,
            "多做": 0,
            "冲突": 0,
            "不适用": 0,
            "待验证": 0,
        }
        for row in rows:
            verdict = row.get("verdict", "")
            if verdict in counts:
                counts[verdict] += 1
        ok = all(not results[code] for code in results)
        if args.json:
            payload = {
                "ok": ok,
                "checks": {
                    code: {"ok": not results[code], "violations": results[code]}
                    for code in ("R1", "R2", "R3", "R4")
                },
                "summaries": summaries,
                "counts": counts,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            emit_text(results, summaries, counts, ok)
        return 0 if ok else 1
    except InputError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print("输入或解析错误: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
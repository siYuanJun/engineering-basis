#!/usr/bin/env python3
"""缺陷单当前动作的闸门判定（零依赖切片）。

输入一条缺陷单的当前动作与字段，输出能不能由 AI 落地。
退出码：0 可落；3 需人拍板或交接；1 输入不合法。
"""
import argparse
import json
import sys

CODE_RESOLUTIONS = {"fixed", "duplicate", "external"}
REQ_RESOLUTIONS = {"tostory", "bydesign", "notrepro", "postponed", "willnotfix"}


def judge(bug):
    action = bug.get("action")
    if action == "close":
        return "HANDOFF", "关闭只由提报人操作，AI 提醒到位即止", 3
    if action != "resolve":
        return "INVALID", "动作只支持 resolve 与 close", 1

    resolution = bug.get("resolution")
    if resolution in REQ_RESOLUTIONS:
        return "HOLD_OWNER", f"归因为 {resolution}，属于需求判断，需人拍板", 3
    if resolution not in CODE_RESOLUTIONS:
        return "INVALID", "归因取值不在约定集合内", 1
    if bug.get("self_test") != "passed":
        return "HOLD_SELF", "自测未通过，不写回解决", 3
    if bug.get("change_weight") == "L3":
        return "HOLD_OWNER", "改动涉及表结构或数据迁移，由人主导评估", 3
    return "RESOLVE", "代码类归因且自测通过，可写回解决", 0


def main():
    parser = argparse.ArgumentParser(description="缺陷单闸门判定")
    parser.add_argument("bug", help="缺陷单 JSON 路径")
    args = parser.parse_args()

    try:
        with open(args.bug, encoding="utf-8") as handle:
            bug = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"输入不合法：{exc}", file=sys.stderr)
        return 1

    verdict, reason, code = judge(bug)
    print(json.dumps({"verdict": verdict, "reason": reason}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""生成缺陷闭环的分叉判定场景。

判定不手写：跑 demos/bug-loop 的三个样例，取真实 verdict/reason 与退出码，
组装 spec 后交给 3d-stage-deck 的 build_fork.py。结果与预期不符就退出。

用法：python3 viz/build_bug.py
"""

import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = os.path.join(os.path.dirname(ROOT), "3d-stage-deck")
SCRIPT_REL = "demos/bug-loop/bug_gate.py"
SCRIPT = os.path.join(ROOT, SCRIPT_REL)
FIX = os.path.join(ROOT, "demos", "bug-loop", "fixtures")
VIZ = os.path.join(ROOT, "viz")
OUT = os.path.join(VIZ, "bug-fork.html")
SPEC_OUT = os.path.join(VIZ, "bug-fork.json")


def run_gate(fixture):
    cmd = [sys.executable, SCRIPT, os.path.join(FIX, fixture)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"读不到 bug_gate 的 JSON：{fixture}\n{p.stdout}\n{p.stderr}")
    return data, p.returncode, f"python3 {SCRIPT_REL} demos/bug-loop/fixtures/{fixture}"


resolved, exit_r, cmd_r = run_gate("resolve.json")
hold, exit_h, cmd_h = run_gate("need-decision.json")
handoff, exit_x, cmd_x = run_gate("close.json")

assert resolved["verdict"] == "RESOLVE" and exit_r == 0, "resolve 应为 RESOLVE / exit 0"
assert hold["verdict"] == "HOLD_OWNER" and exit_h == 3, "need-decision 应为 HOLD_OWNER / exit 3"
assert handoff["verdict"] == "HANDOFF" and exit_x == 3, "close 应为 HANDOFF / exit 3"

spec = {
    "title": "缺陷改完，算不算完",
    "eyebrow": "BUG-LOOP · 3D 分叉",
    "subtitle": "代码改完不等于单能结。归因决定谁能落地：写回、等人拍板、交回提报人。结论来自 bug_gate 实跑。",
    "startLabel": "一条缺陷单",
    "checkpoint": {
        "name": "归因与落地",
        "rule": "归因先定性：代码类还是需求类。需求类一律人拍板，关闭交给提报人。",
        "detail": "改动重量分档，涉及表结构与数据迁移由人主导；AI 只做判定与提醒。",
    },
    "branches": [
        {
            "id": "RESOLVE", "name": "写回解决", "exit": exit_r,
            "color": "#3DDC97", "x": 7.2, "z": 0,
            "rule": "代码类归因且自测通过，可写回解决。",
            "detail": "留下复现步骤与验证方式，单才算真正收口。",
        },
        {
            "id": "HOLD_OWNER", "name": "等人拍板", "exit": exit_h,
            "color": "#FFB454", "x": 3.4, "z": -4.6,
            "rule": "归到需求问题（bydesign），停下来等人拍板。",
            "detail": "需求边界不能由开发自己下结论，否则会被代码悄悄改写。",
        },
        {
            "id": "HANDOFF", "name": "交回提报人", "exit": exit_x,
            "color": "#8FA6C4", "x": 3.4, "z": 4.6,
            "rule": "关闭只由提报人操作，AI 提醒到位即止。",
            "detail": "判定能做，关闭权限不在开发手里。",
        },
    ],
    "loop": {
        "from": "HOLD_OWNER",
        "to": {"x": -2.6, "z": -7.4, "name": "人拍板"},
        "rule": "归因是需求边界，退回产品与提报人；开发不替产品做决定。",
    },
    "cases": [
        {
            "id": "A", "label": "代码问题", "title": "代码问题，自测通过",
            "branch": "RESOLVE", "verdict": resolved["verdict"], "exit": exit_r,
            "reason": resolved["reason"],
            "intro": "归因 fixed，自测通过，改动属于可直接撤回的一档。",
            "stopNote": "写回复现步骤与验证方式，再关单。",
        },
        {
            "id": "B", "label": "归到需求", "title": "归到需求问题",
            "branch": "HOLD_OWNER", "verdict": hold["verdict"], "exit": exit_h,
            "reason": hold["reason"],
            "intro": "bydesign：不是缺陷，是设计如此。",
            "stopNote": "开发不自己拍板，退回产品确认需求边界。",
        },
        {
            "id": "C", "label": "关闭单子", "title": "关闭这张单",
            "branch": "HANDOFF", "verdict": handoff["verdict"], "exit": exit_x,
            "reason": handoff["reason"],
            "intro": "修复完成，但关闭动作不在开发手里。",
            "stopNote": "提醒提报人验证后关闭，AI 到此为止。",
        },
    ],
}

os.makedirs(VIZ, exist_ok=True)
three_src = os.path.join(DECK, "assets", "three.module.min.js")
three_dst = os.path.join(VIZ, "three.module.min.js")
if not os.path.isfile(three_src):
    raise SystemExit(f"找不到 {three_src}")
shutil.copyfile(three_src, three_dst)

with open(SPEC_OUT, "w", encoding="utf-8") as fh:
    json.dump(spec, fh, ensure_ascii=False, indent=2)

build = subprocess.run(
    [sys.executable, os.path.join(DECK, "scripts", "build_fork.py"), SPEC_OUT,
     "--out", OUT, "--three-url", "./three.module.min.js"],
    capture_output=True, text=True,
)
print(build.stdout.strip())
if build.returncode != 0:
    print(build.stderr.strip(), file=sys.stderr)
    raise SystemExit(build.returncode)
print("写入：" + SPEC_OUT)

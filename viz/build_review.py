#!/usr/bin/env python3
"""生成合入审查的分叉判定场景。

判定不手写：跑 demos/review-loop 的三个样例，取真实 verdict/reason 与退出码，
组装 spec 后交给 3d-stage-deck 的 build_fork.py。结果与预期不符就退出。

用法：python3 viz/build_review.py
"""

import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = os.path.join(os.path.dirname(ROOT), "3d-stage-deck")
SCRIPT_REL = "demos/review-loop/check.py"
SCRIPT = os.path.join(ROOT, SCRIPT_REL)
FIX = os.path.join(ROOT, "demos", "review-loop", "fixtures")
VIZ = os.path.join(ROOT, "viz")
OUT = os.path.join(VIZ, "review-fork.html")
SPEC_OUT = os.path.join(VIZ, "review-fork.json")


def run_check(fixture, extra=()):
    cmd = [sys.executable, SCRIPT, os.path.join(FIX, fixture), *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"读不到 check.py 的 JSON：{fixture}\n{p.stdout}\n{p.stderr}")
    shown = f"python3 {SCRIPT_REL} demos/review-loop/fixtures/{fixture}"
    if extra:
        shown += " " + " ".join(extra)
    return data, p.returncode, shown


pass_r, exit_pass, cmd_pass = run_check("pass.json")
block_r, exit_block, cmd_block = run_check("block.json")
esc_r, exit_esc, cmd_esc = run_check("block.json", ("--round", "4"))

# 与案例页结论对齐；check.py 只有 APPROVE=0、其余=3
assert pass_r["verdict"] == "APPROVE" and exit_pass == 0, "pass 样例应为 APPROVE / exit 0"
assert block_r["verdict"] == "BLOCK" and exit_block == 3, "block 样例应为 BLOCK / exit 3"
assert esc_r["verdict"] == "ESCALATE" and exit_esc == 3, "第四轮样例应为 ESCALATE / exit 3"

def metrics(d):
    return f"total {d['total']} · open {d['open']} · important {d['open_important']}"


spec = {
    "title": "合入前，一条改动判到哪",
    "eyebrow": "REVIEW-LOOP · 3D 分叉",
    "subtitle": "同一条判定线，三个出口：通过、阻断、升级。退出码只区分能否合入，具体处置看 verdict。",
    "startLabel": "一条改动",
    "checkpoint": {
        "name": "审查判定",
        "rule": "只看缺陷与影响面，风格类意见不进清单；每条发现要带位置、主张、证据、复核方式。",
        "detail": "判定不依赖评审人记忆：条目状态、严重级、轮次都能复核。",
    },
    "branches": [
        {
            "id": "APPROVE", "name": "通过", "exit": exit_pass,
            "color": "#3DDC97", "x": 7.2, "z": 0,
            "rule": "无 Important 未关闭；历史问题写明另开单即可放行。",
            "detail": "有 open 不等于阻断，旧账不全部算在这次改动上。",
        },
        {
            "id": "BLOCK", "name": "阻断", "exit": exit_block,
            "color": "#FF6B5A", "x": 3.4, "z": -4.6,
            "rule": "存在未关闭的 Important；先改，不进入合并。",
            "detail": "阻断只针对会影响这次改动的缺陷，不针对风格偏好。",
        },
        {
            "id": "ESCALATE", "name": "升级", "exit": exit_esc,
            "color": "#FFB454", "x": 3.4, "z": 4.6,
            "rule": "同一问题超过三轮；停手重想方案，不再继续磨。",
            "detail": "升级不是再提一轮意见，而是把问题交回方案层。",
        },
    ],
    "cases": [
        {
            "id": "A", "label": "一条未关闭", "title": "一条真实缺陷未关闭",
            "branch": "BLOCK", "verdict": block_r["verdict"], "exit": exit_block,
            "reason": block_r["reason"],
            "metrics": metrics(block_r),
            "intro": "token 失效时接口仍返回 200，前端当成成功。一条 Important 未关闭即阻断。",
            "stopNote": "另一条 Nit 已修复，不参与阻断。先改这条，再重新判定。",
        },
        {
            "id": "B", "label": "已给处置", "title": "有历史问题，但已给处置",
            "branch": "APPROVE", "verdict": pass_r["verdict"], "exit": exit_pass,
            "reason": pass_r["reason"],
            "metrics": metrics(pass_r),
            "intro": "一条历史遗留问题写明另开单，没有 Important 未关闭。",
            "stopNote": "有 open 不是阻断理由；审查不把旧账全算在这次改动上。",
        },
        {
            "id": "C", "label": "磨到第四轮", "title": "同一问题磨到第四轮",
            "branch": "ESCALATE", "verdict": esc_r["verdict"], "exit": exit_esc,
            "reason": esc_r["reason"],
            "metrics": metrics(esc_r),
            "intro": "同一条 Important 改到第 4 轮仍未关闭。",
            "stopNote": "超过三轮不再继续提意见，交回方案层重新想。",
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

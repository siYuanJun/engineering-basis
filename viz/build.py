#!/usr/bin/env python3
"""生成发版闸门 3D 流转场景。

判定不手写：先跑 demos/release-loop 的三组 diff，取真实 breaking/additive 与退出码，
组装成 spec 再交给 3d-stage-deck 的 build_gate.py 注入模板。任何一组结果和预期不符就退出。

用法：python3 viz/build.py
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = os.path.join(os.path.dirname(ROOT), "3d-stage-deck")
SCRIPT_REL = "demos/release-loop/contract_snapshot.py"
SCRIPT = os.path.join(ROOT, SCRIPT_REL)
FIX = os.path.join(ROOT, "demos", "release-loop", "fixtures")
OUT = os.path.join(ROOT, "viz", "release-gates.html")
SPEC_OUT = os.path.join(ROOT, "viz", "release-gates.json")


def run_diff(new_snap):
    old_abs = os.path.join(FIX, "snap-base.json")
    new_abs = os.path.join(FIX, new_snap)
    cmd = [sys.executable, SCRIPT, "diff", "--old", old_abs, "--new", new_abs, "--fail-on-removal"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    raw = p.stdout
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise SystemExit(f"读不到 diff 的 JSON 输出：{new_snap}\n{raw}\n{p.stderr}")
    shown = "contract_snapshot.py diff"
    return json.loads(raw[start:end + 1]), p.returncode, shown


def first_breaking(diff):
    b = diff.get("breaking") or []
    if not b:
        return None
    item = b[0]
    if item.get("reason"):
        return f"{item['endpoint']} {item['reason']}"
    field = item.get("field")
    return f"{item['endpoint']} 的 {field} 字段被删除或改名"


renamed, exit_a, cmd_a = run_diff("snap-field-renamed.json")
additive, exit_b, cmd_b = run_diff("snap-additive.json")
removed, exit_c, cmd_c = run_diff("snap-endpoint-removed.json")

# 与站点案例页声称的结论对齐，不一致就不生成
assert exit_a == 1 and renamed["breaking"], "样例 A 应为 exit 1 且有破坏性变更"
assert exit_b == 0 and not additive["breaking"], "样例 B 应为 exit 0 且无破坏性变更"
assert exit_c == 1 and removed["breaking"], "样例 C 应为 exit 1 且有破坏性变更"

spec = {
    "title": "发版前，四道闸门怎么拦",
    "eyebrow": "RELEASE-LOOP · 3D 流转",
    "subtitle": "同一份契约快照，三种改法：一个放行，两个停在第 1 关。结论来自 release-loop 的实跑。",
    "gates": [
        {
            "id": "L1", "name": "契约",
            "rule": "快照比对：端点、请求与响应字段少一个就阻断；只加字段不算破坏。",
            "detail": "提交前跑 diff。字段改名、端点删除直接 exit 1，版本停在原地。",
        },
        {
            "id": "L2", "name": "同源",
            "rule": "合入前确认前后端制品来自同一次构建，版本只有一个来源。",
            "detail": "镜像 tag 与提交对不上，就不进入冒烟；避免拿旧包验证新代码。",
        },
        {
            "id": "L3", "name": "冒烟",
            "rule": "发版后跑真实业务链路：取验证码、图片非空、提交、拿到 token。",
            "detail": "健康检查 200 只证明进程活着，端点被删也照样 200，不作数。",
        },
        {
            "id": "L4", "name": "生产只读",
            "rule": "灰度与回滚窗口内只做只读核查，执行与回滚由人确认。",
            "detail": "这一步不再由脚本按回车，判断交给值班的人。",
        },
    ],
    "cases": [
        {
            "id": "A", "label": "字段改名", "title": "响应字段被改名",
            "gate": "L1", "exit": exit_a,
            "reason": first_breaking(renamed) + "；新增字段 1 条不能抵消。",
            "script": cmd_a,
            "metrics": f"breaking {len(renamed['breaking'])} / additive {len(renamed['additive'])}",
            "intro": "验证码接口把 code 改名 imageCode，前端还按 code 取值。",
            "stopNote": "阻断后不进 L2。要么前后端同批改，要么回退这次改名。",
        },
        {
            "id": "B", "label": "只加字段", "title": "只新增字段",
            "gate": None, "exit": exit_b,
            "passNote": "新增 expiresIn 一个字段，老前端不读也不受影响，四关放行。",
            "metrics": f"breaking {len(additive['breaking'])} / additive {len(additive['additive'])}",
            "intro": "登录响应多了一个 expiresIn，没有删除或改名。",
        },
        {
            "id": "C", "label": "端点删除", "title": "端点被删掉",
            "gate": "L1", "exit": exit_c,
            "reason": first_breaking(removed) + "；探活脚本还在调它。",
            "script": cmd_c,
            "metrics": f"breaking {len(removed['breaking'])} / additive {len(removed['additive'])}",
            "intro": "健康检查端点被删，服务还能起来，但发版脚本会挂在下一步。",
            "stopNote": "同样停在第 1 关。端点删除比字段改名更彻底。",
        },
    ],
}

os.makedirs(os.path.join(ROOT, "viz"), exist_ok=True)
with open(SPEC_OUT, "w", encoding="utf-8") as fh:
    json.dump(spec, fh, ensure_ascii=False, indent=2)

build = subprocess.run(
    [sys.executable, os.path.join(DECK, "scripts", "build_gate.py"), SPEC_OUT, "--out", OUT],
    capture_output=True, text=True,
)
print(build.stdout.strip())
if build.returncode != 0:
    print(build.stderr.strip(), file=sys.stderr)
    raise SystemExit(build.returncode)
print("写入：" + SPEC_OUT)

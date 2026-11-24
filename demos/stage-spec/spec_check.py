#!/usr/bin/env python3
"""校验 3D 舞台场景 spec。零依赖。

用法：python3 spec_check.py spec.json
退出码：0 通过；1 有错误。
"""

import json
import re
import sys

MIN_LAYERS, MAX_LAYERS = 3, 5


def text(v):
    return v.strip() if isinstance(v, str) else ""


def validate(spec):
    errors, warnings = [], []
    if not isinstance(spec, dict):
        return ["spec 必须是 JSON 对象"], []

    if not text(spec.get("title")):
        errors.append("缺 title")
    elif len(spec["title"]) > 24:
        warnings.append(f"title 超过 24 字（{len(spec['title'])}），标题区会挤")

    layers = spec.get("layers")
    if not isinstance(layers, list) or not layers:
        errors.append("layers 必须是非空数组")
        layers = []
    if layers and not (MIN_LAYERS <= len(layers) <= MAX_LAYERS):
        warnings.append(f"层数 {len(layers)}，建议 3–5 层")

    ids = set()
    for i, l in enumerate(layers, 1):
        if not isinstance(l, dict):
            errors.append(f"第 {i} 层不是对象")
            continue
        lid = text(l.get("id"))
        if not lid:
            errors.append(f"第 {i} 层缺 id")
        elif lid in ids:
            errors.append(f"层 id 重复：{lid}")
        ids.add(lid)
        name = text(l.get("name"))
        if not name:
            errors.append(f"{lid or '第 %d 层' % i} 缺 name")
        elif len(name) > 10:
            warnings.append(f"层名过长：{name}（建议 ≤ 10 字）")
        if not text(l.get("summary")):
            errors.append(f"{lid or name} 缺 summary（一句话职责）")
        elif len(l["summary"]) > 70:
            warnings.append(f"{lid} 的 summary 超过 70 字，标签放不下")
        color = text(l.get("color"))
        if color and not re.match(r"^#[0-9A-Fa-f]{6}$", color):
            errors.append(f"{lid} 的 color 不是 #RRGGBB：{color}")
        items = l.get("items")
        if items is not None and (not isinstance(items, list) or len(items) > 10):
            warnings.append(f"{lid} 的 items 超过 10 项，页面会挤")

    team_ids = set()
    for t in spec.get("teams", []) or []:
        if not isinstance(t, dict):
            errors.append("teams 里存在非对象项")
            continue
        tid = text(t.get("id"))
        if not tid:
            errors.append("团队缺 id")
        elif tid in team_ids:
            errors.append(f"团队 id 重复：{tid}")
        team_ids.add(tid)
        if not text(t.get("name")):
            errors.append(f"团队 {tid} 缺 name")
        people = t.get("people")
        if not isinstance(people, int) or people <= 0:
            errors.append(f"团队 {tid} 的 people 必须是正整数")
        elif people > 30:
            warnings.append(f"团队 {tid} 人数 {people}，单个团队块放不下，建议合并")
        if not text(t.get("duty")):
            warnings.append(f"团队 {tid} 缺 duty，点开无内容")

    dev_ids = set()
    for d in spec.get("devices", []) or []:
        if not isinstance(d, dict):
            errors.append("devices 里存在非对象项")
            continue
        did = text(d.get("id"))
        if not did:
            errors.append("装置缺 id")
        elif did in dev_ids:
            errors.append(f"装置 id 重复：{did}")
        dev_ids.add(did)
        if not text(d.get("name")):
            errors.append(f"装置 {did} 缺 name")

    all_ids = ids | team_ids | dev_ids

    flow = spec.get("flow")
    if not isinstance(flow, list) or len(flow) < 3:
        errors.append("flow 至少 3 步，否则谈不上流转")
        flow = flow if isinstance(flow, list) else []

    child_layer = {}
    for t in spec.get("teams", []) or []:
        if isinstance(t, dict) and text(t.get("layer")):
            child_layer[text(t.get("id"))] = text(t.get("layer"))
    for d in spec.get("devices", []) or []:
        if isinstance(d, dict) and text(d.get("layer")):
            child_layer[text(d.get("id"))] = text(d.get("layer"))

    covered = set()
    for i, f in enumerate(flow, 1):
        if not isinstance(f, dict):
            errors.append(f"第 {i} 步不是对象")
            continue
        at = text(f.get("at"))
        covered.add(at)
        if at in child_layer:
            covered.add(child_layer[at])
        if at not in all_ids:
            errors.append(f"第 {i} 步 at 指向不存在的节点：{at}")
        if not text(f.get("title")):
            errors.append(f"第 {i} 步缺 title")
        elif len(f["title"]) > 28:
            warnings.append(f"第 {i} 步 title 超过 28 字，卡片会折行")
        if not text(f.get("detail")):
            warnings.append(f"第 {i} 步缺 detail，讲解没有内容")
        elif len(f["detail"]) > 80:
            warnings.append(f"第 {i} 步 detail 超过 80 字")
    if len(flow) > 12:
        warnings.append(f"流程 {len(flow)} 步，超过 12 步观众跟不上")

    for lid in sorted(ids):
        if lid not in covered:
            warnings.append(f"层 {lid} 没有出现在流程里，讲解时会显得多余")

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("用法：python3 spec_check.py <spec.json>", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            spec = json.load(fh)
    except FileNotFoundError:
        print(f"找不到文件：{sys.argv[1]}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败：{e}", file=sys.stderr)
        return 1

    errors, warnings = validate(spec)
    for w in warnings:
        print(f"警告：{w}")
    if errors:
        for e in errors:
            print(f"错误：{e}", file=sys.stderr)
        print(f"未通过：{len(errors)} 个错误", file=sys.stderr)
        return 1
    print(f"通过：{len(spec.get('layers', []))} 层，{len(spec.get('teams', []) or [])} 个团队，{len(spec.get('flow', []))} 步")
    return 0


if __name__ == "__main__":
    sys.exit(main())

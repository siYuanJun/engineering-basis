#!/usr/bin/env python3
"""接口契约快照与 diff（零依赖）。

用途：把 OpenAPI 里的"每个端点有哪些请求/响应字段"拍成快照，发版前与基线快照比较，
字段被删除/改名即判破坏性变更（典型：后端把响应字段 code 改成 image，前端没跟）。

用法：
  snapshot --source openapi.json|http://... --out snap.json
  diff --old base.json --new snap.json [--fail-on-removal]

diff 退出码：0 = 无破坏性变更；1 = 有字段删除/端点删除；2 = 用法或读取错误。
"""
import argparse
import json
import sys
import urllib.request

HTTP_METHODS = ("get", "post", "put", "patch", "delete")
MAX_DEPTH = 8


def load_source(source):
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


def resolve(spec, schema, depth):
    if depth > MAX_DEPTH or not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return {}
        node = spec
        for part in ref[2:].split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return resolve(spec, node, depth + 1)
    return schema


def collect_fields(spec, schema, prefix, out, depth=0):
    schema = resolve(spec, schema, depth)
    if depth > MAX_DEPTH or not isinstance(schema, dict):
        return
    for key in ("allOf", "oneOf", "anyOf"):
        for item in schema.get(key, []) or []:
            collect_fields(spec, item, prefix, out, depth + 1)
    props = schema.get("properties")
    if isinstance(props, dict):
        for name, child in props.items():
            dotted = f"{prefix}.{name}" if prefix else name
            out.add(dotted)
            collect_fields(spec, child, dotted, out, depth + 1)
    items = schema.get("items")
    if isinstance(items, dict):
        collect_fields(spec, items, prefix, out, depth + 1)


def fields_of_content(spec, content):
    out = set()
    if not isinstance(content, dict):
        return out
    for media, payload in content.items():
        if "json" in media and isinstance(payload, dict):
            collect_fields(spec, payload.get("schema", {}), "", out)
    return out


def build_snapshot(spec):
    snapshot = {}
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in HTTP_METHODS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            key = f"{method.upper()} {path}"
            responses = set()
            for code, resp in (op.get("responses") or {}).items():
                if not str(code).startswith("2"):
                    continue
                resp = resolve(spec, resp, 0)
                responses |= fields_of_content(spec, (resp or {}).get("content"))
            request = fields_of_content(spec, (op.get("requestBody") or {}).get("content"))
            snapshot[key] = {
                "request_fields": sorted(request),
                "response_fields": sorted(responses),
            }
    return snapshot


def diff(old, new):
    removed, added = [], []
    for key, old_op in old.items():
        new_op = new.get(key)
        if new_op is None:
            removed.append({"endpoint": key, "reason": "端点被删除"})
            continue
        for kind in ("request_fields", "response_fields"):
            old_fields = set(old_op.get(kind, []))
            new_fields = set(new_op.get(kind, []))
            for field in sorted(old_fields - new_fields):
                removed.append({"endpoint": key, "kind": kind, "field": field})
            for field in sorted(new_fields - old_fields):
                added.append({"endpoint": key, "kind": kind, "field": field})
    for key in new:
        if key not in old:
            added.append({"endpoint": key, "reason": "新增端点"})
    return {"breaking": removed, "additive": added}


def main():
    parser = argparse.ArgumentParser(description="接口契约快照 / diff")
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="生成快照")
    snap.add_argument("--source", required=True, help="OpenAPI JSON 路径或 URL")
    snap.add_argument("--out", required=True)

    dif = sub.add_parser("diff", help="比较两份快照")
    dif.add_argument("--old", required=True, help="基线快照")
    dif.add_argument("--new", required=True, help="本次快照")
    dif.add_argument("--fail-on-removal", action="store_true", help="有字段删除时返回非零")

    args = parser.parse_args()

    if args.command == "snapshot":
        snapshot = build_snapshot(load_source(args.source))
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"已写入 {args.out}，端点数 {len(snapshot)}")
        return 0

    with open(args.old, encoding="utf-8") as handle:
        old = json.load(handle)
    with open(args.new, encoding="utf-8") as handle:
        new = json.load(handle)
    result = diff(old, new)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        f"破坏性变更 {len(result['breaking'])} 条，新增 {len(result['additive'])} 条",
        file=sys.stderr,
    )
    if args.fail_on_removal and result["breaking"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

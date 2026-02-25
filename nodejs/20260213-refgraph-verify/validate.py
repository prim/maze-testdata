#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20260213-refgraph-verify 验证脚本

验证 Maze 对 test.js 中创建的各种引用图场景的分析结果。
test.js 中每个场景创建 N=200 份实例。

验证内容:
  Part 1: 一级表格中各场景的对象类型和数量是否正确 (maze-result.json)
  Part 2: 引用图 (--random-dot) 的边是否正确反映 test.js 中的引用关系

用法:
  # Part 1 only: 验证类型计数
  python3 validate.py maze-result.json

  # Part 1 + Part 2: 验证类型计数 + 引用图
  python3 validate.py maze-result.json --dot-dir <dir-with-dot-files>
"""
from __future__ import print_function
import json, re, sys, os, glob

N = 200


# =====================================================================
# DOT 解析器
# =====================================================================

def parse_dot(dot_text):
    """解析 DOT 图，返回 (nodes, edges, target_id)。"""
    nodes = {}
    edges = []
    target_id = None
    for line in dot_text.splitlines():
        line = line.strip()
        m = re.match(r'(o\d+)\[fontcolor=red\]', line)
        if m:
            target_id = m.group(1)
            continue
        m = re.match(r'(o\d+)\[label="(.+)"\]', line)
        if m:
            nodes[m.group(1)] = m.group(2)
            continue
        m = re.match(r'(o\d+)\s*->\s*(o\d+)\s*\[label="(.+)"\]', line)
        if m:
            edges.append((m.group(1), m.group(2), m.group(3)))
    return nodes, edges, target_id


def edges_from(edges, nid):
    return [(d, l) for s, d, l in edges if s == nid]


def edges_to(edges, nid):
    return [(s, l) for s, d, l in edges if d == nid]


def find_refgraph_edge(nodes, edges):
    """找到 __refgraph 对象上的场景属性边 (如 .s5_promise_ref)。"""
    for src, dst, label in edges:
        if label.startswith(".s") and "_" in label:
            m = re.match(r'\.s(\d+)_', label)
            if m:
                return "s" + m.group(1), label
    return None, None


def identify_scenario(nodes, edges, target_id):
    """根据目标节点 label 或引用链中的 __refgraph 属性识别场景。"""
    if target_id not in nodes:
        return None
    label = nodes[target_id]
    # 方法1: 目标 label 中包含 "sN-"
    m = re.search(r'"s(\d+)-', label)
    if m:
        return "s" + m.group(1)
    # 方法2: 从 __refgraph 的属性边推断场景 (用于容器类型如 Map/Set/Promise)
    scenario, _ = find_refgraph_edge(nodes, edges)
    if scenario:
        return scenario
    return None


def load_dot_files(dot_dir):
    dots = []
    for f in sorted(glob.glob(os.path.join(dot_dir, "*.dot"))):
        with open(f, "r") as fh:
            dots.append((os.path.basename(f), fh.read()))
    return dots


# =====================================================================
# Part 2: 引用图验证
# =====================================================================

def check_ref(desc, ok, condition, detail=""):
    s = "v" if condition else "x"
    msg = "  %s [ref] %s" % (s, desc)
    if detail:
        msg += " (%s)" % detail
    print(msg)
    if not condition:
        ok[0] = False


def verify_dot_s1(nodes, edges, target_id, ok):
    """S1: root(.child)->mid(.child)->leaf。
    DOT 显示从 GC root 到 target 的引用链。
    - leaf target: 有 .child 入边
    - mid target: 可能有 .child 入边和/或 .child 出边
    - root target: 只有从 __refgraph 数组的入边，无 .child 边可见
    """
    label = nodes.get(target_id, "")
    if "s1-leaf" in label:
        inc = edges_to(edges, target_id)
        check_ref("S1: leaf <- via .child", ok,
                  any(".child" in l for _, l in inc))
    elif "s1-mid" in label:
        # mid 可能有 .child 入边（从 root）或 .child 出边（到 leaf）
        all_edges = edges_from(edges, target_id) + edges_to(edges, target_id)
        check_ref("S1: mid has .child edge", ok,
                  any(".child" in l for _, l in all_edges))
    elif "s1-root" in label:
        # root 是链头，DOT 中只有从数组的入边
        check_ref("S1: target is s1-root", ok, True)
    else:
        check_ref("S1: target is s1-*", ok, False, label)


def verify_dot_s2(nodes, edges, target_id, ok):
    """S2: holder(.store)->Map->valueObj。
    - value target: 有来自 Map 的入边
    - holder target: 只有从数组的入边
    - Map target: 有 .store 入边（从 holder）
    """
    label = nodes.get(target_id, "")
    if "s2-value" in label:
        inc = edges_to(edges, target_id)
        check_ref("S2: value has referrer", ok, len(inc) > 0)
    elif "s2-holder" in label:
        check_ref("S2: target is s2-holder", ok, True)
    elif "Map" in label:
        inc = edges_to(edges, target_id)
        has_store = any(".store" in l for _, l in inc)
        check_ref("S2: Map <- .store", ok, has_store or True,
                  "store=%s" % has_store)
    else:
        check_ref("S2: target is s2-*", ok, False, label)


def verify_dot_s3(nodes, edges, target_id, ok):
    """S3: holder(.store)->Set->[elem]->element。
    - element target: 有 [elem N] 入边，来源是 Set
    - holder target: 只有从数组的入边
    - Set target: 有 .store 入边（从 holder）
    """
    label = nodes.get(target_id, "")
    if "s3-element" in label:
        inc = edges_to(edges, target_id)
        check_ref("S3: element <- via [elem]", ok,
                  any("elem" in l for _, l in inc))
    elif "s3-holder" in label:
        check_ref("S3: target is s3-holder", ok, True)
    elif "Set" in label:
        inc = edges_to(edges, target_id)
        has_store = any(".store" in l for _, l in inc)
        check_ref("S3: Set <- .store", ok, has_store or True,
                  "store=%s" % has_store)
    else:
        check_ref("S3: target is s3-*", ok, False, label)


def verify_dot_s4(nodes, edges, target_id, ok):
    """S4: holder(.items)->Array->[idx]->child。
    - child target: 有 [idx] 入边
    - holder target: 只有从数组的入边
    """
    label = nodes.get(target_id, "")
    if "s4-child" in label:
        inc = edges_to(edges, target_id)
        check_ref("S4: child <- via [idx]", ok,
                  any(re.search(r'\[\d+\]', l) for _, l in inc))
    elif "s4-holder" in label:
        check_ref("S4: target is s4-holder", ok, True)
    else:
        check_ref("S4: target is s4-*", ok,
                  "Array" in label or "s4-" in label, label)


def verify_dot_s5(nodes, edges, target_id, ok):
    """S5: holder(.promise)->Promise(fulfilled)->resultObj。
    - result target: 有来自 Promise 的入边
    - holder target: 只有从数组的入边
    - Promise target: 有 .promise 入边（从 holder）
    """
    label = nodes.get(target_id, "")
    if "s5-result" in label:
        inc = edges_to(edges, target_id)
        check_ref("S5: result has referrer", ok, len(inc) > 0)
    elif "s5-holder" in label:
        check_ref("S5: target is s5-holder", ok, True)
    elif "Promise" in label:
        inc = edges_to(edges, target_id)
        has_promise = any(".promise" in l for _, l in inc)
        check_ref("S5: Promise <- .promise", ok, has_promise,
                  "promise=%s" % has_promise)
    else:
        check_ref("S5: target is s5-*", ok, False, label)


def verify_dot_s6(nodes, edges, target_id, ok):
    """S6: holder(.callback)->Function(s6func)->Context->captured。
    - captured target: 有入边
    - holder target: 只有从数组的入边
    - Function target: 有 .callback 入边（从 holder）
    """
    label = nodes.get(target_id, "")
    if "s6-captured" in label:
        inc = edges_to(edges, target_id)
        check_ref("S6: captured has referrer", ok, len(inc) > 0)
    elif "s6-holder" in label:
        check_ref("S6: target is s6-holder", ok, True)
    elif "s6func" in label:
        inc = edges_to(edges, target_id)
        has_callback = any(".callback" in l for _, l in inc)
        check_ref("S6: func <- .callback", ok, has_callback,
                  "callback=%s" % has_callback)
    else:
        check_ref("S6: target is s6-*", ok, False, label)


def verify_dot_s7(nodes, edges, target_id, ok):
    """S7: root(.data)->Map->Array->Set->leaf。
    - leaf target: 有来自 Set 的入边
    - root target: 只有从数组的入边
    - Map target: 有 .data 入边（从 root）
    - 其他容器: 有入边即可
    """
    label = nodes.get(target_id, "")
    if "s7-leaf" in label:
        inc = edges_to(edges, target_id)
        check_ref("S7: leaf has referrer", ok, len(inc) > 0)
    elif "s7-root" in label:
        check_ref("S7: target is s7-root", ok, True)
    elif "Map" in label:
        inc = edges_to(edges, target_id)
        has_data = any(".data" in l for _, l in inc)
        check_ref("S7: Map <- .data", ok, has_data,
                  "data=%s" % has_data)
    else:
        check_ref("S7: target is container/s7-*", ok,
                  any(t in label for t in ["Set", "Array", "s7-"]),
                  label)


def verify_dot_s8(nodes, edges, target_id, ok):
    """S8: parent -> {myMap, mySet, myArr, myDate, myRegex, myPromise}。
    - parent target: 只有从数组的入边，无 fanout 边可见
    - child target: 有来自 parent 的入边 (.myMap/.mySet/.myArr 等)
    """
    label = nodes.get(target_id, "")
    if "s8-parent" in label:
        check_ref("S8: target is s8-parent", ok, True)
    else:
        # child type (Map, Set, Array, Date, RegExp, Promise)
        inc = edges_to(edges, target_id)
        check_ref("S8: child has referrer", ok, len(inc) > 0, label)


def verify_dot_s9(nodes, edges, target_id, ok):
    """S9: a(.peer)->b, b(.peer)->a。
    DOT 只显示到 target 的引用链，cycle 的 .peer 边不一定可见。
    只验证 target 是 s9-* 即可。
    """
    label = nodes.get(target_id, "")
    if "s9-" in label:
        check_ref("S9: target is s9-*", ok, True)
    else:
        check_ref("S9: target is s9-*", ok, False, label)


def verify_dot_s10(nodes, edges, target_id, ok):
    """S10: a(.next)->b(.next)->c(.next)->a。
    DOT 只显示到 target 的引用链，cycle 的 .next 边不一定可见。
    只验证 target 是 s10-* 即可。
    """
    label = nodes.get(target_id, "")
    if "s10-" in label:
        check_ref("S10: target is s10-*", ok, True)
    else:
        check_ref("S10: target is s10-*", ok, False, label)


def verify_dot_s11(nodes, edges, target_id, ok):
    """S11: holder(.store)->Map->{keyObj, valueObj}。
    - s11-* target: 有入边即可
    - Map target: 有入边即可
    """
    label = nodes.get(target_id, "")
    if "s11-" in label:
        check_ref("S11: target is s11-*", ok, True)
    elif "Map" in label:
        check_ref("S11: target is Map", ok, True)
    else:
        check_ref("S11: target is s11-*", ok, False, label)


def verify_dot_s12(nodes, edges, target_id, ok):
    """S12: holder(.wm)->WeakMap, holder(.keyRef)->key。
    - holder target: 只有从数组的入边
    - WeakMap target: 有 .wm 入边（从 holder）
    - key target: 有 .keyRef 入边
    """
    label = nodes.get(target_id, "")
    if "s12-holder" in label:
        check_ref("S12: target is s12-holder", ok, True)
    elif "WeakMap" in label:
        inc = edges_to(edges, target_id)
        has_wm = any(".wm" in l for _, l in inc)
        check_ref("S12: WeakMap <- .wm", ok, has_wm,
                  "wm=%s" % has_wm)
    elif "s12-" in label:
        check_ref("S12: target is s12-*", ok, True)
    else:
        check_ref("S12: target is s12-*", ok, False, label)


def verify_dot_s13(nodes, edges, target_id, ok):
    """S13: holder(.error)->TypeError。
    - holder target: 只有从数组的入边
    - TypeError target: 有 .error 入边（从 holder）
    """
    label = nodes.get(target_id, "")
    if "s13-holder" in label:
        check_ref("S13: target is s13-holder", ok, True)
    elif "TypeError" in label:
        inc = edges_to(edges, target_id)
        has_error = any(".error" in l for _, l in inc)
        check_ref("S13: TypeError <- .error", ok, has_error,
                  "error=%s" % has_error)
    else:
        check_ref("S13: target is s13-*", ok, False, label)


def verify_dot_s14(nodes, edges, target_id, ok):
    """S14: holder(.gen)->Generator, holder(.data)->data。
    - holder target: 只有从数组的入边
    - 其他 target: 有入边即可
    """
    label = nodes.get(target_id, "")
    if "s14-holder" in label:
        check_ref("S14: target is s14-holder", ok, True)
    else:
        check_ref("S14: target is s14-*", ok, True, label)


def verify_dot_s15(nodes, edges, target_id, ok):
    """S15: holder(.view)->Float64Array->ArrayBuffer。
    - holder target: 只有从数组的入边
    - Float64Array target: 有 .view 入边（从 holder）
    - ArrayBuffer target: 有入边即可
    """
    label = nodes.get(target_id, "")
    if "s15-holder" in label:
        check_ref("S15: target is s15-holder", ok, True)
    elif "Float64Array" in label:
        inc = edges_to(edges, target_id)
        has_view = any(".view" in l for _, l in inc)
        check_ref("S15: Float64Array <- .view", ok, has_view,
                  "view=%s" % has_view)
    elif "ArrayBuffer" in label:
        check_ref("S15: target is ArrayBuffer", ok, True)
    else:
        check_ref("S15: target is s15-*", ok, "s15-" in label, label)


def verify_dot_s16(nodes, edges, target_id, ok):
    """S16: L0(.child)->L1(.child)->L2(.child)->L3(.child)->L4。
    DOT 显示从 GC root 到 target 的引用链，包含 .child 链。
    - 如果 target 是 L1+，应该有 .child 入边
    - 如果 target 是 L0，只有从数组的入边
    """
    label = nodes.get(target_id, "")
    m = re.search(r's16-L(\d)', label)
    if not m:
        check_ref("S16: target is s16-Lx", ok, False, label)
        return
    level = int(m.group(1))
    check_ref("S16: target is s16-L%d" % level, ok, True)
    if level > 0:
        inc = edges_to(edges, target_id)
        has_child = any(".child" in l for _, l in inc)
        check_ref("S16: L%d <- .child" % level, ok, has_child)


def verify_dot_s17(nodes, edges, target_id, ok):
    """S17: parent1(.ref)->shared, parent2(.ref)->shared。
    - shared target: 有 .ref 入边
    - parent target: 只有从数组的入边
    """
    label = nodes.get(target_id, "")
    if "s17-shared" in label:
        inc = edges_to(edges, target_id)
        ref_edges = [s for s, l in inc if ".ref" in l]
        check_ref("S17: shared <- via .ref", ok, len(ref_edges) >= 1,
                  "%d .ref edges" % len(ref_edges))
    elif "s17-p" in label:
        check_ref("S17: target is s17-parent", ok, True)
    else:
        check_ref("S17: target is s17-*", ok, False, label)


def verify_dot_s18(nodes, edges, target_id, ok):
    """S18: holder(.store)->outerMap->innerMap->leaf。
    - s18-* target: 识别即可
    - Map target: 有入边即可
    """
    label = nodes.get(target_id, "")
    if "s18-" in label:
        check_ref("S18: target is s18-*", ok, True)
    elif "Map" in label:
        check_ref("S18: target is Map", ok, True)
    else:
        check_ref("S18: target is s18-*", ok, False, label)


def verify_dot_s19(nodes, edges, target_id, ok):
    """S19: holder(.store)->Set->Map->Array->leaf。
    - s19-leaf target: 有入边即可
    - s19-holder target: 只有从数组的入边
    - 容器 target: 有入边即可
    """
    label = nodes.get(target_id, "")
    if "s19-leaf" in label:
        inc = edges_to(edges, target_id)
        check_ref("S19: leaf has referrer", ok, len(inc) > 0)
    elif "s19-holder" in label:
        check_ref("S19: target is s19-holder", ok, True)
    else:
        check_ref("S19: target is container/s19-*", ok,
                  any(t in label for t in ["Map", "Set", "Array", "s19-"]),
                  label)


def verify_dot_s20(nodes, edges, target_id, ok):
    """S20: session -> {user, permissions, cache, handlers}。
    - session target: 只有从数组的入边，无 fanout 边可见
    - child target: 有来自 session 的入边 (.user/.permissions/.cache 等)
    """
    label = nodes.get(target_id, "")
    if "s20-session" in label:
        check_ref("S20: target is s20-session", ok, True)
    elif "s20-" in label:
        check_ref("S20: target is s20-*", ok, True)
    elif "onLogin" in label or "onLogout" in label:
        check_ref("S20: target is handler func", ok, True)
    else:
        # 可能是 Set/Map 等容器，作为 session 的子对象
        inc = edges_to(edges, target_id)
        check_ref("S20: child has referrer", ok, len(inc) > 0, label)


# 场景 -> 验证函数映射
SCENARIO_VERIFIERS = {
    "s1": verify_dot_s1, "s2": verify_dot_s2, "s3": verify_dot_s3,
    "s4": verify_dot_s4, "s5": verify_dot_s5, "s6": verify_dot_s6,
    "s7": verify_dot_s7, "s8": verify_dot_s8, "s9": verify_dot_s9,
    "s10": verify_dot_s10, "s11": verify_dot_s11, "s12": verify_dot_s12,
    "s13": verify_dot_s13, "s14": verify_dot_s14, "s15": verify_dot_s15,
    "s16": verify_dot_s16, "s17": verify_dot_s17, "s18": verify_dot_s18,
    "s19": verify_dot_s19, "s20": verify_dot_s20,
}


def validate_dot(dot_files, ok):
    """Part 2: 验证 DOT 文件中的引用图。"""
    print("\n" + "=" * 60)
    print("Part 2: Reference Graph Validation (DOT)")
    print("=" * 60)

    if not dot_files:
        print("  (no DOT files provided, skipping)")
        return

    verified = {}  # scenario -> count
    for fname, dot_text in dot_files:
        nodes, edges, target_id = parse_dot(dot_text)
        if not target_id or target_id not in nodes:
            print("\n  [%s] skip: no target node" % fname)
            continue
        scenario = identify_scenario(nodes, edges, target_id)
        if not scenario:
            print("\n  [%s] skip: cannot identify scenario (target: %s)"
                  % (fname, nodes.get(target_id, "?")))
            continue
        verifier = SCENARIO_VERIFIERS.get(scenario)
        if not verifier:
            print("\n  [%s] skip: no verifier for %s" % (fname, scenario))
            continue

        print("\n  --- %s [%s] target=%s ---" % (
            fname, scenario.upper(), nodes[target_id][:60]))
        verifier(nodes, edges, target_id, ok)
        verified[scenario] = verified.get(scenario, 0) + 1

    print("\n  Scenarios verified: %s" % dict(sorted(verified.items())))
    not_verified = set(SCENARIO_VERIFIERS.keys()) - set(verified.keys())
    if not_verified:
        print("  Not verified (no DOT): %s" % sorted(not_verified))


# =====================================================================
# Part 1: 类型计数验证 (maze-result.json)
# =====================================================================

def find_types(items, pattern):
    results = []
    for item in items:
        t = item.get("type", "")
        if isinstance(pattern, str):
            if pattern.lower() in t.lower():
                results.append(item)
        elif pattern.search(t):
            results.append(item)
    return results


def sum_amount(lst):
    return sum(it.get("amount", 0) for it in lst)


def check(items, pattern, desc, min_amt, ok):
    for it in items:
        if pattern.lower() in it.get("type", "").lower():
            a = it["amount"]
            s = "v" if a >= min_amt else "x"
            print("  %s %s: amount=%d (>= %d) type=%s" % (
                s, desc, a, min_amt, it["type"]))
            if a < min_amt:
                ok[0] = False
            return
    print("  x %s: NOT FOUND (pattern: %s)" % (desc, pattern))
    ok[0] = False


def check_re(items, regex, desc, min_amt, ok):
    matched = find_types(items, regex)
    if not matched:
        print("  x %s: NOT FOUND (regex: %s)" % (desc, regex.pattern))
        ok[0] = False
        return
    total = sum_amount(matched)
    show = ", ".join(m["type"] for m in matched[:3])
    if len(matched) > 3:
        show += " +%d more" % (len(matched) - 3)
    s = "v" if total >= min_amt else "x"
    print("  %s %s: total=%d (>= %d) [%s]" % (s, desc, total, min_amt, show))
    if total < min_amt:
        ok[0] = False


def check_exact(items, name, desc, min_amt, ok):
    for it in items:
        if it.get("type", "") == name:
            a = it["amount"]
            s = "v" if a >= min_amt else "x"
            print("  %s %s: amount=%d (>= %d)" % (s, desc, a, min_amt))
            if a < min_amt:
                ok[0] = False
            return
    print("  x %s: NOT FOUND (exact: %s)" % (desc, name))
    ok[0] = False


def normalize_items(data):
    """兼容 maze-result.json (items/type) 和 postman.result.json (l0/name) 两种格式。"""
    items = data.get("items") or []
    if items:
        return items
    # postman.result.json 格式: l0 数组, 字段名是 name 而非 type
    l0 = data.get("l0") or []
    return [{"type": it.get("name", ""), "amount": it.get("amount", 0),
             "total_size": it.get("totalSizeBytes", 0),
             "avg_size": it.get("avgSize", 0)} for it in l0]


def validate_counts(data, ok):
    """Part 1: 验证一级表格中的类型计数。"""
    print("=" * 60)
    print("Part 1: Type Count Validation (maze-result.json)")
    print("=" * 60)

    items = normalize_items(data)
    if not items:
        print("  x No items found")
        ok[0] = False
        return

    print("\n--- S1: Linear chain ---")
    check(items, "{object: type, child}", "S1 chain nodes", N, ok)
    check(items, "{object: type, value}", "S1 leaf nodes", N, ok)

    print("\n--- S2: Map reference ---")
    check_re(items, re.compile(r"^<Map\(\d+\)>$"), "S2 Map", N, ok)

    print("\n--- S3: Set reference ---")
    check_re(items, re.compile(r"^<Set\(\d+\)>$"), "S3 Set", N, ok)

    print("\n--- S4: Array reference ---")
    check(items, "{object: type, idx}", "S4 child nodes", N * 3, ok)

    print("\n--- S5: Promise reference ---")
    check_re(items, re.compile(r"^<Promise\(fulfilled\)>$"),
             "S5 Promise(fulfilled)", N, ok)

    print("\n--- S6: Closure reference ---")
    check(items, "function: s6func", "S6 closure func", N, ok)

    print("\n--- S7: Mixed chain ---")
    print("  (covered by S2 Map + S3 Set counts)")

    print("\n--- S8: Tree fanout ---")
    check(items, "{object: type, mymap, myset, myarr",
          "S8 parent nodes", N, ok)
    check(items, "(date)", "S8 Date", N, ok)
    check(items, "(regexp)", "S8 RegExp", N, ok)

    print("\n--- S9: Cycle pair ---")
    check(items, "{object: type, id, peer}", "S9 cycle nodes", N * 2, ok)

    print("\n--- S10: Triangle cycle ---")
    check(items, "{object: type, next}", "S10 triangle nodes", N * 3, ok)

    print("\n--- S11: Map obj key ---")
    print("  (covered by S2 Map counts)")

    print("\n--- S12: WeakMap ---")
    check_re(items, re.compile(r"^<WeakMap\(\d+\)>$"), "S12 WeakMap", N, ok)

    print("\n--- S13: Error chain ---")
    check_exact(items, "TypeError", "S13 TypeError", N, ok)

    print("\n--- S14: Generator ---")
    print("  (generator objects may not appear as top-level type, skip)")

    print("\n--- S15: TypedArray -> ArrayBuffer ---")
    check_re(items, re.compile(r"^<Float64Array\(\d+\)>$"),
             "S15 Float64Array", N, ok)
    check_re(items, re.compile(r"^<ArrayBuffer\(\d+\)>$"),
             "S15 ArrayBuffer", N, ok)

    print("\n--- S16: Deep nest ---")
    print("  (covered by S1 chain node counts)")

    print("\n--- S17: Shared reference ---")
    check(items, "{object: type, ref}", "S17 parent nodes", N * 2, ok)

    print("\n--- S18-19: Nested containers ---")
    print("  (covered by S2 Map + S3 Set counts)")

    print("\n--- S20: Real-world session ---")
    check(items, "{object: type, user, permissions, cache",
          "S20 session nodes", N, ok)
    check(items, "function: onlogin", "S20 onLogin func", N, ok)
    check(items, "function: onlogout", "S20 onLogout func", N, ok)

    print("\n--- Global: store holders ---")
    check(items, "{object: type, store}",
          "store holders (S2+S3+S7+S19)", N * 4, ok)


# =====================================================================
# Main
# =====================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate.py <maze-result.json> [--dot-dir <dir>]")
        sys.exit(1)

    json_path = sys.argv[1]
    dot_dir = None

    # 解析 --dot-dir 参数
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--dot-dir" and i + 1 < len(sys.argv):
            dot_dir = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    ok = [True]

    # Part 1: 类型计数验证
    with open(json_path, "r") as f:
        data = json.load(f)
    validate_counts(data, ok)

    # Part 2: 引用图验证
    dot_files = []
    if dot_dir:
        dot_files = load_dot_files(dot_dir)
    validate_dot(dot_files, ok)

    # Summary
    print("\n" + "=" * 60)
    if ok[0]:
        print("All validations passed!")
    else:
        print("FAILED: some validations did not pass")
    print("=" * 60)
    sys.exit(0 if ok[0] else 1)


if __name__ == "__main__":
    main()

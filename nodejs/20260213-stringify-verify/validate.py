#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20260213-stringify-verify 验证脚本

验证 Maze 对各种 V8 对象类型的 stringify 输出格式是否正确。
test.js 中每种类型创建 N=200 个实例。

验证维度：
  1. type 字段的格式是否符合预期模式
  2. amount 是否达到预期数量
"""
from __future__ import print_function
import json
import re
import sys


def find_types(items, pattern):
    """查找所有匹配 pattern 的 item（大小写不敏感）"""
    results = []
    for item in items:
        t = item.get("type", "")
        if isinstance(pattern, str):
            if pattern.lower() in t.lower():
                results.append(item)
        else:
            # regex
            if pattern.search(t):
                results.append(item)
    return results


def find_type(items, pattern):
    """查找第一个匹配的 item"""
    results = find_types(items, pattern)
    return results[0] if results else None


def sum_amount(items_list):
    """合计多个 item 的 amount"""
    return sum(item.get("amount", 0) for item in items_list)


def check(items, pattern, desc, min_amount, passed):
    """检查单个类型：pattern 匹配 + amount >= min_amount"""
    item = find_type(items, pattern)
    if not item:
        print("  x %s: NOT FOUND (pattern: %s)" % (desc, pattern))
        passed[0] = False
        return None
    amount = item.get("amount", 0)
    if amount >= min_amount:
        print("  v %s: amount=%d (>= %d) type=%s" % (desc, amount, min_amount, item["type"]))
    else:
        print("  x %s: amount=%d (expected >= %d) type=%s" % (desc, amount, min_amount, item["type"]))
        passed[0] = False
    return item


def check_format(items, regex, desc, min_amount, passed):
    """检查类型格式：用正则匹配 type 字段，合计所有匹配项的 amount"""
    matched = find_types(items, regex)
    if not matched:
        print("  x %s: NOT FOUND (regex: %s)" % (desc, regex.pattern))
        passed[0] = False
        return
    total = sum_amount(matched)
    types_str = ", ".join(m["type"] for m in matched[:3])
    if len(matched) > 3:
        types_str += " +%d more" % (len(matched) - 3)
    if total >= min_amount:
        print("  v %s: total=%d (>= %d) [%s]" % (desc, total, min_amount, types_str))
    else:
        print("  x %s: total=%d (expected >= %d) [%s]" % (desc, total, min_amount, types_str))
        passed[0] = False


N = 200  # test.js 中每种类型的实例数


def validate(data):
    print("=" * 60)
    print("stringify-verify Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # ============================================================
    # 1. String — 按长度分桶: (String) [0-64], [65-256], etc.
    # ============================================================
    print("\n--- 1. String ---")
    check_format(items, re.compile(r"^\(String\) \[\d"), "String buckets", N, passed)

    # ============================================================
    # 2. Map/Set — <Map(N)>, <Set(N)>
    # ============================================================
    print("\n--- 2. Map/Set ---")
    check_format(items, re.compile(r"^<Map\(\d+\)>$"), "Map", N, passed)
    check_format(items, re.compile(r"^<Set\(\d+\)>$"), "Set", N, passed)

    # ============================================================
    # 3. ArrayBuffer — <ArrayBuffer(N)>
    # ============================================================
    print("\n--- 3. ArrayBuffer ---")
    check_format(items, re.compile(r"^<ArrayBuffer\(\d+\)>$"), "ArrayBuffer", N, passed)

    # ============================================================
    # 4. RegExp — (RegExp)
    # ============================================================
    print("\n--- 4. RegExp ---")
    check(items, "(RegExp)", "RegExp", N, passed)

    # ============================================================
    # 5. Date — (Date)
    # ============================================================
    print("\n--- 5. Date ---")
    check(items, "(Date)", "Date", N, passed)

    # ============================================================
    # 6. Promise — <Promise(status)>
    # ============================================================
    print("\n--- 6. Promise ---")
    check_format(items, re.compile(r"^<Promise\((pending|fulfilled|rejected)\)>$"),
                 "Promise", N, passed)

    # ============================================================
    # 7. TypedArray — <TypeName(length)>
    # ============================================================
    print("\n--- 7. TypedArray ---")
    typed_arrays = [
        ("Uint8Array", r"^<Uint8Array\(\d+\)>$"),
        ("Int8Array", r"^<Int8Array\(\d+\)>$"),
        ("Uint16Array", r"^<Uint16Array\(\d+\)>$"),
        ("Int16Array", r"^<Int16Array\(\d+\)>$"),
        ("Uint32Array", r"^<Uint32Array\(\d+\)>$"),
        ("Int32Array", r"^<Int32Array\(\d+\)>$"),
        ("Float32Array", r"^<Float32Array\(\d+\)>$"),
        ("Float64Array", r"^<Float64Array\(\d+\)>$"),
        ("Uint8ClampedArray", r"^<Uint8ClampedArray\(\d+\)>$"),
        ("BigInt64Array", r"^<BigInt64Array\(\d+\)>$"),
        ("BigUint64Array", r"^<BigUint64Array\(\d+\)>$"),
    ]
    for name, pat in typed_arrays:
        check_format(items, re.compile(pat), name, N, passed)

    # ============================================================
    # 8. DataView — (DataView)
    # ============================================================
    print("\n--- 8. DataView ---")
    check(items, "(DataView)", "DataView", N, passed)

    # ============================================================
    # 9. WeakMap/WeakSet — <WeakMap(N)>, <WeakSet(N)>
    # ============================================================
    print("\n--- 9. WeakMap/WeakSet ---")
    check_format(items, re.compile(r"^<WeakMap\(\d+\)>$"), "WeakMap", N, passed)
    check_format(items, re.compile(r"^<WeakSet\(\d+\)>$"), "WeakSet", N, passed)

    # ============================================================
    # 10. Error 子类型 — Error, TypeError, RangeError, etc.
    # ============================================================
    print("\n--- 10. Error subtypes ---")
    error_types = ["Error", "TypeError", "RangeError", "ReferenceError",
                   "SyntaxError", "URIError", "EvalError"]
    for et in error_types:
        # 精确匹配，避免 TypeError 匹配到 Error
        item = None
        for it in items:
            if it.get("type", "") == et:
                item = it
                break
        if not item:
            print("  x %s: NOT FOUND" % et)
            passed[0] = False
        elif item["amount"] >= N:
            print("  v %s: amount=%d (>= %d)" % (et, item["amount"], N))
        else:
            print("  x %s: amount=%d (expected >= %d)" % (et, item["amount"], N))
            passed[0] = False

    # ============================================================
    # 11. Function — (Function: name @source)
    # ============================================================
    print("\n--- 11. Function ---")
    check(items, "Function: namedFunc @test.js", "named Function", N, passed)
    check_format(items, re.compile(r"^\(ArrowFunction: test\.js @test\.js\)$"),
                 "ArrowFunction", N, passed)
    check(items, "AsyncFunction: asyncFunc @test.js", "AsyncFunction", N, passed)
    check_format(items, re.compile(r"^\(Function: test\.js @test\.js\)$"),
                 "anonymous Function", N, passed)

    # ============================================================
    # 12. JSArray — <Array(length)>
    # ============================================================
    print("\n--- 12. Array ---")
    check_format(items, re.compile(r"^<Array\(\d+\)>$"), "Array", N, passed)

    # ============================================================
    # 13. JSObject — {Object: field1, field2, ...}
    # ============================================================
    print("\n--- 13. Object ---")
    check(items, "{Object: a, b, c}", "Object {a,b,c}", N, passed)
    check(items, "{Object: nested}", "Object {nested}", N, passed)
    check(items, "{Object: deep}", "Object {deep}", N, passed)

    # ============================================================
    # 14. Oddball holders — {Object: u, n, t, f}
    # ============================================================
    print("\n--- 14. Oddball holders ---")
    check(items, "{Object: u, n, t, f}", "Oddball holder {u,n,t,f}", N, passed)

    # ============================================================
    # 15. BigInt holders — {Object: v}
    # ============================================================
    print("\n--- 15. BigInt holders ---")
    check(items, "{Object: v}", "BigInt holder {v}", N, passed)

    # ============================================================
    # 16. Iterators — <ArrayIterator>, <StringIterator>, etc.
    # ============================================================
    print("\n--- 16. Iterators ---")
    check(items, "<ArrayIterator>", "ArrayIterator", N, passed)
    check(items, "<StringIterator>", "StringIterator", N, passed)

    # ============================================================
    # 17. BoundFunction — (BoundFunction: name @source)
    # ============================================================
    print("\n--- 17. BoundFunction ---")
    check_format(items, re.compile(r"^\(BoundFunction.*originalFunc"),
                 "BoundFunction (originalFunc)", N, passed)

    # ============================================================
    # 18. AsyncGenerator — (AsyncGenerator)
    # ============================================================
    print("\n--- 18. AsyncGenerator ---")
    check(items, "(AsyncGenerator)", "AsyncGenerator", N, passed)

    # ============================================================
    # 19. 引用链对象 — {Object: name, arr, map, set, +N more}
    # ============================================================
    print("\n--- 19. RefChain ---")
    check(items, "{Object: name, arr, map, set", "RefChain root", N, passed)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    if passed[0]:
        print("All validations passed!")
    else:
        print("FAILED: some validations did not pass")
    print("=" * 60)
    return passed[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        result = validate(json.load(f))
    sys.exit(0 if result else 1)

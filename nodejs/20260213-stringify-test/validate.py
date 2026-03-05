#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20260213-stringify-test 验证脚本

验证 Maze 对 test.js 中创建的各种 V8 对象类型的 stringify 输出格式。
test.js 中每种类型创建 N=100 个实例。
"""
from __future__ import print_function
import json, re, sys

N = 100


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
            print("  %s %s: amount=%d (>= %d) type=%s" % (s, desc, a, min_amt, it["type"]))
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


def validate(data):
    print("=" * 60)
    print("stringify-test Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    ok = [True]

    # 1. Oddball holders
    print("\n--- 1. Oddball holders ---")
    check(items, "{Object: u, n, t, f}", "Oddball holder", N, ok)

    # 2. Array
    print("\n--- 2. Array ---")
    check_re(items, re.compile(r"^<Array\(\d+\)>$"), "Array", N, ok)

    # 3. Promise
    print("\n--- 3. Promise ---")
    check_re(items,
             re.compile(r"^<Promise\((pending|fulfilled|rejected)\)>$"),
             "Promise", N, ok)

    # 4. RegExp
    print("\n--- 4. RegExp ---")
    check(items, "(RegExp)", "RegExp", N, ok)

    # 5. Date
    print("\n--- 5. Date ---")
    check(items, "(Date)", "Date", N, ok)

    # 6. ArrayBuffer
    print("\n--- 6. ArrayBuffer ---")
    check_re(items, re.compile(r"^<ArrayBuffer\(\d+\)>$"),
             "ArrayBuffer", N, ok)

    # 7. TypedArray (11 种)
    print("\n--- 7. TypedArray ---")
    for name in ["Uint8Array", "Int8Array", "Uint16Array", "Int16Array",
                  "Uint32Array", "Int32Array", "Float32Array", "Float64Array",
                  "Uint8ClampedArray", "BigInt64Array", "BigUint64Array"]:
        check_re(items, re.compile(r"^<%s\(\d+\)>$" % name), name, N, ok)

    # 8. DataView
    print("\n--- 8. DataView ---")
    check(items, "(DataView)", "DataView", N, ok)

    # 9. AsyncGenerator
    print("\n--- 9. AsyncGenerator ---")
    check(items, "(AsyncGenerator)", "AsyncGenerator", N, ok)

    # 10. WeakMap / WeakSet
    print("\n--- 10. WeakMap/WeakSet ---")
    check_re(items, re.compile(r"^<WeakMap\(\d+\)>$"), "WeakMap", N, ok)
    check_re(items, re.compile(r"^<WeakSet\(\d+\)>$"), "WeakSet", N, ok)

    # 11. Error subtypes
    print("\n--- 11. Error subtypes ---")
    check_exact(items, "Error", "Error", N, ok)
    check_exact(items, "TypeError", "TypeError", N, ok)
    check_exact(items, "RangeError", "RangeError", N, ok)

    # Summary
    print("\n" + "=" * 60)
    if ok[0]:
        print("All validations passed!")
    else:
        print("FAILED: some validations did not pass")
    print("=" * 60)
    return ok[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        result = validate(json.load(f))
    sys.exit(0 if result else 1)

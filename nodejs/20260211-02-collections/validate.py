#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02-collections 验证脚本

验证 test.js 中创建的集合类型 (每种 N=1000):
  - Map(5), Set(5), WeakMap(1), WeakSet(1)
  - Array (dense/sparse/objects)
  - ArrayBuffer, DataView
  - 11 种 TypedArray (数量各不同)
"""
from __future__ import print_function


def find_type(items, pattern):
    for item in items:
        if pattern.lower() in item.get("type", "").lower():
            return item
    return None


def check(items, pattern, desc, min_amount, passed):
    item = find_type(items, pattern)
    if not item:
        print("  x %s: NOT FOUND (pattern: %s)" % (desc, pattern))
        passed[0] = False
        return
    amount = item.get("amount", 0)
    if amount >= min_amount:
        print("  v %s: amount=%d (>= %d)" % (desc, amount, min_amount))
    else:
        print("  x %s: amount=%d (expected >= %d)" % (desc, amount, min_amount))
        passed[0] = False


def validate(data):
    print("=" * 60)
    print("02-collections Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 集合类型 (N=1000)
    # 2.1 Map(5)
    check(items, "Map(", "Map", 1000, passed)
    # 2.2 Set(5)
    check(items, "Set(", "Set", 1000, passed)
    # 2.3 WeakMap(1)
    check(items, "WeakMap(", "WeakMap", 1000, passed)
    # 2.4 WeakSet(1)
    check(items, "WeakSet(", "WeakSet", 1000, passed)
    # 2.9 DataView
    check(items, "(DataView)", "DataView", 1000, passed)
    # 2.8 ArrayBuffer
    check(items, "ArrayBuffer", "ArrayBuffer", 1000, passed)
    # 2.7 Array of objects -> {idx, val}
    check(items, "Object: idx, val", "Array element {idx,val}", 1000, passed)
    # 2.1 Map value -> {value}
    check(items, "Object: value", "Map value {value}", 1000, passed)

    print("\n" + "=" * 60)
    if passed[0]:
        print("All validations passed!")
    else:
        print("FAILED: some validations did not pass")
    print("=" * 60)
    return passed[0]


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        result = validate(json.load(f))
    sys.exit(0 if result else 1)

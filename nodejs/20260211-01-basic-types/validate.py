#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01-basic-types 验证脚本

验证 test.js 中创建的基础 JavaScript 类型：
  - 1000 个 Object {id, name, value, nested}
  - 1000 个 nested Object {x, y, z}
  - 1000 个 deep nested Object {deep}
  - 1000 个 Symbol holder {sym}
  - 1000 个 BigInt holder {big}
  - 1000 个 Closure object {closureId, data, payload}
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
    print("01-basic-types Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 中创建的对象类型 (每种 N=1000)
    # 1.1 普通对象 {id, name, value, nested}
    check(items, "Object: id, name", "Object {id,name,value,nested}", 1000, passed)
    # 1.1 嵌套对象 {x, y, z}
    check(items, "Object: x, y, z", "Nested {x,y,z}", 1000, passed)
    # 1.1 深层嵌套 {deep}
    check(items, "Object: deep", "Deep nested {deep}", 1000, passed)
    # 1.8 Symbol holder {sym}
    check(items, "Object: sym", "Symbol holder {sym}", 1000, passed)
    # 1.9 BigInt holder {big}
    check(items, "Object: big", "BigInt holder {big}", 1000, passed)
    # 1.10 闭包对象 {closureId, data, payload}
    check(items, "Object: closureId", "Closure {closureId,data,payload}", 1000, passed)

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

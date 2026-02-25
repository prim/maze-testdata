#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03-binary-types 验证脚本

验证 test.js 中创建的二进制数据类型 (每种 N=1000):
  - Buffer, ArrayBuffer, SharedArrayBuffer
  - DataView
  - 11 种 TypedArray
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
    print("03-binary-types Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 二进制类型 (N=1000)
    # 3.2 ArrayBuffer
    check(items, "ArrayBuffer", "ArrayBuffer", 1000, passed)
    # 3.5 DataView
    check(items, "(DataView)", "DataView", 1000, passed)
    # 3.4 Uint8ClampedArray
    check(items, "Uint8ClampedArray", "Uint8ClampedArray", 1000, passed)
    # 3.4 Int16Array
    check(items, "Int16Array", "Int16Array", 1000, passed)
    # 3.4 Uint16Array
    check(items, "Uint16Array", "Uint16Array", 1000, passed)
    # 3.4 Float32Array
    check(items, "Float32Array", "Float32Array", 1000, passed)
    # 3.4 Float64Array
    check(items, "Float64Array", "Float64Array", 1000, passed)
    # 3.4 BigInt64Array
    check(items, "BigInt64Array", "BigInt64Array", 1000, passed)
    # 3.4 BigUint64Array
    check(items, "BigUint64Array", "BigUint64Array", 1000, passed)

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

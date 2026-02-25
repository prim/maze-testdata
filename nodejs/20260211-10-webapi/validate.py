#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10-webapi 验证脚本

验证 test.js 中创建的 Web API 兼容对象:
  - TextEncoder        x1000
  - TextDecoder        x1000
  - AbortController    x1000
  - Blob               x1000
  - Headers            x1000
  - Response           x1000
  - Request            x1000
  - FormData           x1000
  - ReadableStream     x1000
  - WritableStream     x1000

注意: 多数 Web API 对象是 C++ 后端实现，Maze 可能无法直接识别。
本脚本检查可识别的关联对象。
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
    print("10-webapi Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 10.5: Headers -> _HeadersList x1000 (each has 3 name/value pairs)
    check(items, "_HeadersList", "Headers (_HeadersList)", 1000, passed)
    # test.js 10.7: Request -> URLContext x1000
    check(items, "URLContext", "Request (URLContext)", 1000, passed)

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

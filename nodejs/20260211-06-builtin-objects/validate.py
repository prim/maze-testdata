#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06-builtin-objects 验证脚本

验证 test.js 中创建的内置对象类型:
  - Date              x1000
  - RegExp            x1000
  - Error             x1000
  - TypeError         x1000
  - RangeError        x1000
  - Promise.pending   x1000
  - Promise.resolved  x1000
  - Promise.rejected  x1000
  - Proxy             x1000
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
    print("06-builtin-objects Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 6.1: Date x1000
    check(items, "(Date)", "Date", 1000, passed)
    # test.js 6.2: RegExp x1000
    check(items, "(RegExp)", "RegExp", 1000, passed)
    # test.js 6.3: Error x1000
    check(items, "Error", "Error", 1000, passed)
    # test.js 6.4: TypeError x1000
    check(items, "TypeError", "TypeError", 1000, passed)
    # test.js 6.5: RangeError x1000
    check(items, "RangeError", "RangeError", 1000, passed)
    # test.js 6.6-6.8: Promise (pending+resolved+rejected) x3000
    check(items, "Promise", "Promise (all states)", 3000, passed)

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

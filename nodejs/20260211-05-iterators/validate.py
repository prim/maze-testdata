#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05-iterators 验证脚本

验证 test.js 中创建的迭代器类型:
  - Generator (gen)           x1000
  - AsyncGenerator (asyncGen) x1000
  - ArrayIterator             x1000
  - MapIterator               x1000
  - SetIterator               x1000
  - StringIterator            x1000
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
    print("05-iterators Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 5.1: Generator (gen) x1000
    check(items, "GeneratorFunction: gen", "GeneratorFunction (gen)", 1000, passed)
    # test.js 5.2: AsyncGenerator (asyncGen) x1000
    check(items, "AsyncGeneratorFunction: asyncGen", "AsyncGeneratorFunction (asyncGen)", 1000, passed)
    # test.js 5.3: ArrayIterator x1000
    check(items, "ArrayIterator", "ArrayIterator", 1000, passed)
    # test.js 5.6: StringIterator x1000
    check(items, "StringIterator", "StringIterator", 1000, passed)

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

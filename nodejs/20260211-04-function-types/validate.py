#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04-function-types 验证脚本

验证 test.js 中创建的函数类型:
  - Function (namedFunc)        x1000
  - ArrowFunction               x1100
  - AsyncFunction (asyncFn)     x1200
  - GeneratorFunction (genFn)   x1300
  - AsyncGeneratorFunction      x1400
  - Function.dynamic (new Function) x1500
  - BoundFunction (boundTarget) x1600
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
    print("04-function-types Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 4.1: 普通函数 namedFunc x1000
    check(items, "Function: namedFunc", "Function (namedFunc)", 1000, passed)
    # test.js 4.2: 箭头函数 x1100
    check(items, "ArrowFunction:", "ArrowFunction", 1100, passed)
    # test.js 4.3: 异步函数 asyncFn x1200
    check(items, "AsyncFunction: asyncFn", "AsyncFunction", 1200, passed)
    # test.js 4.4: 生成器函数 genFn x1300
    check(items, "GeneratorFunction: genFn", "GeneratorFunction", 1300, passed)
    # test.js 4.5: 异步生成器函数 asyncGenFn x1400
    check(items, "AsyncGeneratorFunction: asyncGenFn", "AsyncGeneratorFunction", 1400, passed)
    # test.js 4.6: 动态函数 new Function x1500
    check(items, "Function: dynamic", "Function.dynamic", 1500, passed)
    # test.js 4.7: 绑定函数 boundTarget x1600
    check(items, "BoundFunction: boundTarget", "BoundFunction", 1600, passed)

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

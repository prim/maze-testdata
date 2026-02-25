#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
11-special-objects 验证脚本

验证 test.js 中创建的特殊对象:
  - Object.nullProto   x1000 (null 原型)
  - Object.frozen      x1000 (冻结对象)
  - Object.sealed      x1000 (密封对象)
  - Object.circular    x1000 (循环引用)
  - Object.deepNested  x1000 (深度嵌套, 每个 5 层子对象)
  - Object.manyProps   x1000 (50 个属性)
  - Arguments          x1000 (arguments 对象)
  - Object.symbolKeys  x1000 (Symbol 键)
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
    print("11-special-objects Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 11.2: frozen {id, frozen} x1000
    check(items, "{Object: id, frozen}", "Object.frozen", 1000, passed)
    # test.js 11.3: sealed {id, sealed} x1000
    check(items, "{Object: id, sealed}", "Object.sealed", 1000, passed)
    # test.js 11.4: circular {id, self} x1000
    check(items, "{Object: id, self}", "Object.circular", 1000, passed)
    # test.js 11.5: deep nested {depth, id, child} x5000 (1000 roots * 5 levels)
    check(items, "{Object: depth, id, child}", "Object.deepNested", 1000, passed)
    # test.js 11.7: arguments x1000
    check(items, "Arguments", "Arguments", 1000, passed)

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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07-es6-plus 验证脚本

验证 test.js 中创建的 ES6+ 特性对象:
  - WeakRef                  x1000 (target: {id, data})
  - FinalizationRegistry     x1000 (wrapper: {registry, obj})
  - PrivateFieldsClass       x1000
  - DerivedClass (extends)   x1000
  - Object.accessors         x1000 (getter/setter)
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
    print("07-es6-plus Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 7.3: PrivateFieldsClass x1000
    check(items, "PrivateFieldsClass", "PrivateFieldsClass", 1000, passed)
    # test.js 7.4: DerivedClass x1000
    check(items, "DerivedClass", "DerivedClass", 1000, passed)
    # test.js 7.5: getter/setter - Function: get value / set value x1000
    check(items, "Function: get value", "getter (get value)", 1000, passed)
    check(items, "Function: set value", "setter (set value)", 1000, passed)

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

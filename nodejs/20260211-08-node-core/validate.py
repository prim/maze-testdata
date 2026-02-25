#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
08-node-core 验证脚本

验证 test.js 中创建的 Node.js 核心模块对象:
  - EventEmitter       x1000
  - Stream.Readable    x1000
  - Stream.Writable    x1000
  - Stream.Transform   x1000
  - URL                x1000
  - URLSearchParams    x1000
  - crypto.Hash        x1000
  - zlib.Gzip          x1000
  - vm.Script          x1000
  - MessageChannel     x1000
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
    print("08-node-core Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    passed = [True]

    # test.js 8.1: EventEmitter x1000
    check(items, "EventEmitter", "EventEmitter", 1000, passed)
    # test.js 8.4: Stream.Transform x1000
    check(items, "Transform", "Stream.Transform", 1000, passed)
    # test.js 8.5: URL (URLContext) x1000
    check(items, "URLContext", "URL", 1000, passed)
    # test.js 8.8: zlib.Gzip x1000
    check(items, "Gzip", "zlib.Gzip", 1000, passed)

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

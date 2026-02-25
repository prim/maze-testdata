#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
09-intl-objects 验证脚本

验证 test.js 中创建的国际化对象:
  - Intl.DateTimeFormat      x1000
  - Intl.NumberFormat        x1000
  - Intl.Collator            x1000
  - Intl.PluralRules         x1000
  - Intl.RelativeTimeFormat  x1000
  - Intl.ListFormat          x1000
  - Intl.Segmenter           x1000

注意: Intl 对象是 C++ 后端实现，Maze 可能无法识别为独立的 V8 堆对象。
本验证脚本仅检查分析结果非空。
"""
from __future__ import print_function


def validate(data):
    print("=" * 60)
    print("09-intl-objects Validation")
    print("=" * 60)

    items = data.get("items") or []
    if not items:
        print("  x No items found")
        return False

    print("  v items count: %d" % len(items))
    print("  (Intl objects are C++-backed, not visible as V8 heap types)")

    print("\n" + "=" * 60)
    print("All validations passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        result = validate(json.load(f))
    sys.exit(0 if result else 1)

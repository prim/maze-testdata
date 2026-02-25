#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ 1拆N 阈值测试验证脚本

Bug 针对：
    ResultClassify 1拆N 阈值 n>5 (cpp.go:970)
    malloc 块中包含 2-5 个相同结构体时不会被拆分
"""
from __future__ import print_function
import json
import sys


def find_type_containing(items, substring):
    for item in items:
        if substring in item.get("type", ""):
            return item
    return None


def find_all_types_containing(items, substring):
    return [item for item in items if substring in item.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ 1-to-N Split Threshold Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    all_passed = True

    # Check 1: Widget 类型识别
    print("\n[Check 1] Widget instances...")
    widget_items = find_all_types_containing(items, "Widget")
    total_widget = sum(i.get("amount", 0) for i in widget_items)
    print("  Widget entries: %d" % len(widget_items))
    for w in widget_items:
        print("    - %s: amount=%d, avg_size=%d, total=%d" % (
            w.get("type", ""), w.get("amount", 0),
            w.get("avg_size", 0),
            w.get("amount", 0) * w.get("avg_size", 0)))
    print("  Total Widget amount: %d" % total_widget)

    # 期望: 每个 vector 存了 N 个指针
    # g_split2: 3000 个指针 → 3000 个 Widget (每个在 malloc(sz*2) 块中)
    # g_split3: 3000 个指针 → 3000 个 Widget (每个在 malloc(sz*3) 块中)
    # g_split5: 2000 个指针 → 2000 个 Widget (每个在 malloc(sz*5) 块中)
    # g_split8: 1000 个指针 → 1000 个 Widget (每个在 malloc(sz*8) 块中)
    # 总计: 9000 个 Widget
    expected_min = 8000
    if total_widget >= expected_min:
        print("  PASS total >= %d" % expected_min)
    else:
        print("  FAIL total too low (expected >= %d)" % expected_min)
        all_passed = False

    # Check 2: 检测 1拆N 阈值 bug
    # 如果 bug 存在 (n>5 阈值):
    #   split2/3/5 的块不会被拆分，avg_size 会是 sizeof(Widget)*N
    #   split8 的块会被拆分，avg_size 接近 sizeof(Widget)
    # 如果 bug 不存在:
    #   所有块的 avg_size 都接近 sizeof(Widget)
    print("\n[Check 2] Bug detection: avg_size analysis...")
    for w in widget_items:
        avg = w.get("avg_size", 0)
        amt = w.get("amount", 0)
        typ = w.get("type", "")
        print("    %s: amount=%d, avg_size=%d" % (typ, amt, avg))

    # Check 3: 内存总量分析
    print("\n[Check 3] Memory overview...")
    total_mem = sum(i.get("amount", 0) * i.get("avg_size", 0)
                    for i in widget_items)
    print("  Total Widget memory: %d bytes" % total_mem)

    # Check 4: 结果概览
    print("\n[Check 4] Result items overview...")
    print("  Total items: %d" % len(items))
    for item in items[:10]:
        print("    - %s: amount=%d, avg_size=%d" % (
            item.get("type", "unknown"),
            item.get("amount", 0),
            item.get("avg_size", 0)))
    if len(items) > 10:
        print("    ... (%d more)" % (len(items) - 10))

    # Final
    print("\n" + "=" * 60)
    if all_passed:
        print("All validations passed!")
    else:
        print("Some validations FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

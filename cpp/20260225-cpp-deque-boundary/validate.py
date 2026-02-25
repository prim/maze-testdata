#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Deque 边界元素测试验证脚本

Bug 针对：
    DequeClassifyInfo 边界检查失效 (custom.go:139/156)
    curNode 自增后边界比较永远为 false
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
    print("C++ Deque Boundary Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    all_passed = True

    # 200 deques * 100 push = 20000 Task objects allocated
    # 200 deques * 30 pop = 6000 popped (but still in g_all_tasks)
    # alive in deques: 200 * 70 = 14000
    # total allocated: 20000

    print("\n[Check 1] Task instances...")
    task_items = find_all_types_containing(items, "Task")
    total_task = sum(i.get("amount", 0) for i in task_items)
    print("  Task entries: %d" % len(task_items))
    for t in task_items:
        print("    - %s: amount=%d, avg_size=%d" % (
            t.get("type", ""), t.get("amount", 0),
            t.get("avg_size", 0)))
    print("  Total Task amount: %d (expected: ~20000)" % total_task)

    if total_task >= 18000:
        print("  PASS total >= 18000")
    else:
        print("  FAIL total too low")
        all_passed = False

    # Check 2: 结果概览
    print("\n[Check 2] Result items overview...")
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node.js Basic Objects 测试验证脚本

验证目标：
    1. 验证 Maze 能识别 test.js 中创建的各种 Node.js/V8 对象类型
    2. 检查对象数量是否符合预期

测试数据 (test.js):
    - 10,000 个 Object {id, name, value, nested}
    - 10,000 个 Object {x, y} (nested)
    - 1,000 个 Date
    - 1,000 个 RegExp
    - 1,000 个 Promise
    - 1,000 个 MyClass
    - 1,000 个 Error
    - 1,000 个 EventEmitter
    - 1,000 个 Map
    - 1,000 个 Set
    - 1,000 个 Function
    - 1,000 个 Uint8Array
    - 1,000 个 ArrayBuffer
    - 1,000 个 Buffer (backed by Uint8Array)
"""
from __future__ import print_function
import json
import sys


def find_type(items, pattern):
    """查找类型名包含指定子串的项"""
    for item in items:
        if pattern.lower() in item.get("type", "").lower():
            return item
    return None


def check_type(items, pattern, desc, expected_min, all_passed_ref):
    """检查某个类型的对象数量是否 >= expected_min"""
    item = find_type(items, pattern)
    if not item:
        print("  x %s: NOT FOUND (pattern: %s)" % (desc, pattern))
        all_passed_ref[0] = False
        return
    amount = item.get("amount", 0)
    if amount >= expected_min:
        print("  v %s: amount=%d (>= %d) type=%s" % (
            desc, amount, expected_min, item["type"][:60]))
    else:
        print("  x %s: amount=%d (expected >= %d) type=%s" % (
            desc, amount, expected_min, item["type"][:60]))
        all_passed_ref[0] = False


def validate(data):
    """验证 maze 分析结果"""
    print("=" * 60)
    print("Node.js Basic Objects Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data.get("items") or []
    summary = data["summary"]

    vms = summary.get("vms", 0)
    core_size = summary.get("core_size", 0)
    print("\n[Summary]")
    print("  VMS: %.2f MB" % (vms / 1024 / 1024))
    print("  Core Size: %.2f MB" % (core_size / 1024 / 1024))
    print("  Item types: %d" % len(items))

    # mutable ref for pass/fail
    all_passed = [True]

    # =========================================================
    # Check 1: 基本结构
    # =========================================================
    print("\n[Check 1] Basic structure...")
    if len(items) == 0:
        print("  x No items found")
        return False
    print("  v Found %d item types" % len(items))

    if vms < 10 * 1024 * 1024:
        print("  x VMS too small")
        all_passed[0] = False
    else:
        print("  v VMS reasonable")

    # =========================================================
    # Check 2: 验证 test.js 创建的对象类型
    # =========================================================
    print("\n[Check 2] Expected object types...")

    # (pattern, description, min_amount)
    expected_types = [
        ("Object: id, name", "Plain Object {id,name,value,nested}", 10000),
        ("Object: x, y", "Nested Object {x,y}", 10000),
        ("(Date)", "Date", 1000),
        ("(RegExp)", "RegExp", 1000),
        ("Promise", "Promise", 1000),
        ("MyClass", "MyClass", 1000),
        ("Error", "Error", 1000),
        ("EventEmitter", "EventEmitter", 1000),
        ("Map(", "Map", 1000),
        ("Set(", "Set", 1000),
        ("Function: func", "Function (func)", 1000),
        ("Uint8Array", "Uint8Array", 1000),
        ("ArrayBuffer", "ArrayBuffer", 1000),
    ]

    for pattern, desc, expected_min in expected_types:
        check_type(items, pattern, desc, expected_min, all_passed)

    # =========================================================
    # Check 3: Top 10 by size
    # =========================================================
    print("\n[Top 10 Types by Size]")
    sorted_items = sorted(items, key=lambda x: x.get("total_size", 0), reverse=True)
    for i, item in enumerate(sorted_items[:10]):
        print("  %2d. %-50s amount=%5d size=%.1f KB" % (
            i + 1,
            item.get("type", "?")[:50],
            item.get("amount", 0),
            item.get("total_size", 0) / 1024.0,
        ))

    # 最终结果
    print("\n" + "=" * 60)
    if all_passed[0]:
        print("All validations passed!")
    else:
        print("FAILED: some validations did not pass")
    print("=" * 60)
    return all_passed[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

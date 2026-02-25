#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ STL Containers 测试验证脚本

验证目标：
    1. 验证 Maze 能识别 Widget / Session / TaskQueue 三种类型
    2. 验证各类型的 amount 接近预期值
    3. 验证容器内部内存被追踪（weak malloc 比例不过高）

测试数据：
    - 5000 个 Widget (vector<int*> + string)
    - 2000 个 Session (unordered_map<int,string>)
    - 1000 个 TaskQueue (deque<int*> + list<int*>)
"""
from __future__ import print_function
import json
import sys


def find_type_containing(items, substring):
    """查找类型名包含指定子串的项"""
    for item in items:
        if substring in item.get("type", ""):
            return item
    return None


def validate(data):
    print("=" * 60)
    print("C++ Containers Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    summary = data["summary"]
    all_passed = True

    # Check 1: Widget
    print("\n[Check 1] Widget instances...")
    widget = find_type_containing(items, "Widget")
    if widget:
        amount = widget.get("amount", 0)
        avg_size = widget.get("avg_size", 0)
        print("  Found: %s" % widget.get("type", ""))
        print("  amount: %d (expected: ~5000)" % amount)
        print("  avg_size: %d" % avg_size)
        if amount >= 4500:
            print("  PASS amount >= 4500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Widget not found in results")
        all_passed = False

    # Check 2: Session
    print("\n[Check 2] Session instances...")
    session = find_type_containing(items, "Session")
    if session:
        amount = session.get("amount", 0)
        avg_size = session.get("avg_size", 0)
        print("  Found: %s" % session.get("type", ""))
        print("  amount: %d (expected: ~2000)" % amount)
        print("  avg_size: %d" % avg_size)
        if amount >= 1800:
            print("  PASS amount >= 1800")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Session not found in results")
        all_passed = False

    # Check 3: TaskQueue
    print("\n[Check 3] TaskQueue instances...")
    tq = find_type_containing(items, "TaskQueue")
    if tq:
        amount = tq.get("amount", 0)
        avg_size = tq.get("avg_size", 0)
        print("  Found: %s" % tq.get("type", ""))
        print("  amount: %d (expected: ~1000)" % amount)
        print("  avg_size: %d" % avg_size)
        if amount >= 900:
            print("  PASS amount >= 900")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL TaskQueue not found in results")
        all_passed = False

    # Check 4: weak malloc 比例
    print("\n[Check 4] Weak malloc ratio...")
    total_known = 0
    total_weak = 0
    for item in items:
        t = item.get("type", "")
        total_size = item.get("total_size", 0)
        if "(weak)" in t:
            total_weak += total_size
        else:
            total_known += total_size

    total_all = total_known + total_weak
    if total_all > 0:
        weak_pct = 100.0 * total_weak / total_all
        print("  Known: %d bytes" % total_known)
        print("  Weak:  %d bytes (%.1f%%)" % (total_weak, weak_pct))
        # 容器内部内存应该大部分被追踪到，weak 不应超过 80%
        if weak_pct < 80:
            print("  PASS weak ratio < 80%%")
        else:
            print("  WARN weak ratio >= 80%% (container tracking may be incomplete)")
    else:
        print("  SKIP no size data")

    # Check 5: 类型区分
    print("\n[Check 5] Type differentiation...")
    found_types = set()
    for item in items:
        t = item.get("type", "")
        for name in ["Widget", "Session", "TaskQueue"]:
            if name in t:
                found_types.add(name)
    print("  Distinct types found: %s" % sorted(found_types))
    if len(found_types) >= 3:
        print("  PASS all 3 types distinguished")
    else:
        print("  FAIL expected 3 distinct types, got %d" % len(found_types))
        all_passed = False

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

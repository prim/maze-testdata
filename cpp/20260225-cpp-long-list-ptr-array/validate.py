#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Long List & Pointer Array 测试验证脚本

验证目标：
    1. 超长 std::list (500K节点) 能被正确处理，Task 类型被识别
    2. EventDispatcher 的指针数组 (Listener*[8]) 不导致 DFS 异常
    3. Particle 的结构体数组 (Vec3[4]) 被正常处理
    4. 分析过程不超时、不崩溃（隐式验证）

Bug 针对：
    - ListClassifyInfo 循环上限 1M vs 错误检查 10M 不匹配
    - ArrayClassifyInfo 指针数组 skip 代码被注释掉
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
    print("C++ Long List & Pointer Array Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    summary = data["summary"]
    all_passed = True

    # Check 1: Task 类型识别（list 中的元素，有 vtable）
    print("\n[Check 1] Task instances (from std::list)...")
    task = find_type_containing(items, "Task")
    if task:
        amount = task.get("amount", 0)
        print("  Found: %s" % task.get("type", ""))
        print("  amount: %d (expected: ~500000)" % amount)
        # 500K 个 Task，但 ListClassifyInfo 循环上限 1M，应该全部处理
        if amount >= 400000:
            print("  PASS amount >= 400000")
        else:
            print("  FAIL amount too low (ListClassifyInfo may have truncated)")
            all_passed = False
    else:
        print("  FAIL Task not found in results")
        all_passed = False

    # Check 2: Listener 类型识别（通过指针数组持有）
    print("\n[Check 2] Listener instances (from pointer arrays)...")
    listener = find_type_containing(items, "Listener")
    if listener:
        amount = listener.get("amount", 0)
        print("  Found: %s" % listener.get("type", ""))
        print("  amount: %d (expected: ~13500)" % amount)
        # 3000 dispatchers * avg 4.5 listeners = ~13500
        if amount >= 10000:
            print("  PASS amount >= 10000")
        else:
            print("  WARN amount lower than expected (ArrayClassifyInfo may skip ptr arrays)")
    else:
        print("  INFO Listener not found (may be absorbed into EventDispatcher)")

    # Check 3: EventDispatcher 类型识别
    print("\n[Check 3] EventDispatcher instances...")
    dispatcher = find_type_containing(items, "EventDispatcher")
    if dispatcher:
        amount = dispatcher.get("amount", 0)
        print("  Found: %s" % dispatcher.get("type", ""))
        print("  amount: %d (expected: ~3000)" % amount)
        if amount >= 2500:
            print("  PASS amount >= 2500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL EventDispatcher not found in results")
        all_passed = False

    # Check 4: Particle 类型识别（含 Vec3[4] 结构体数组）
    print("\n[Check 4] Particle instances (with struct arrays)...")
    particle = find_type_containing(items, "Particle")
    if particle:
        amount = particle.get("amount", 0)
        print("  Found: %s" % particle.get("type", ""))
        print("  amount: %d (expected: ~5000)" % amount)
        if amount >= 4000:
            print("  PASS amount >= 4000")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Particle not found in results")
        all_passed = False

    # Check 5: 总体结果条目
    print("\n[Check 5] Result items overview...")
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

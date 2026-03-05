#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py — forward_list, queue, stack 容器测试验证

测试目标：验证 Maze 对未专门支持的 STL 容器中对象的识别能力。
- Task: 3000 个，存在 forward_list + vector 中
- Message: 4000 个，存在 queue + vector 中
- Event: 5000 个，存在 stack + vector 中

这些容器没有专门的 TYPE_CODE，对象通过 vtable 和 vector 引用识别。
"""
from __future__ import print_function


def find_type_containing(items, substring):
    """在 items 中查找 type 包含 substring 的条目"""
    for item in items:
        if substring in item.get("type", ""):
            return item
    return None


def validate(data):
    items = data.get("items", [])
    print("Total items: %d" % len(items))

    passed = True

    # Check 1: Task objects (3000 expected)
    print("\n[Check 1] Task objects (expected ~3000)...")
    task = find_type_containing(items, "Task")
    if task:
        amount = task.get("amount", 0)
        print("  Found Task: amount=%d, avg_size=%d" % (
            amount, task.get("avg_size", 0)))
        if amount >= 2700:
            print("  OK: Task count >= 2700")
        else:
            print("  FAIL: Task count %d < 2700" % amount)
            passed = False
    else:
        print("  FAIL: Task type not found")
        passed = False

    # Check 2: Message objects (4000 expected)
    print("\n[Check 2] Message objects (expected ~4000)...")
    msg = find_type_containing(items, "Message")
    if msg:
        amount = msg.get("amount", 0)
        print("  Found Message: amount=%d, avg_size=%d" % (
            amount, msg.get("avg_size", 0)))
        if amount >= 3600:
            print("  OK: Message count >= 3600")
        else:
            print("  FAIL: Message count %d < 3600" % amount)
            passed = False
    else:
        print("  FAIL: Message type not found")
        passed = False

    # Check 3: Event objects (5000 expected)
    print("\n[Check 3] Event objects (expected ~5000)...")
    event = find_type_containing(items, "Event")
    if event:
        amount = event.get("amount", 0)
        print("  Found Event: amount=%d, avg_size=%d" % (
            amount, event.get("avg_size", 0)))
        if amount >= 4500:
            print("  OK: Event count >= 4500")
        else:
            print("  FAIL: Event count %d < 4500" % amount)
            passed = False
    else:
        print("  FAIL: Event type not found")
        passed = False

    if passed:
        print("\nAll checks passed!")
    return passed

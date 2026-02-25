#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ shared_ptr / unique_ptr 智能指针测试验证脚本

测试目标：
    验证 Maze 能否通过 StructClassifyInfo + PtrClassifyInfo
    正确追踪智能指针指向的对象。
"""
from __future__ import print_function
import json
import sys


def find_all(items, sub):
    return [i for i in items if sub in i.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ Smart Pointer Test Validation")
    print("=" * 60)

    assert "items" in data and "summary" in data
    items = data["items"]
    ok = True

    # Check 1: Player (3000 via shared_ptr)
    print("\n[Check 1] Player (shared_ptr)...")
    total = sum(i.get("amount", 0) for i in find_all(items, "Player"))
    print("  Total: %d (expected ~3000)" % total)
    if total >= 2700:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Check 2: Bullet (5000 via unique_ptr)
    print("\n[Check 2] Bullet (unique_ptr)...")
    total = sum(i.get("amount", 0) for i in find_all(items, "Bullet"))
    print("  Total: %d (expected ~5000)" % total)
    if total >= 4500:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Check 3: Effect (4000 via shared_ptr)
    print("\n[Check 3] Effect (shared_ptr)...")
    total = sum(i.get("amount", 0) for i in find_all(items, "Effect"))
    print("  Total: %d (expected ~4000)" % total)
    if total >= 3600:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Overview
    print("\n[Check 4] Overview...")
    print("  Total items: %d" % len(items))
    for item in items[:15]:
        print("    - %s: amount=%d, avg_size=%d" % (
            item.get("type", "?"), item.get("amount", 0),
            item.get("avg_size", 0)))
    if len(items) > 15:
        print("    ... (%d more)" % (len(items) - 15))

    print("\n" + "=" * 60)
    print("All passed!" if ok else "Some FAILED")
    print("=" * 60)
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    sys.exit(0 if validate(data) else 1)

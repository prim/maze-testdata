#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ 多重继承 vtable 测试验证脚本

测试目标：
    验证 Maze 对多重继承对象的类型识别能力。
    多重继承对象有多个 vtable（主 vtable + 次级 vtable），
    cpp package 只检测 offset 0 的主 vtable。
"""
from __future__ import print_function
import json
import sys


def find_all(items, sub):
    return [i for i in items if sub in i.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ Multi-Inherit Test Validation")
    print("=" * 60)

    assert "items" in data and "summary" in data
    items = data["items"]
    ok = True

    # Check 1: GameObject (4000, dual inherit)
    print("\n[Check 1] GameObject (dual inherit)...")
    matches = find_all(items, "GameObject")
    total = sum(i.get("amount", 0) for i in matches)
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total: %d (expected ~4000)" % total)
    if total >= 3600:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Check 2: NetworkEntity (3000, triple inherit)
    print("\n[Check 2] NetworkEntity (triple inherit)...")
    matches = find_all(items, "NetworkEntity")
    total = sum(i.get("amount", 0) for i in matches)
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total: %d (expected ~3000)" % total)
    if total >= 2700:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Check 3: SimpleNPC (5000, single inherit control)
    print("\n[Check 3] SimpleNPC (single inherit)...")
    matches = find_all(items, "SimpleNPC")
    total = sum(i.get("amount", 0) for i in matches)
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total: %d (expected ~5000)" % total)
    if total >= 4500:
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

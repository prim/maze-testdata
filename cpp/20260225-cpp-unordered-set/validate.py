#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ std::unordered_set / unordered_map 测试验证脚本

测试目标：
    验证 Maze 对 unordered_set/map 中元素的识别。
    unordered_map 有 TYPE_CODE_CUSTOM_UNORDERED_MAP (1002)，
    unordered_set 没有专门的 TYPE_CODE。
"""
from __future__ import print_function
import json
import sys


def find_all(items, sub):
    return [i for i in items if sub in i.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ Unordered Set/Map Test Validation")
    print("=" * 60)

    assert "items" in data and "summary" in data
    items = data["items"]
    ok = True

    # Check 1: Enemy (4000 via unordered_set + vector)
    print("\n[Check 1] Enemy instances...")
    matches = find_all(items, "Enemy")
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

    # Check 2: Item (3000 via unordered_map + vector)
    print("\n[Check 2] Item instances...")
    matches = find_all(items, "Item")
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

    # Check 3: Hash node info
    print("\n[Check 3] Hash node info...")
    hash_matches = find_all(items, "Hash_node")
    for m in hash_matches:
        t = m.get("type", "")
        if len(t) > 60:
            t = t[:57] + "..."
        print("    - %s: amount=%d, avg_size=%d" % (
            t, m.get("amount", 0), m.get("avg_size", 0)))

    # Overview
    print("\n[Check 4] Overview...")
    print("  Total items: %d" % len(items))
    for item in items[:15]:
        t = item.get("type", "?")
        if len(t) > 60:
            t = t[:57] + "..."
        print("    - %s: amount=%d, avg_size=%d" % (
            t, item.get("amount", 0),
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ std::map / std::set 红黑树测试验证脚本

测试目标：
    验证 Maze 对 std::map/set 中元素的识别能力。
    cpp package 没有注册 map/set 的 TYPE_CODE，
    红黑树节点通过通用 StructClassifyInfo + PtrClassifyInfo 追踪。
"""
from __future__ import print_function
import json
import sys


def find_all_types_containing(items, substring):
    return [item for item in items if substring in item.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ Map/Set Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    all_passed = True

    # Check 1: Monster (5000 via map + vector)
    print("\n[Check 1] Monster instances...")
    monster_items = find_all_types_containing(items, "Monster")
    total_monster = sum(i.get("amount", 0) for i in monster_items)
    for m in monster_items:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total: %d (expected ~5000)" % total_monster)
    if total_monster >= 4500:
        print("  PASS")
    else:
        print("  FAIL total too low")
        all_passed = False

    # Check 2: Weapon (3000 via set + vector)
    print("\n[Check 2] Weapon instances...")
    weapon_items = find_all_types_containing(items, "Weapon")
    total_weapon = sum(i.get("amount", 0) for i in weapon_items)
    for w in weapon_items:
        print("    - %s: amount=%d, avg_size=%d" % (
            w.get("type", ""), w.get("amount", 0),
            w.get("avg_size", 0)))
    print("  Total: %d (expected ~3000)" % total_weapon)
    if total_weapon >= 2700:
        print("  PASS")
    else:
        print("  FAIL total too low")
        all_passed = False

    # Check 3: overview
    print("\n[Check 3] Result overview...")
    print("  Total items: %d" % len(items))
    for item in items[:15]:
        print("    - %s: amount=%d, avg_size=%d" % (
            item.get("type", "unknown"),
            item.get("amount", 0),
            item.get("avg_size", 0)))
    if len(items) > 15:
        print("    ... (%d more)" % (len(items) - 15))

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
    sys.exit(0 if validate(data) else 1)

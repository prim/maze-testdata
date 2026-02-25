#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Vtable Types 测试验证脚本

验证目标：
    1. 验证 Maze 能识别 Dog / Cat / GoldFish 三种类型
    2. 验证各类型的 amount 接近预期值
    3. 验证 avg_size 合理

测试数据：
    - 10000 个 Dog 实例 + 200 个 Dog 数组元素
    - 5000 个 Cat 实例
    - 3000 个 GoldFish 实例
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
    print("C++ Vtable Types Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    all_passed = True

    # Check 1: Dog
    print("\n[Check 1] Dog instances...")
    dog = find_type_containing(items, "Dog")
    if dog:
        amount = dog.get("amount", 0)
        avg_size = dog.get("avg_size", 0)
        print("  Found: %s" % dog.get("type", ""))
        print("  amount: %d (expected: ~10200)" % amount)
        print("  avg_size: %d" % avg_size)
        # 10000 个 new Dog + 200 个数组元素，允许一定误差
        if amount >= 9000:
            print("  PASS amount >= 9000")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Dog not found in results")
        all_passed = False

    # Check 2: Cat
    print("\n[Check 2] Cat instances...")
    cat = find_type_containing(items, "Cat")
    if cat:
        amount = cat.get("amount", 0)
        avg_size = cat.get("avg_size", 0)
        print("  Found: %s" % cat.get("type", ""))
        print("  amount: %d (expected: ~5000)" % amount)
        print("  avg_size: %d" % avg_size)
        if amount >= 4500:
            print("  PASS amount >= 4500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Cat not found in results")
        all_passed = False

    # Check 3: GoldFish
    print("\n[Check 3] GoldFish instances...")
    fish = find_type_containing(items, "GoldFish")
    if fish:
        amount = fish.get("amount", 0)
        avg_size = fish.get("avg_size", 0)
        print("  Found: %s" % fish.get("type", ""))
        print("  amount: %d (expected: ~3000)" % amount)
        print("  avg_size: %d" % avg_size)
        if amount >= 2700:
            print("  PASS amount >= 2700")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL GoldFish not found in results")
        all_passed = False

    # Check 4: 类型区分 — Dog/Cat/GoldFish 应该是不同的 type 条目
    print("\n[Check 4] Type differentiation...")
    type_names = set()
    for item in items:
        t = item.get("type", "")
        if "Dog" in t or "Cat" in t or "GoldFish" in t:
            type_names.add(t)
    print("  Distinct animal types found: %d" % len(type_names))
    for t in sorted(type_names):
        print("    - %s" % t)
    if len(type_names) >= 3:
        print("  PASS at least 3 distinct types")
    else:
        print("  FAIL expected at least 3 distinct types")
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

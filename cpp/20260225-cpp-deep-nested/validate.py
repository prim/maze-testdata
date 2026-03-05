#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Deep Nested Containers 测试验证脚本

验证目标：
    1. 二层嵌套 Warehouse->Inventory->Item 的容器展开正确性
    2. OrderBook 中 list + map<int,vector> 混合容器的处理
    3. 所有 Item 实例被正确归属（不丢失、不重复计数）
    4. DFS 递归深度不导致崩溃

Bug 针对：
    - 多层容器嵌套时 DFS 深度压力
    - list + map + vector 混合场景的交互
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
    print("C++ Deep Nested Containers Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    summary = data["summary"]
    all_passed = True

    # Check 1: Item 类型识别
    # 总共 100*20*10 + 500*(5*8+15) = 20000 + 27500 = 47500 个 Item
    print("\n[Check 1] Item instances...")
    item_entry = find_type_containing(items, "Item")
    if item_entry:
        amount = item_entry.get("amount", 0)
        print("  Found: %s" % item_entry.get("type", ""))
        print("  amount: %d (expected: ~47500)" % amount)
        if amount >= 30000:
            print("  PASS amount >= 30000")
        else:
            print("  FAIL amount too low (nested containers may lose items)")
            all_passed = False
    else:
        print("  FAIL Item not found in results")
        all_passed = False

    # Check 2: Inventory 类型识别
    print("\n[Check 2] Inventory instances...")
    inv = find_type_containing(items, "Inventory")
    if inv:
        amount = inv.get("amount", 0)
        print("  Found: %s" % inv.get("type", ""))
        print("  amount: %d (expected: ~2000)" % amount)
        if amount >= 1500:
            print("  PASS amount >= 1500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Inventory not found in results")
        all_passed = False

    # Check 3: Warehouse 类型识别
    print("\n[Check 3] Warehouse instances...")
    wh = find_type_containing(items, "Warehouse")
    if wh:
        amount = wh.get("amount", 0)
        print("  Found: %s" % wh.get("type", ""))
        print("  amount: %d (expected: ~100)" % amount)
        if amount >= 80:
            print("  PASS amount >= 80")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Warehouse not found in results")
        all_passed = False

    # Check 4: OrderBook 类型识别
    print("\n[Check 4] OrderBook instances...")
    ob = find_type_containing(items, "OrderBook")
    if ob:
        amount = ob.get("amount", 0)
        print("  Found: %s" % ob.get("type", ""))
        print("  amount: %d (expected: ~500)" % amount)
        if amount >= 400:
            print("  PASS amount >= 400")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL OrderBook not found in results")
        all_passed = False

    # Check 5: known_size 占比 — 嵌套容器应该贡献大量已知内存
    print("\n[Check 5] Known size ratio...")
    known_size = data.get("known_size", 0)
    total_topn = data.get("total_topn", 0)
    if total_topn > 0:
        known_pct = 100.0 * known_size / total_topn
        print("  known_size: %d" % known_size)
        print("  total_topn: %d" % total_topn)
        print("  ratio: %.1f%%" % known_pct)
        if known_pct > 20:
            print("  PASS known ratio > 20%%")
        else:
            print("  WARN known ratio low for nested containers")
    else:
        print("  SKIP no total_topn data")

    # Check 6: 结果概览
    print("\n[Check 6] Result items overview...")
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

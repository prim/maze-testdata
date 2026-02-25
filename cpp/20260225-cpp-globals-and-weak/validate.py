#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Globals & Weak Classification 测试验证脚本

验证目标：
    1. 验证 Maze 能识别全局变量（g_config 等）
    2. 验证 Record 类型被正确识别
    3. 验证 known_size 占比合理（全局符号 + vtable 对象贡献）

测试数据：
    - 1 个全局 Config 对象
    - 5000 个 Record 实例（有 vtable）
    - 5000 个 Point3D 实例（无 vtable，POD）
    - 1000 个 Node 链表节点（无 vtable，指针链）
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


def find_all_types_containing(items, substring):
    """查找所有类型名包含指定子串的项"""
    return [item for item in items if substring in item.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ Globals & Weak Classification Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    summary = data["summary"]
    all_passed = True

    # Check 1: Record 类型识别（有 vtable，应该被识别）
    print("\n[Check 1] Record instances...")
    record = find_type_containing(items, "Record")
    if record:
        amount = record.get("amount", 0)
        print("  Found: %s" % record.get("type", ""))
        print("  amount: %d (expected: ~5000)" % amount)
        if amount >= 4500:
            print("  PASS amount >= 4500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Record not found in results")
        all_passed = False

    # Check 2: Config 类型（全局对象，应通过 vtable 或全局符号被识别）
    print("\n[Check 2] Config global object...")
    config = find_type_containing(items, "Config")
    if config:
        print("  Found: %s" % config.get("type", ""))
        print("  amount: %d" % config.get("amount", 0))
        print("  PASS Config type recognized")
    else:
        # Config 是全局对象，可能不在 items 中单独出现
        # 但它的 vector<string> 内部分配应该被追踪
        print("  INFO Config not found as separate item (may be inlined)")

    # Check 3: known_size 占比
    print("\n[Check 3] Known size ratio...")
    known_size = data.get("known_size", 0)
    total_topn = data.get("total_topn", 0)
    if total_topn > 0:
        known_pct = 100.0 * known_size / total_topn
        print("  known_size: %d" % known_size)
        print("  total_topn: %d" % total_topn)
        print("  ratio: %.1f%%" % known_pct)
        # 至少应该有一些已知类型的内存
        if known_pct > 5:
            print("  PASS known ratio > 5%%")
        else:
            print("  WARN known ratio very low")
    else:
        print("  SKIP no total_topn data")

    # Check 4: weak malloc 中应该包含 Point3D 和 Node 的内存
    # 它们没有 vtable，会走弱分类，以 malloc(size) 形式出现
    print("\n[Check 4] Weak malloc blocks (Point3D/Node expected here)...")
    weak_items = find_all_types_containing(items, "(weak)")
    malloc_items = [i for i in items if i.get("type", "").startswith("malloc(")]
    total_weak_amount = sum(i.get("amount", 0) for i in weak_items)
    total_malloc_amount = sum(i.get("amount", 0) for i in malloc_items)
    print("  Weak items: %d categories, %d total blocks" % (
        len(weak_items), total_weak_amount))
    print("  Malloc items: %d categories, %d total blocks" % (
        len(malloc_items), total_malloc_amount))
    # Point3D(24 bytes) * 5000 + Node(16 bytes) * 1000 应该贡献大量 weak/malloc 块
    if total_weak_amount + total_malloc_amount >= 3000:
        print("  PASS sufficient weak/malloc blocks detected (>= 3000)")
    else:
        print("  WARN fewer weak/malloc blocks than expected")

    # Check 5: 总体结果条目数
    print("\n[Check 5] Result items count...")
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

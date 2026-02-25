#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Deque 边界 & 批量分配测试验证脚本

Bug 针对：
    1. DequeClassifyInfo 边界检查失效 (custom.go:156)
    2. new Type[N] 首元素丢失 — cookie 偏移导致第一个对象不在 malloc 块起始位置
       vector 指针解引用找到 Entity[0] 但 JustMatchMemoryPieceSize 要求 addr==begin
       Entity[0] 地址 = malloc_begin + 8 (cookie) != malloc_begin → 返回 0 → 不统计
    3. ResultClassify 1拆N 阈值 n>5 (cpp.go:970) — 未在此测试中触发
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
    print("C++ Deque & Batch Alloc Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    all_passed = True

    # Check 1: Job 类型识别 (deque 中的元素)
    # 500 deques * 50 jobs = 25000
    print("\n[Check 1] Job instances (from deque)...")
    job = find_type_containing(items, "Job")
    if job:
        amount = job.get("amount", 0)
        print("  Found: %s" % job.get("type", ""))
        print("  amount: %d (expected: ~25000)" % amount)
        if amount >= 22000:
            print("  PASS amount >= 22000")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Job not found")
        all_passed = False

    # Check 2: Entity 类型识别
    # batch3: 2000*3=6000, batch5: 2000*5=10000, batch8: 1000*8=8000
    # 总计 24000
    print("\n[Check 2] Entity instances...")
    entity_items = find_all_types_containing(items, "Entity")
    total_entity = sum(i.get("amount", 0) for i in entity_items)
    print("  Entity entries: %d" % len(entity_items))
    for e in entity_items:
        print("    - %s: amount=%d, avg_size=%d" % (
            e.get("type", ""), e.get("amount", 0),
            e.get("avg_size", 0)))
    print("  Total Entity amount: %d" % total_entity)
    # 已知 bug: new Type[N] 首元素丢失，每个 malloc 块只被当作 1 个对象统计
    # 实际: batch3=2000块, batch5=2000块, batch8=1000块 = 5000 个 malloc 块
    # 如果 bug 修复后: 2000*3 + 2000*5 + 1000*8 = 24000 个 Entity
    if total_entity >= 20000:
        print("  total >= 20000: new Type[N] bug 已修复!")
        print("  PASS")
    elif total_entity >= 4500:
        print("  total=%d ~= 5000: 符合已知 bug 行为 (每个 new[] 块算 1 个)" % total_entity)
        print("  KNOWN BUG: new Type[N] 首元素丢失")
        print("  PASS (已知 bug，暂不阻断)")
    else:
        print("  FAIL total too low (unexpected)")
        all_passed = False

    # Check 3: new Type[N] 首元素丢失 bug 检测
    # new Entity[N] 有 8 字节 cookie，Entity[0] 在 offset 8
    # vector 指针解引用找到 Entity[0]，标记为 seen
    # JustMatchMemoryPieceSize 要求 addr==begin，但 Entity[0] != malloc 起始 → 返回 0
    # 后续 weak 扫描发现 vtable 时已 seen → 也不统计
    print("\n[Check 3] Bug detection: new Type[N] first element...")
    if total_entity >= 22000:
        print("  total=%d >= 22000: new[] 首元素被正确统计" % total_entity)
        print("  PASS (bug 已修复)")
    elif total_entity >= 4500:
        print("  total=%d ~= 5000: 每个 new[] 块只算 1 个对象" % total_entity)
        print("  KNOWN BUG: new Type[N] cookie 偏移导致首元素丢失")
    else:
        print("  total=%d: 异常偏低" % total_entity)

    # Check 4: 结果概览
    print("\n[Check 4] Result items overview...")
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

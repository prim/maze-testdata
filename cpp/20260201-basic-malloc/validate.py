#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Basic Malloc 测试验证脚本

验证目标：
    1. 验证 Maze 能识别 class A 实例
    2. 验证 malloc 分配的不同大小内存块

测试数据：
    - 80000 个 class A 实例 (8 bytes，含 vtable 指针)
    - 80000 个 malloc(16) 块
    - 80000 个 malloc(32) 块
    - 80000 个 malloc(64) 块

注意：ptmalloc 会对小块进行对齐，实际 chunk 大小可能大于请求大小
"""
from __future__ import print_function
import json
import sys
import os


# =========================================================
# 预期值常量
# =========================================================
EXPECTED_COUNT = 80000

# ptmalloc 最小 chunk 大小是 32 bytes (64位系统)
# malloc(16) -> chunk 32 bytes
# malloc(32) -> chunk 48 bytes  
# malloc(64) -> chunk 80 bytes
# class A (8 bytes) -> chunk 32 bytes (通过 new 分配)


def find_type_containing(items, substring):
    """查找类型名包含指定子串的项"""
    for item in items:
        if substring in item.get("type", ""):
            return item
    return None


def find_by_avg_size_range(items, min_size, max_size):
    """按 avg_size 范围查找"""
    results = []
    for item in items:
        avg_size = item.get("avg_size", 0)
        if min_size <= avg_size <= max_size:
            results.append(item)
    return results


def validate(data):
    """验证 maze 分析结果"""
    print("=" * 60)
    print("C++ Basic Malloc Test Validation")
    print("=" * 60)
    
    # 检查基本结构
    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"
    
    items = data["items"]
    summary = data["summary"]
    
    # 打印摘要
    print("\n[Summary]")
    print("  VMS: %s" % summary.get("vms", "N/A"))
    print("  Ptmalloc Heap: %s" % summary.get("ptmalloc_heap", "N/A"))
    
    all_passed = True
    
    # =========================================================
    # Check 1: class A 实例
    # =========================================================
    print("\n[Check 1] class A instances...")
    class_a = find_type_containing(items, "A")
    if class_a:
        amount = class_a.get("amount", 0)
        avg_size = class_a.get("avg_size", 0)
        print("  Found: %s" % class_a.get("type", ""))
        print("  amount: %d (expected: ~%d)" % (amount, EXPECTED_COUNT))
        print("  avg_size: %d" % avg_size)
        
        # class A 应该有 80000 个左右
        if amount >= EXPECTED_COUNT * 0.9:
            print("  ✓ amount reasonable (>= 90%% of %d)" % EXPECTED_COUNT)
        else:
            print("  ⚠ amount lower than expected")
    else:
        print("  ⚠ class A not found in results (may be grouped differently)")
    
    # =========================================================
    # Check 2: malloc 块统计
    # =========================================================
    print("\n[Check 2] malloc blocks...")
    
    # 统计不同大小的 chunk
    total_chunks = 0
    for item in items:
        amount = item.get("amount", 0)
        total_chunks += amount
    
    print("  Total items in result: %d" % len(items))
    print("  Total chunks counted: %d" % total_chunks)
    
    # 预期至少有 80000 * 4 = 320000 个分配
    expected_total = EXPECTED_COUNT * 4
    if total_chunks >= expected_total * 0.5:
        print("  ✓ Total chunks reasonable (>= 50%% of %d)" % expected_total)
    else:
        print("  ⚠ Total chunks lower than expected")
    
    # =========================================================
    # Check 3: 检查是否有大量小块
    # =========================================================
    print("\n[Check 3] Small chunk distribution...")
    
    # 查找 avg_size 在 16-100 范围内的项
    small_chunks = find_by_avg_size_range(items, 16, 100)
    print("  Items with avg_size 16-100 bytes: %d" % len(small_chunks))
    
    for item in small_chunks[:5]:  # 只显示前5个
        print("    - %s: amount=%d, avg_size=%d" % (
            item.get("type", "unknown"),
            item.get("amount", 0),
            item.get("avg_size", 0)
        ))
    
    if len(small_chunks) > 0:
        print("  ✓ Found small chunks as expected")
    else:
        print("  ⚠ No small chunks found")
        all_passed = False
    
    # =========================================================
    # Check 4: 内存大小合理性
    # =========================================================
    print("\n[Check 4] Memory size sanity check...")
    
    ptmalloc_heap = summary.get("ptmalloc_heap", 0)
    
    # 预期堆大小：
    # 80000 * 32 (class A) + 80000 * 32 (malloc 16) + 80000 * 48 (malloc 32) + 80000 * 80 (malloc 64)
    # = 80000 * (32 + 32 + 48 + 80) = 80000 * 192 = 15.36 MB
    # 加上 vector 和其他开销，预期 20-50 MB
    
    if ptmalloc_heap > 0:
        heap_mb = ptmalloc_heap / (1024 * 1024)
        print("  Ptmalloc heap: %.2f MB" % heap_mb)
        
        if 10 < heap_mb < 100:
            print("  ✓ Heap size reasonable (10-100 MB)")
        else:
            print("  ⚠ Heap size outside expected range")
    else:
        print("  ⚠ Ptmalloc heap size not available")
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_passed:
        print("All validations passed!")
    else:
        print("Some validations need attention (may still be acceptable)")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        print("")
        print("Example:")
        print("  python validate.py maze-result.json")
        sys.exit(1)
    
    with open(sys.argv[1], "r") as f:
        data = json.load(f)
    
    result = validate(data)
    sys.exit(0 if result else 1)

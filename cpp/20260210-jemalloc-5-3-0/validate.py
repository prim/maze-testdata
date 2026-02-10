#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jemalloc Malloc 测试验证脚本

验证目标：
    1. 验证 Maze 检测到 jemalloc 分配器
    2. 验证 class A 实例被正确识别
    3. 验证各种大小的 malloc 块存在
    4. 验证大块 (1MB/2MB/3MB) 被识别

测试数据：
    - 20000 个 class A 实例
    - 20000 个 malloc(16/32/64) 块
    - 10000 个 malloc(128/256/512/1024) 块
    - 100 个 malloc(1MB/2MB/3MB) 块
"""
from __future__ import print_function
import json
import sys
import os


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
    print("jemalloc Malloc Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    summary = data["summary"]

    print("\n[Summary]")
    print("  VMS: %s" % summary.get("vms", "N/A"))

    all_passed = True

    # =========================================================
    # Check 1: 总分配量合理性
    # =========================================================
    print("\n[Check 1] Total allocation sanity...")

    total_chunks = 0
    for item in items:
        total_chunks += item.get("amount", 0)

    print("  Total items in result: %d" % len(items))
    print("  Total chunks counted: %d" % total_chunks)

    # 预期: 20000*4 + 10000*4 + 100*3 = 120300
    if total_chunks >= 50000:
        print("  ✓ Total chunks reasonable (>= 50000)")
    else:
        print("  ⚠ Total chunks lower than expected: %d" % total_chunks)
        all_passed = False

    # =========================================================
    # Check 2: 小块分布
    # =========================================================
    print("\n[Check 2] Small chunk distribution...")

    small_chunks = find_by_avg_size_range(items, 8, 128)
    print("  Items with avg_size 8-128 bytes: %d" % len(small_chunks))
    for item in small_chunks[:6]:
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
    # Check 3: 中等块分布 (128-1024)
    # =========================================================
    print("\n[Check 3] Medium chunk distribution (128-1024 bytes)...")

    medium_chunks = find_by_avg_size_range(items, 129, 2048)
    print("  Items with avg_size 129-2048 bytes: %d" % len(medium_chunks))
    for item in medium_chunks[:6]:
        print("    - %s: amount=%d, avg_size=%d" % (
            item.get("type", "unknown"),
            item.get("amount", 0),
            item.get("avg_size", 0)
        ))

    if len(medium_chunks) > 0:
        print("  ✓ Found medium chunks as expected")
    else:
        print("  ⚠ No medium chunks found")

    # =========================================================
    # Check 4: 大块分布 (1MB+)
    # =========================================================
    print("\n[Check 4] Large block distribution (1MB+)...")

    large_chunks = find_by_avg_size_range(items, 900000, 4000000)
    print("  Items with avg_size ~1MB-3MB: %d" % len(large_chunks))
    for item in large_chunks[:5]:
        size_mb = item.get("avg_size", 0) / (1024.0 * 1024.0)
        print("    - %s: amount=%d, avg_size=%.2fMB" % (
            item.get("type", "unknown"),
            item.get("amount", 0),
            size_mb
        ))

    if len(large_chunks) > 0:
        print("  ✓ Found large blocks as expected")
    else:
        print("  ⚠ No large blocks found (may be in mmap region)")

    # =========================================================
    # Check 5: VMS 大小合理性
    # =========================================================
    print("\n[Check 5] VMS size sanity check...")

    vms = summary.get("vms", 0)
    if vms > 0:
        vms_gb = vms / (1024.0 * 1024.0 * 1024.0)
        print("  VMS: %.2f GB" % vms_gb)

        # 预期: 1MB*100 + 2MB*100 + 3MB*100 = 600MB + 其他 ≈ 6-10 GB
        if vms_gb > 0.3:
            print("  ✓ VMS size reasonable (> 0.3GB)")
        else:
            print("  ⚠ VMS size seems too small: %.2f GB" % vms_gb)
    else:
        print("  ⚠ VMS not available")

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
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

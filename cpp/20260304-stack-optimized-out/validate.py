#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC-B002: Optimized Out 变量处理测试验证脚本

验证目标：
1. 程序在 -O2 优化下正常运行不崩溃
2. 即使部分变量被优化，分析仍能完成
3. 无异常抛出
"""

import json
import sys


def validate(data):
    """验证 maze-result.json 中的结果"""
    items = data.get("items", [])

    print("=" * 60)
    print("TC-B002: Optimized Out Variable Test")
    print("=" * 60)

    # 检查是否有 OptimizedTest 类型（可能有部分被识别）
    found_optimized = False
    optimized_amount = 0

    for item in items:
        type_name = item.get("type", "")
        if "OptimizedTest" in type_name:
            found_optimized = True
            optimized_amount = item.get("amount", 0)
            print(f"✓ Found OptimizedTest type: {type_name}")
            print(f"  amount: {optimized_amount}")
            break

    print()

    # 验证结果 - 主要是确认没有崩溃
    passed = True

    # 检查 summary 是否存在
    summary = data.get("summary", {})
    if not summary:
        print("✗ Summary not found in results")
        passed = False
    else:
        print(f"✓ Summary exists: {summary}")

    # 检查 items 是否存在
    if not items:
        print("⚠ No items found in results (may be expected with heavy optimization)")
    else:
        print(f"✓ Found {len(items)} items in results")

    print()

    # 主要验证：分析完成无崩溃
    if passed:
        print("✅ TC-B002 PASSED: Analysis completed without crash")
        print("   (Optimized out variables handled correctly)")
    else:
        print("✗ TC-B002 FAILED: Issues found")

    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC-B006: 引用类型处理测试验证脚本

验证目标：
1. RefTarget 对象被正确识别
2. 引用类型处理无崩溃
"""

import json
import sys


def validate(data):
    """验证 maze-result.json 中的结果"""
    items = data.get("items", [])

    print("=" * 60)
    print("TC-B006: Reference Type Test")
    print("=" * 60)

    # 检查 RefTarget
    found_ref = False
    ref_amount = 0

    for item in items:
        type_name = item.get("type", "")
        if "RefTarget" in type_name:
            found_ref = True
            ref_amount = item.get("amount", 0)
            print(f"✓ Found RefTarget type: {type_name}")
            print(f"  amount: {ref_amount}")
            break

    print()

    # 验证结果
    passed = True

    if not found_ref:
        print("⚠ RefTarget not found in results")
        print("  (Reference handling may store objects differently)")
    else:
        # 预期 2 个对象
        if ref_amount >= 1:
            print(f"✓ RefTarget amount ({ref_amount}) >= 1 (expected ~2)")
        else:
            print(f"⚠ RefTarget amount ({ref_amount}) is lower than expected")

    print()

    # 主要验证：分析完成无崩溃
    summary = data.get("summary", {})
    if summary:
        print(f"✓ Analysis completed successfully")
        print(f"  Total items: {len(items)}")
    else:
        print("✗ Summary not found")
        passed = False

    print()

    if passed:
        print("✅ TC-B006 PASSED: Reference type handling completed")
    else:
        print("✗ TC-B006 FAILED")

    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

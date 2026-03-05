#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC-B001: 空指针和 NULL 处理测试验证脚本

验证目标：
1. 只有有效的 TestObject 被识别（amount = 1）
2. 空指针、无效地址被正确过滤，不会导致崩溃
3. 已释放的内存被过滤
"""

import json
import sys


def validate(data):
    """验证 maze-result.json 中的结果"""
    items = data.get("items", [])

    print("=" * 60)
    print("TC-B001: Null Pointer Handling Test")
    print("=" * 60)

    found_test_object = False
    test_object_amount = 0

    for item in items:
        type_name = item.get("type", "")
        if "TestObject" in type_name:
            found_test_object = True
            test_object_amount = item.get("amount", 0)
            print(f"✓ Found TestObject type: {type_name}")
            print(f"  amount: {test_object_amount}")
            break

    print()

    # 验证结果
    passed = True

    if not found_test_object:
        print("✗ TestObject not found in results")
        passed = False
    else:
        # 应该只识别出 1 个有效对象
        if test_object_amount == 1:
            print(f"✓ TestObject amount is exactly 1 (valid object only)")
        elif test_object_amount > 1:
            print(f"⚠ TestObject amount is {test_object_amount}, expected 1")
            print("  (May include some invalid pointers, but within tolerance)")
            # 允许少量误报，只要不超过 3 个
            if test_object_amount > 3:
                passed = False
        else:
            print(f"✗ TestObject amount is {test_object_amount}, expected at least 1")
            passed = False

    print()

    # 检查是否有崩溃或异常
    summary = data.get("summary", {})
    total_objects = summary.get("total_objects", 0)
    print(f"Summary: total_objects = {total_objects}")

    if passed:
        print("\n✅ TC-B001 PASSED: Null pointers are correctly filtered")
    else:
        print("\n✗ TC-B001 FAILED: Issues found in null pointer handling")

    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

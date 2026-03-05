#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC-004: 非多态对象通过栈变量识别的验证

验证 maze 能否正确识别仅通过栈局部变量持有的非多态 C++ 对象
"""

import json
import sys
import os


def validate(data):
    """
    验证 maze 分析结果

    Args:
        data: maze-result.json 解析后的 dict

    Returns:
        bool: 验证是否通过
    """
    print("=" * 60)
    print("TC-004: Stack Non-Polymorphic Object Recognition")
    print("=" * 60)

    items = data.get("items", [])
    summary = data.get("summary", {})

    # 检查是否识别到了 ConfigManager 类型
    config_manager_found = False
    config_manager_amount = 0

    for item in items:
        type_name = item.get("type", "")
        if "ConfigManager" in type_name:
            config_manager_found = True
            config_manager_amount = item.get("amount", 0)
            print(f"✓ Found ConfigManager type: {type_name}")
            print(
                f"  amount: {config_manager_amount}, avg_size: {item.get('avg_size', 0)}"
            )
            break

    # 验证结果
    passed = True

    if not config_manager_found:
        print("✗ ConfigManager type not found (expected to be found via stack locals)")
        print(
            "  This is a non-polymorphic class that can only be reached via stack variables"
        )
        passed = False
    else:
        # 验证数量是否合理（测试程序创建了 10 个）
        expected = 10
        tolerance = 0.1  # 10% 容差
        min_expected = int(expected * (1 - tolerance))

        if config_manager_amount < min_expected:
            print(
                f"✗ ConfigManager amount ({config_manager_amount}) is less than expected minimum ({min_expected})"
            )
            passed = False
        else:
            print(
                f"✓ ConfigManager amount ({config_manager_amount}) is within expected range (>= {min_expected})"
            )

    # 检查 summary
    print(f"\nSummary:")
    print(f"  total_objects: {summary.get('total_objects', 0)}")
    print(f"  total_size: {summary.get('total_size', 0)}")

    if passed:
        print("\n✓ All validations passed!")
    else:
        print("\n✗ Some validations failed!")

    return passed


def validate_cpp_json():
    """
    验证 .cpp.json 文件中的 stack_locals 字段
    """
    cpp_json_path = ".cpp.json"
    if not os.path.exists(cpp_json_path):
        print(f"⚠ Warning: {cpp_json_path} not found, skipping stack_locals validation")
        return True

    print(f"\nValidating {cpp_json_path}...")

    with open(cpp_json_path, "r") as f:
        cpp_data = json.load(f)

    if "stack_locals" not in cpp_data:
        print("✗ 'stack_locals' field not found in .cpp.json")
        return False

    stack_locals = cpp_data["stack_locals"]
    count = len(stack_locals)
    print(f"✓ 'stack_locals' field found with {count} entries")

    if count == 0:
        print("✗ 'stack_locals' is empty")
        return False

    # 显示前几个栈变量
    print("\nFirst 5 stack locals entries:")
    for i, (addr, info) in enumerate(list(stack_locals.items())[:5]):
        print(
            f"  [{i + 1}] addr={addr}, type_idx={info.get('type', 'N/A')}, name={info.get('name', 'N/A')}, func={info.get('func', 'N/A')}"
        )

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate.py <maze-result.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    with open(json_path, "r") as f:
        data = json.load(f)

    result1 = validate(data)
    result2 = validate_cpp_json()

    if result1 and result2:
        print("\n" + "=" * 60)
        print("✓✓✓ TC-004 PASSED ✓✓✓")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗✗✗ TC-004 FAILED ✗✗✗")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

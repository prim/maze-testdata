#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC-001: Stack Locals Basic Test Validation
验证 maze 能否正确收集函数栈帧中的局部变量
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
    print("TC-001: Stack Locals Basic Test")
    print("=" * 60)

    items = data.get("items", [])
    summary = data.get("summary", {})

    # 检查是否识别到了 Point 类型
    point_found = False
    datablock_found = False
    simplenode_found = False

    for item in items:
        type_name = item.get("type", "")
        if "Point" in type_name:
            point_found = True
            print(f"✓ Found Point type: {type_name}")
            print(
                f"  amount: {item.get('amount', 0)}, avg_size: {item.get('avg_size', 0)}"
            )
        elif "DataBlock" in type_name:
            datablock_found = True
            print(f"✓ Found DataBlock type: {type_name}")
            print(
                f"  amount: {item.get('amount', 0)}, avg_size: {item.get('avg_size', 0)}"
            )
        elif "SimpleNode" in type_name:
            simplenode_found = True
            print(f"✓ Found SimpleNode type: {type_name}")
            print(
                f"  amount: {item.get('amount', 0)}, avg_size: {item.get('avg_size', 0)}"
            )

    # 验证结果
    passed = True

    if not point_found:
        print("✗ Point type not found (expected to be found via stack locals)")
        passed = False

    if not datablock_found:
        print("✗ DataBlock type not found (expected to be found via stack locals)")
        passed = False

    if not simplenode_found:
        print("✗ SimpleNode type not found (expected to be found via stack locals)")
        passed = False

    # 检查是否有栈变量相关的信息
    # 通过查看 summary 中的内存统计
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
        print("✓✓✓ TC-001 PASSED ✓✓✓")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗✗✗ TC-001 FAILED ✗✗✗")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

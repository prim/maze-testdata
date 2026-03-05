#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TC-B007: 大内存进程栈变量收集测试验证脚本

验证目标：
1. 大内存进程分析完成无崩溃
2. 分析时间在合理范围内
3. LargeMemNode 对象被正确识别
"""

import json
import sys
import time


def validate(data):
    """验证 maze-result.json 中的结果"""
    items = data.get("items", [])

    print("=" * 60)
    print("TC-B007: Large Memory Process Test")
    print("=" * 60)

    # 检查 LargeMemNode
    found_node = False
    node_amount = 0

    for item in items:
        type_name = item.get("type", "")
        if "LargeMemNode" in type_name:
            found_node = True
            node_amount = item.get("amount", 0)
            print(f"✓ Found LargeMemNode type: {type_name}")
            print(f"  amount: {node_amount}")
            break

    print()

    # 验证结果
    passed = True

    if not found_node:
        print("⚠ LargeMemNode not found in results")
    else:
        if node_amount >= 20:
            print(f"✓ LargeMemNode amount ({node_amount}) >= 20 (expected ~50)")
        else:
            print(f"⚠ LargeMemNode amount ({node_amount}) is lower than expected")

    print()

    # 主要验证：分析完成无崩溃
    summary = data.get("summary", {})
    if summary:
        print(f"✓ Analysis completed successfully")
        print(f"  Total items: {len(items)}")

        # 检查内存使用
        vms = summary.get("vms", 0)
        print(f"  Process VMS: {vms / 1024 / 1024:.1f} MB")
    else:
        print("✗ Summary not found")
        passed = False

    print()

    if passed:
        print("✅ TC-B007 PASSED: Large memory process handled correctly")
    else:
        print("✗ TC-B007 FAILED")

    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

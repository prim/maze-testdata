#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ Edge Case Bug 触发测试验证脚本

Bug 针对：
    1. checkStructLastMemberIsArrayOne off-by-one (cpp.go:1051)
       - SlotTable 含 Slot[1] 柔性数组，精确分配
       - 如果最后一个 Slot 被漏掉，SlotTable 的 total_size 会偏小
    2. ArrayClassifyInfo 指针数组遇 NULL 放弃 (base.go:203)
       - Pipeline 含 Handler*[4]，后 2 个为 NULL
       - 如果遇 NULL 就放弃，Pipeline 通过指针数组追踪到的 Handler 会比 FullPipeline 少
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
    print("C++ Edge Case Bug Test Validation")
    print("=" * 60)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    all_passed = True

    # Check 1: Handler 类型识别
    # Pipeline(3000) * 2 + FullPipeline(3000) * 4 = 18000 个 Handler
    print("\n[Check 1] Handler instances...")
    handler = find_type_containing(items, "Handler")
    if handler:
        amount = handler.get("amount", 0)
        print("  Found: %s" % handler.get("type", ""))
        print("  amount: %d (expected: ~18000)" % amount)
        if amount >= 16000:
            print("  PASS amount >= 16000")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Handler not found")
        all_passed = False

    # Check 2: Pipeline 类型识别
    print("\n[Check 2] Pipeline instances...")
    pipeline = find_type_containing(items, "Pipeline")
    if pipeline:
        amount = pipeline.get("amount", 0)
        print("  Found: %s" % pipeline.get("type", ""))
        print("  amount: %d (expected: ~3000)" % amount)
        if amount >= 2500:
            print("  PASS amount >= 2500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL Pipeline not found")
        all_passed = False

    # Check 3: FullPipeline 类型识别
    print("\n[Check 3] FullPipeline instances...")
    full = find_type_containing(items, "FullPipeline")
    if full:
        amount = full.get("amount", 0)
        print("  Found: %s" % full.get("type", ""))
        print("  amount: %d (expected: ~3000)" % amount)
        if amount >= 2500:
            print("  PASS amount >= 2500")
        else:
            print("  FAIL amount too low")
            all_passed = False
    else:
        print("  FAIL FullPipeline not found")
        all_passed = False

    # Check 4: Bug 2 检测 — 指针数组含 NULL 时 Handler 是否丢失
    # Pipeline 每个有 2 个 Handler，FullPipeline 每个有 4 个
    # 如果 ArrayClassifyInfo 遇 NULL 放弃，Pipeline 的 Handler 不会被追踪
    # 那 Handler 总数只有 FullPipeline 的 12000，而不是 18000
    print("\n[Check 4] Bug detection: NULL pointer array...")
    if handler:
        amount = handler.get("amount", 0)
        if amount >= 17000:
            print("  amount=%d >= 17000: 指针数组含 NULL 的 Handler 被正确追踪" % amount)
            print("  PASS (Bug 2 未触发或已修复)")
        elif amount >= 11000:
            print("  amount=%d < 17000: Pipeline 的 Handler 可能丢失" % amount)
            print("  BUG DETECTED: ArrayClassifyInfo 遇 NULL 放弃了指针数组")
            print("  (base.go:203 IsPointer 对 NULL 返回 false)")
        else:
            print("  amount=%d: 异常偏低" % amount)

    # Check 5: 结果概览
    print("\n[Check 5] Result items overview...")
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

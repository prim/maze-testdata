#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class Merge 测试验证脚本

验证目标：
    1. 普通模式：<class A> instance 和内层大字典分别统计
    2. --py-merge 模式：内层大字典应该被合并到 <class A> instance

测试数据：
    - 10000 个 class A 实例
    - 每个实例包含 self.items = {"a": 1, "b": {256条目的大字典}}

内存布局预期 (Python 3.11):
    - <class A> instance:      ~96 bytes (对象头)
    - {"a", "b"} 外层 dict:     ~192 bytes
    - {long => long}<256:      ~9304 bytes (内层大字典)
    
合并模式预期:
    - <class A> instance avg_size 应约等于 96 + 192 + 9304 ≈ 9592 bytes
"""
from __future__ import print_function
import json
import sys
import os


# =========================================================
# 预期值常量 (基于 Python 3.11 测量)
# =========================================================
EXPECTED_COUNT = 10000

# 普通模式下各组件的独立大小
NORMAL_CLASS_A_AVG_SIZE = 96          # class A 实例本身
NORMAL_OUTER_DICT_AVG_SIZE = 192      # {"a", "b"}
NORMAL_INNER_DICT_AVG_SIZE = 9304     # {long => long}<256

# 合并模式下 class A 应包含所有子对象
# 允许 10% 的误差范围
MERGE_CLASS_A_MIN_AVG_SIZE = int((NORMAL_CLASS_A_AVG_SIZE + 
                                   NORMAL_OUTER_DICT_AVG_SIZE + 
                                   NORMAL_INNER_DICT_AVG_SIZE) * 0.9)
MERGE_CLASS_A_MAX_AVG_SIZE = int((NORMAL_CLASS_A_AVG_SIZE + 
                                   NORMAL_OUTER_DICT_AVG_SIZE + 
                                   NORMAL_INNER_DICT_AVG_SIZE) * 1.1)


def find_type_containing(items, substring):
    """查找类型名包含指定子串的项"""
    for item in items:
        if substring in item.get("type", ""):
            return item
    return None


def find_exact_type(items, target_type):
    """精确匹配类型名"""
    for item in items:
        if item.get("type", "") == target_type:
            return item
    return None


def is_merge_mode():
    """检查是否在合并模式下运行"""
    # 通过环境变量传递
    return os.environ.get("MAZE_PY_MERGE", "0") == "1"


def validate_normal_mode(items, summary):
    """
    验证普通模式的结果
    
    预期:
        - <class A> instance: amount=10000, avg_size≈96
        - {long => long}<256: amount=10000, avg_size≈9304
        - {"a", "b"}: amount=10000, avg_size≈192
    """
    print("\n" + "=" * 60)
    print("Normal Mode Validation")
    print("=" * 60)
    
    all_passed = True
    
    # =========================================================
    # Check 1: <class A> instance
    # =========================================================
    print("\n[Check 1] <class A> instance...")
    class_a = find_type_containing(items, "<class A>")
    if class_a:
        amount = class_a["amount"]
        avg_size = class_a["avg_size"]
        print("  Found: %s" % class_a["type"])
        print("  amount: %d (expected: %d)" % (amount, EXPECTED_COUNT))
        print("  avg_size: %d (expected: ~%d)" % (avg_size, NORMAL_CLASS_A_AVG_SIZE))
        
        if amount != EXPECTED_COUNT:
            print("  ✗ FAIL: amount mismatch")
            all_passed = False
        else:
            print("  ✓ amount correct")
        
        # 普通模式下 avg_size 应该很小（只有对象头）
        if avg_size < 200:  # 合理范围
            print("  ✓ avg_size reasonable for normal mode (< 200)")
        else:
            print("  ⚠ avg_size larger than expected (may indicate merge)")
    else:
        print("  ✗ FAIL: <class A> instance not found")
        all_passed = False
    
    # =========================================================
    # Check 2: Inner dict {long => long}<256
    # =========================================================
    print("\n[Check 2] Inner dict {long => long}<256...")
    inner_dict = find_type_containing(items, "{long => long}")
    if inner_dict:
        amount = inner_dict["amount"]
        avg_size = inner_dict["avg_size"]
        print("  Found: %s" % inner_dict["type"])
        print("  amount: %d (expected: %d)" % (amount, EXPECTED_COUNT))
        print("  avg_size: %d (expected: ~%d)" % (avg_size, NORMAL_INNER_DICT_AVG_SIZE))
        
        if amount != EXPECTED_COUNT:
            print("  ✗ FAIL: amount mismatch")
            all_passed = False
        else:
            print("  ✓ amount correct")
        
        # 验证 avg_size 在合理范围内 (允许 20% 误差)
        expected_min = int(NORMAL_INNER_DICT_AVG_SIZE * 0.8)
        expected_max = int(NORMAL_INNER_DICT_AVG_SIZE * 1.2)
        if expected_min <= avg_size <= expected_max:
            print("  ✓ avg_size in expected range [%d, %d]" % (expected_min, expected_max))
        else:
            print("  ⚠ avg_size outside expected range [%d, %d]" % (expected_min, expected_max))
    else:
        print("  ✗ FAIL: Inner dict not found (should exist in normal mode)")
        all_passed = False
    
    # =========================================================
    # Check 3: Outer dict {"a", "b"}
    # =========================================================
    print("\n[Check 3] Outer dict {\"a\", \"b\"}...")
    outer_dict = find_type_containing(items, '"a"')
    if outer_dict and '"b"' in outer_dict.get("type", ""):
        amount = outer_dict["amount"]
        avg_size = outer_dict["avg_size"]
        print("  Found: %s" % outer_dict["type"])
        print("  amount: %d (expected: %d)" % (amount, EXPECTED_COUNT))
        print("  avg_size: %d (expected: ~%d)" % (avg_size, NORMAL_OUTER_DICT_AVG_SIZE))
        
        if amount != EXPECTED_COUNT:
            print("  ✗ FAIL: amount mismatch")
            all_passed = False
        else:
            print("  ✓ amount correct")
    else:
        print("  ⚠ Outer dict not found in top results")
    
    return all_passed


def validate_merge_mode(items, summary):
    """
    验证合并模式的结果
    
    预期:
        - <class A> instance: amount=10000, avg_size≈9592 (包含内层字典)
        - {long => long}<256: 不应该出现 (已合并) 或 amount < 10000
        - {"a", "b"}: 不应该出现 (已合并) 或 amount < 10000
    """
    print("\n" + "=" * 60)
    print("Merge Mode Validation (--py-merge)")
    print("=" * 60)
    
    all_passed = True
    
    # =========================================================
    # Check 1: <class A> instance with merged size
    # =========================================================
    print("\n[Check 1] <class A> instance (should include merged children)...")
    class_a = find_type_containing(items, "<class A>")
    if class_a:
        amount = class_a["amount"]
        avg_size = class_a["avg_size"]
        total_size = class_a.get("total_size", amount * avg_size)
        print("  Found: %s" % class_a["type"])
        print("  amount: %d (expected: %d)" % (amount, EXPECTED_COUNT))
        print("  avg_size: %d" % avg_size)
        print("  total_size: %d" % total_size)
        print("  Expected avg_size range: [%d, %d]" % 
              (MERGE_CLASS_A_MIN_AVG_SIZE, MERGE_CLASS_A_MAX_AVG_SIZE))
        
        if amount != EXPECTED_COUNT:
            print("  ✗ FAIL: amount mismatch")
            all_passed = False
        else:
            print("  ✓ amount correct")
        
        # 验证合并后的 avg_size
        if MERGE_CLASS_A_MIN_AVG_SIZE <= avg_size <= MERGE_CLASS_A_MAX_AVG_SIZE:
            print("  ✓ avg_size in expected merged range")
            print("    (confirms inner dict is merged into class A)")
        elif avg_size > MERGE_CLASS_A_MAX_AVG_SIZE:
            print("  ⚠ avg_size larger than expected (may have extra merges)")
        else:
            print("  ✗ FAIL: avg_size too small - merge may not be working")
            print("    Expected: >= %d (class + outer dict + inner dict)" % 
                  MERGE_CLASS_A_MIN_AVG_SIZE)
            all_passed = False
    else:
        print("  ✗ FAIL: <class A> instance not found")
        all_passed = False
    
    # =========================================================
    # Check 2: Inner dict should be merged (not appear separately)
    # =========================================================
    print("\n[Check 2] Inner dict {long => long}<256 (should be merged)...")
    inner_dict = find_type_containing(items, "{long => long}")
    if inner_dict:
        amount = inner_dict["amount"]
        print("  Found: %s (amount: %d)" % (inner_dict["type"], amount))
        if amount == EXPECTED_COUNT:
            print("  ✗ FAIL: Inner dict still counted separately (amount=%d)" % amount)
            print("    This means --py-merge is NOT working correctly")
            all_passed = False
        elif amount == 0:
            print("  ✓ All inner dicts merged (amount=0)")
        else:
            print("  ⚠ Partial merge: %d out of %d merged" % 
                  (EXPECTED_COUNT - amount, EXPECTED_COUNT))
    else:
        print("  ✓ Inner dict not found in results (fully merged)")
    
    # =========================================================
    # Check 3: Outer dict should also be merged
    # =========================================================
    print("\n[Check 3] Outer dict {\"a\", \"b\"} (should be merged)...")
    outer_dict = find_type_containing(items, '"a"')
    if outer_dict and '"b"' in outer_dict.get("type", ""):
        amount = outer_dict["amount"]
        print("  Found: %s (amount: %d)" % (outer_dict["type"], amount))
        if amount == EXPECTED_COUNT:
            print("  ⚠ Outer dict still counted separately")
            print("    (may be expected if refcnt > 1)")
        else:
            print("  ⚠ Partial merge: %d remaining" % amount)
    else:
        print("  ✓ Outer dict not found in results (fully merged)")
    
    return all_passed


def validate(data):
    """
    验证 maze 分析结果
    
    根据 MAZE_PY_MERGE 环境变量自动选择验证模式
    """
    print("=" * 60)
    print("Class Merge Test Validation")
    print("=" * 60)
    
    # 检查基本结构
    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"
    
    items = data["items"]
    summary = data["summary"]
    
    # 打印摘要
    print("\n[Summary]")
    print("  VMS: %s" % summary.get("vms", "N/A"))
    print("  PyMemPool Objects: %s" % summary.get("pymempool_objects", "N/A"))
    print("  PyMemPool Size: %s" % summary.get("pymempool", "N/A"))
    
    merge_mode = is_merge_mode()
    print("  Mode: %s" % ("--py-merge" if merge_mode else "normal"))
    
    # 基本检查
    pymempool_objects = summary.get("pymempool_objects", 0)
    print("\n[Basic Check] PyMemPool objects: %d" % pymempool_objects)
    # assert pymempool_objects > 30000, \
    #     "Too few objects: %d (expected > 30000)" % pymempool_objects
    # print("  ✓ Object count reasonable (> 30000)")
    
    # 根据模式选择验证逻辑
    if merge_mode:
        result = validate_merge_mode(items, summary)
    else:
        result = validate_normal_mode(items, summary)
    
    # 最终结果
    print("\n" + "=" * 60)
    if result:
        print("All validations passed!")
    else:
        print("Some validations FAILED!")
    print("=" * 60)
    
    return result


def validate_merge_comparison(normal_data, merge_data):
    """
    比较普通模式和 --py-merge 模式的结果
    """
    print("\n" + "=" * 60)
    print("PyMerge Comparison Validation")
    print("=" * 60)
    
    normal_items = normal_data.get("items", [])
    merge_items = merge_data.get("items", [])
    
    all_passed = True
    
    # =========================================================
    # Compare <class A> instance
    # =========================================================
    normal_a = find_type_containing(normal_items, "<class A>")
    merge_a = find_type_containing(merge_items, "<class A>")
    
    print("\n[<class A> instance comparison]")
    if normal_a and merge_a:
        normal_avg = normal_a["avg_size"]
        merge_avg = merge_a["avg_size"]
        size_increase = merge_avg - normal_avg
        
        print("  Normal mode:   amount=%d, avg_size=%d" % 
              (normal_a["amount"], normal_avg))
        print("  PyMerge mode:  amount=%d, avg_size=%d" % 
              (merge_a["amount"], merge_avg))
        print("  Size increase: %d bytes" % size_increase)
        
        # 验证数量一致
        if normal_a["amount"] != merge_a["amount"]:
            print("  ✗ FAIL: amount mismatch between modes")
            all_passed = False
        else:
            print("  ✓ amount consistent")
        
        # --py-merge 模式下，avg_size 应该显著增加
        # 增加量应约等于内层字典大小
        expected_increase_min = int(NORMAL_INNER_DICT_AVG_SIZE * 0.8)
        expected_increase_max = int((NORMAL_INNER_DICT_AVG_SIZE + NORMAL_OUTER_DICT_AVG_SIZE) * 1.2)
        
        if size_increase >= expected_increase_min:
            print("  ✓ Size increased significantly (>= %d)" % expected_increase_min)
            if size_increase <= expected_increase_max:
                print("  ✓ Size increase in expected range [%d, %d]" % 
                      (expected_increase_min, expected_increase_max))
            else:
                print("  ⚠ Size increase larger than expected")
        else:
            print("  ✗ FAIL: Size increase too small (%d < %d)" % 
                  (size_increase, expected_increase_min))
            print("    This suggests --py-merge is not merging the inner dict")
            all_passed = False
    else:
        print("  ✗ Cannot compare - <class A> not found in one or both results")
        all_passed = False
    
    # =========================================================
    # Compare inner dict presence
    # =========================================================
    print("\n[Inner dict {long => long} comparison]")
    normal_inner = find_type_containing(normal_items, "long => long")
    merge_inner = find_type_containing(merge_items, "long => long")
    
    if normal_inner:
        print("  Normal mode:   amount=%d, avg_size=%d" % 
              (normal_inner["amount"], normal_inner["avg_size"]))
    else:
        print("  Normal mode:   not found (unexpected!)")
        all_passed = False
    
    if merge_inner:
        print("  PyMerge mode:  amount=%d, avg_size=%d" % 
              (merge_inner["amount"], merge_inner["avg_size"]))
        if merge_inner["amount"] == EXPECTED_COUNT:
            print("  ✗ FAIL: Inner dict not merged (amount still %d)" % EXPECTED_COUNT)
            all_passed = False
        elif merge_inner["amount"] < normal_inner["amount"] if normal_inner else True:
            print("  ✓ Partial/full merge (amount reduced)")
    else:
        print("  PyMerge mode:  not found (fully merged)")
        print("  ✓ Inner dict fully merged into parent")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("Comparison validation passed!")
    else:
        print("Comparison validation FAILED!")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json> [merge-result.json]")
        print("")
        print("Environment variables:")
        print("  MAZE_PY_MERGE=1  - Validate as merge mode result")
        print("")
        print("Examples:")
        print("  # Validate normal mode result")
        print("  python validate.py maze-result.json")
        print("")
        print("  # Validate merge mode result")
        print("  MAZE_PY_MERGE=1 python validate.py maze-result-merge.json")
        print("")
        print("  # Compare both modes")
        print("  python validate.py maze-result.json maze-result-merge.json")
        sys.exit(1)
    
    with open(sys.argv[1], "r") as f:
        data = json.load(f)
    
    result = validate(data)
    
    # 如果提供了第二个文件，进行对比验证
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "r") as f:
            merge_data = json.load(f)
        compare_result = validate_merge_comparison(data, merge_data)
        result = result and compare_result
    
    sys.exit(0 if result else 1)
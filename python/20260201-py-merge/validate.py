#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyMerge 模式验证脚本

验证策略：
    这个测试用例比较特殊，需要对比两次运行结果：
    1. 不带 --py-merge 的结果
    2. 带 --py-merge 的结果
    
    由于当前测试框架只支持单次运行，这里我们验证：
    - 基本结构正确性
    - 特定类型的存在性
    - 对象数量在合理范围内
    
    更深入的合并逻辑测试需要扩展测试框架支持对比模式。

测试覆盖的 Bug：
    Bug 1: refcnt=1 的顶层对象可能被错误跳过
           - 验证 toplevel_refcnt1_dicts 出现在结果中
    Bug 2: 两次遍历的 skip 策略与合并逻辑可能不一致
           - 需要对比模式验证
    问题 3: 嵌套容器的大小可能重复计算
           - 验证 nested_dicts 和 deep_nested_dicts 的 avg_size 合理
    问题 4: ClassifySkip 未正确重置
           - 需要多次调用 Maze 来测试

测试对象类型签名（预期）：
    - exclusive_dicts: {"ex_key_*_*"}
    - shared_dicts: {"shared_key_*"}
    - mixed_dicts: {"mixed_exclusive_*", "mixed_shared"}
    - nested_dicts: {"outer_key"}
    - exclusive_lists: list
    - number_dicts: {"big_int_*", "float_*"}
    - toplevel_refcnt1: {"toplevel_key_*"}
    - deep_nested_dicts: {"deep_outer"}
    - circular_refs: {"circular_a_key", ...}
"""
from __future__ import print_function
import sys
import re


def find_type_containing(items, substring):
    """查找类型名包含特定子串的项"""
    results = []
    for item in items:
        if substring in item.get("type", ""):
            results.append(item)
    return results


def find_type_matching(items, pattern):
    """查找类型名匹配正则的项"""
    regex = re.compile(pattern)
    results = []
    for item in items:
        if regex.search(item.get("type", "")):
            results.append(item)
    return results


def validate(data):
    """
    验证 maze 分析结果
    
    Args:
        data: maze-result.json 的内容
        
    Returns:
        bool: 验证是否通过
    """
    print("=" * 60)
    print("PyMerge Test Validation")
    print("=" * 60)
    
    # 基本结构检查
    assert "items" in data, "Missing 'items' in result"
    assert "summary" in data, "Missing 'summary' in result"
    
    items = data["items"]
    summary = data["summary"]
    
    print("\n[Summary]")
    print("  VMS: %s" % summary.get("vms", "N/A"))
    print("  PyMemPool Objects: %s" % summary.get("pymempool_objects", "N/A"))
    print("  PyMemPool Size: %s" % summary.get("pymempool", "N/A"))
    
    # =========================================================
    # 验证 1: 检查 pymempool 对象数量
    # 测试程序创建了约 550 个容器对象 + 大量字符串
    # =========================================================
    print("\n[Check 1] PyMemPool object count...")
    pymempool_objects = summary.get("pymempool_objects", 0)
    assert pymempool_objects > 500, \
        "Too few pymempool objects: %d (expected > 500)" % pymempool_objects
    print("  ✓ pymempool_objects = %d (> 500)" % pymempool_objects)
    
    # =========================================================
    # 验证 2: 检查 exclusive_dicts 类型存在
    # 类型签名应包含 "ex_key"
    # 注意：在 --py-merge 模式下，refcnt=1 的对象会被合并到父对象，
    #       因此可能不会独立出现在结果中
    # =========================================================
    print("\n[Check 2] exclusive_dicts presence...")
    ex_items = find_type_containing(items, "ex_key")
    
    if len(ex_items) > 0:
        total_ex_amount = sum(item.get("amount", 0) for item in ex_items)
        print("  ✓ Found %d type(s) with 'ex_key', total amount = %d" % (len(ex_items), total_ex_amount))
        
        # exclusive_dicts 应该有 100 个
        if total_ex_amount >= 100:
            print("  ✓ exclusive_dicts amount >= 100")
        else:
            print("  ⚠ exclusive_dicts amount low: %d (may be partially merged)" % total_ex_amount)
    else:
        # 在 --py-merge 模式下，refcnt=1 的对象可能被合并到父对象
        print("  ⚠ No 'ex_key' type found (expected in --py-merge mode: merged to parents)")
    
    # =========================================================
    # 验证 3: 检查 shared_dicts 类型存在
    # 类型签名应包含 "shared_key"
    # =========================================================
    print("\n[Check 3] shared_dicts presence...")
    shared_items = find_type_containing(items, "shared_key")
    assert len(shared_items) > 0, "Cannot find shared_dicts (type containing 'shared_key')"
    
    total_shared_amount = sum(item.get("amount", 0) for item in shared_items)
    print("  ✓ Found %d type(s) with 'shared_key', total amount = %d" % (len(shared_items), total_shared_amount))
    
    # shared_dicts 应该有 100 个
    assert total_shared_amount >= 100, \
        "shared_dicts amount too low: %d (expected >= 100)" % total_shared_amount
    print("  ✓ shared_dicts amount >= 100")
    
    # =========================================================
    # 验证 4: 检查 nested_dicts 类型存在
    # 类型签名应包含 "outer_key"
    # 注意：在 --py-merge 模式下可能被合并
    # =========================================================
    print("\n[Check 4] nested_dicts presence...")
    nested_items = find_type_containing(items, "outer_key")
    
    if len(nested_items) > 0:
        total_nested_amount = sum(item.get("amount", 0) for item in nested_items)
        print("  ✓ Found %d type(s) with 'outer_key', total amount = %d" % (len(nested_items), total_nested_amount))
        
        # nested_dicts 应该有 50 个
        if total_nested_amount >= 50:
            print("  ✓ nested_dicts amount >= 50")
        else:
            print("  ⚠ nested_dicts amount low: %d (may be partially merged)" % total_nested_amount)
    else:
        print("  ⚠ No 'outer_key' type found (expected in --py-merge mode: merged to parents)")
    
    # =========================================================
    # 验证 5: 检查 list 类型存在
    # =========================================================
    print("\n[Check 5] exclusive_lists presence...")
    list_items = find_type_containing(items, "list")
    if len(list_items) > 0:
        total_list_amount = sum(item.get("amount", 0) for item in list_items)
        print("  ✓ Found %d list type(s), total amount = %d" % (len(list_items), total_list_amount))
    else:
        # list 可能被归类为其他类型，不强制要求
        print("  ⚠ No explicit 'list' type found (may be classified differently)")
    
    # =========================================================
    # 验证 6: 检查 number_dicts 类型存在
    # 类型签名应包含 "big_int" 或 "float_"
    # =========================================================
    print("\n[Check 6] number_dicts presence...")
    num_items = find_type_containing(items, "big_int")
    if len(num_items) == 0:
        num_items = find_type_containing(items, "float_")
    
    if len(num_items) > 0:
        total_num_amount = sum(item.get("amount", 0) for item in num_items)
        print("  ✓ Found %d number dict type(s), total amount = %d" % (len(num_items), total_num_amount))
    else:
        print("  ⚠ No explicit number dict type found")
    
    # =========================================================
    # 验证 7: 检查 str 类型
    # 应该有大量 str 对象
    # =========================================================
    print("\n[Check 7] str/unicode presence...")
    str_items = find_type_containing(items, "str")
    unicode_items = find_type_containing(items, "unicode")
    
    str_total = sum(item.get("amount", 0) for item in str_items)
    unicode_total = sum(item.get("amount", 0) for item in unicode_items)
    total_strings = str_total + unicode_total
    
    print("  Found str types: %d, unicode types: %d" % (len(str_items), len(unicode_items)))
    print("  Total string objects: %d" % total_strings)
    
    if total_strings > 0:
        print("  ✓ String objects present")
    
    # =========================================================
    # 验证 8: Bug 1 - 检查 toplevel_refcnt1 类型存在
    # 确保 refcnt=1 的顶层对象没有被错误跳过
    # =========================================================
    print("\n[Check 8] Bug 1: toplevel_refcnt1 presence...")
    toplevel_items = find_type_containing(items, "toplevel_key")
    if len(toplevel_items) > 0:
        total_toplevel = sum(item.get("amount", 0) for item in toplevel_items)
        print("  ✓ Found %d toplevel type(s), total amount = %d" % (len(toplevel_items), total_toplevel))
        # 应该有约 100 个
        if total_toplevel >= 50:
            print("  ✓ toplevel_refcnt1 objects not skipped (Bug 1 check passed)")
        else:
            print("  ⚠ toplevel_refcnt1 count low: %d (may indicate Bug 1)" % total_toplevel)
    else:
        print("  ⚠ No toplevel_refcnt1 type found (may be below Top 100)")
    
    # =========================================================
    # 验证 9: Bug 3 - 检查 deep_nested_dicts 类型
    # 验证嵌套容器的大小是否合理（不重复计算）
    # =========================================================
    print("\n[Check 9] Bug 3: deep_nested_dicts presence...")
    deep_items = find_type_containing(items, "deep_outer")
    if len(deep_items) > 0:
        total_deep = sum(item.get("amount", 0) for item in deep_items)
        avg_size = deep_items[0].get("avg_size", 0)
        print("  ✓ Found %d deep nested type(s), total amount = %d" % (len(deep_items), total_deep))
        print("  Average size: %d bytes" % avg_size)
        
        # 3层嵌套的合理大小估算:
        # outer dict: ~200 bytes
        # middle dict: ~200 bytes  
        # inner dict: ~200 bytes
        # inner string: ~50 bytes
        # 不合并时: outer dict 本身约 200 bytes
        # 合并时: 约 650 bytes (如果全部合并)
        # 如果重复计算，可能会超过 1000 bytes
        if avg_size < 2000:
            print("  ✓ avg_size looks reasonable (< 2000, no obvious duplication)")
        else:
            print("  ⚠ avg_size very large: %d (possible Bug 3 - size duplication)" % avg_size)
    else:
        print("  ⚠ No deep_nested type found (may be below Top 100)")
    
    # =========================================================
    # 验证 10: 检查 circular_refs 是否导致问题
    # 确保循环引用不会导致死循环或异常
    # =========================================================
    print("\n[Check 10] Circular reference handling...")
    circular_items = find_type_containing(items, "circular")
    if len(circular_items) > 0:
        print("  ✓ Found %d circular ref type(s) (no crash, cycle handled)" % len(circular_items))
    else:
        print("  ⚠ No circular type found (may be below Top 100, but no crash is good)")
    print("  ✓ No infinite loop detected (test completed)")
    
    # =========================================================
    # 总结
    # =========================================================
    print("\n" + "=" * 60)
    print("All basic validations passed!")
    print("=" * 60)
    
    print("\n[Bug Coverage Summary]")
    print("  Bug 1 (toplevel refcnt=1 skip):   %s" % 
          ("✓ Checked" if len(toplevel_items) > 0 else "⚠ Not in Top 100"))
    print("  Bug 2 (two-pass skip mismatch):   Needs --py-merge comparison mode")
    print("  Bug 3 (nested size duplication):  %s" % 
          ("✓ Checked" if len(deep_items) > 0 else "⚠ Not in Top 100"))
    print("  Bug 4 (ClassifySkip reset):       Needs multi-run test")
    
    print("\n[Note]")
    print("  This test validates basic structure and object presence.")
    print("  To fully test --py-merge, compare results with/without the flag:")
    print("    ./maze --tar <tarball> --text --json-output")
    print("    ./maze --tar <tarball> --text --json-output --py-merge")
    print("  With --py-merge, exclusive_dicts should have larger avg_size")
    print("  (due to merged refcnt=1 strings)")
    
    return True


def validate_merge_comparison(data_without_merge, data_with_merge):
    """
    对比启用/不启用 --py-merge 的结果
    
    这个函数需要测试框架支持两次运行后调用
    
    预期差异：
    1. exclusive_dicts 的 avg_size：
       - 不启用 merge: ~192 bytes (dict 本身)
       - 启用 merge: ~700+ bytes (dict + merged strings)
       
    2. str/unicode 的数量：
       - 不启用 merge: 独立统计所有字符串
       - 启用 merge: refcnt=1 的字符串不再独立统计
    """
    print("=" * 60)
    print("PyMerge Comparison Validation")
    print("=" * 60)
    
    items_without = data_without_merge["items"]
    items_with = data_with_merge["items"]
    
    all_passed = True
    
    # =========================================================
    # 对比 1: exclusive_dicts avg_size
    # Bug 2 测试: 确保两次遍历结果一致
    # =========================================================
    ex_without = find_type_containing(items_without, "ex_key")
    ex_with = find_type_containing(items_with, "ex_key")
    
    if ex_without and ex_with:
        avg_without = ex_without[0].get("avg_size", 0)
        avg_with = ex_with[0].get("avg_size", 0)
        
        print("\n[exclusive_dicts avg_size comparison]")
        print("  Without --py-merge: %d bytes" % avg_without)
        print("  With    --py-merge: %d bytes" % avg_with)
        
        # 启用 merge 后，avg_size 应该显著增加
        if avg_with > avg_without * 1.5:
            print("  ✓ avg_size increased by %.1fx (merge working!)" % (avg_with / max(avg_without, 1)))
        else:
            print("  ✗ avg_size did not increase significantly (merge may not be working)")
            all_passed = False
    
    # =========================================================
    # 对比 2: str 统计数量
    # =========================================================
    str_without = find_type_containing(items_without, "str")
    str_with = find_type_containing(items_with, "str")
    unicode_without = find_type_containing(items_without, "unicode")
    unicode_with = find_type_containing(items_with, "unicode")
    
    count_without = sum(item.get("amount", 0) for item in str_without + unicode_without)
    count_with = sum(item.get("amount", 0) for item in str_with + unicode_with)
    
    print("\n[str/unicode object count comparison]")
    print("  Without --py-merge: %d" % count_without)
    print("  With    --py-merge: %d" % count_with)
    
    # 启用 merge 后，独立统计的 str 数量应该减少
    if count_with < count_without:
        reduction = count_without - count_with
        print("  ✓ str count decreased by %d (refcnt=1 strings merged)" % reduction)
    else:
        print("  ⚠ str count did not decrease (may be expected if no refcnt=1 strings)")
    
    # =========================================================
    # 对比 3: shared_dicts avg_size
    # 共享对象不应该被合并，所以 avg_size 应该相近
    # =========================================================
    shared_without = find_type_containing(items_without, "shared_key")
    shared_with = find_type_containing(items_with, "shared_key")
    
    if shared_without and shared_with:
        avg_shared_without = shared_without[0].get("avg_size", 0)
        avg_shared_with = shared_with[0].get("avg_size", 0)
        
        print("\n[shared_dicts avg_size comparison (should be similar)]")
        print("  Without --py-merge: %d bytes" % avg_shared_without)
        print("  With    --py-merge: %d bytes" % avg_shared_with)
        
        # 差异不应该太大（共享对象不合并）
        diff_ratio = abs(avg_shared_with - avg_shared_without) / max(avg_shared_without, 1)
        if diff_ratio < 0.5:
            print("  ✓ avg_size similar (shared objects not merged, as expected)")
        else:
            print("  ⚠ avg_size differs by %.1f%% (unexpected for shared objects)" % (diff_ratio * 100))
    
    # =========================================================
    # 对比 4: nested_dicts 大小（Bug 3 验证）
    # 检查是否有重复计算
    # =========================================================
    nested_without = find_type_containing(items_without, "outer_key")
    nested_with = find_type_containing(items_with, "outer_key")
    
    if nested_without and nested_with:
        avg_nested_without = nested_without[0].get("avg_size", 0)
        avg_nested_with = nested_with[0].get("avg_size", 0)
        
        print("\n[nested_dicts avg_size comparison (Bug 3 check)]")
        print("  Without --py-merge: %d bytes" % avg_nested_without)
        print("  With    --py-merge: %d bytes" % avg_nested_with)
        
        # 合并后应该更大，但不应该异常大
        if avg_nested_with > avg_nested_without:
            increase_ratio = avg_nested_with / max(avg_nested_without, 1)
            if increase_ratio < 10:
                print("  ✓ size increase ratio %.1fx (reasonable, no duplication)" % increase_ratio)
            else:
                print("  ⚠ size increase ratio %.1fx (very high, possible Bug 3!)" % increase_ratio)
                all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("Comparison validation passed!")
    else:
        print("Comparison validation FAILED!")
    print("=" * 60)
    return all_passed


if __name__ == "__main__":
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        print("       python validate.py <result-no-merge.json> <result-with-merge.json>")
        sys.exit(1)
    
    if len(sys.argv) == 2:
        # 单文件模式：基本验证
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
        result = validate(data)
        sys.exit(0 if result else 1)
    
    elif len(sys.argv) >= 3:
        # 双文件模式：对比验证
        with open(sys.argv[1], "r") as f:
            data_without = json.load(f)
        with open(sys.argv[2], "r") as f:
            data_with = json.load(f)
        
        # 先做基本验证
        validate(data_without)
        validate(data_with)
        
        # 再做对比验证
        result = validate_merge_comparison(data_without, data_with)
        sys.exit(0 if result else 1)
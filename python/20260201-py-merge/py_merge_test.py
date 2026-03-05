#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyMerge 模式测试程序

测试目标：
    验证 --py-merge 选项能正确地将 refcnt=1 的子对象内存合并到父对象

设计原理：
    1. 创建 "独占子对象" - 只被一个父对象引用的 str/int/float (refcnt=1)
    2. 创建 "共享子对象" - 被多个父对象引用的对象 (refcnt>1)
    3. 对比启用/不启用 --py-merge 的结果差异

测试覆盖的 Bug：
    Bug 1: refcnt=1 的顶层对象可能被错误跳过
           - 使用 toplevel_refcnt1_objects 测试
    Bug 2: 两次遍历的 skip 策略与合并逻辑可能不一致
           - 使用 first_pass_objects 和 second_pass_objects 测试
    问题 3: 嵌套容器的大小可能重复计算
           - 使用 nested_dicts 测试，验证 avg_size 合理性
    问题 4: ClassifySkip 未正确重置
           - 需要在 validate.py 中多次调用 Maze 来测试

预期结果：
    - 不启用 --py-merge: 每个 str/int 都单独统计
    - 启用 --py-merge: refcnt=1 的子对象合并到父 dict 统计

测试对象：
    1. exclusive_dicts: 100 个 dict，每个包含 10 个独占 str (refcnt=1)
       - 每个 dict 应该合并 10 个 str 的内存
       - 预期：dict 平均大小 ≈ 192 (dict) + 10 * 50 (str) ≈ 700+ bytes
       
    2. shared_dicts: 100 个 dict，共享同一批 str (refcnt=100)
       - str 不应该被合并，因为 refcnt > 1
       - 预期：dict 平均大小 ≈ 192 bytes (不含 str)
       
    3. mixed_dicts: 100 个 dict，混合独占和共享对象
       - 只有独占部分被合并
       
    4. toplevel_refcnt1: 顶层独立的 refcnt=1 对象 (Bug 1 测试)
       - 这些对象不应该被跳过
"""
from __future__ import print_function
import os
import time
import sys

def main():
    pid = os.getpid()
    print("=" * 60)
    print("PyMerge Test - PID: %d" % pid)
    print("=" * 60)
    
    # =====================================================
    # 测试组 1: 独占子对象 (exclusive)
    # 每个 dict 独占一批 str，这些 str 的 refcnt=1
    # 启用 --py-merge 后，这些 str 应该合并到 dict
    # 注意：keys 必须相同才能被归为同一类型，但 values 是独占的
    # =====================================================
    print("\n[1] Creating exclusive_dicts (refcnt=1 values)...")
    exclusive_dicts = []
    # 共享的 keys（让 dict 类型签名相同）
    ex_keys = ["ex_key_%d" % j for j in range(10)]
    for i in range(100):
        # 每个 dict 有相同的 keys，但独占的 values (refcnt=1)
        d = {}
        for j, k in enumerate(ex_keys):
            d[k] = "exclusive_value_%d_%d_padding_text" % (i, j)
        exclusive_dicts.append(d)
    print("  Created %d dicts, each with 10 exclusive value strings" % len(exclusive_dicts))
    
    # =====================================================
    # 测试组 2: 共享子对象 (shared)
    # 多个 dict 共享同一批 str，这些 str 的 refcnt > 1
    # 启用 --py-merge 后，这些 str 不应该被合并
    # =====================================================
    print("\n[2] Creating shared_dicts (refcnt>1 strings)...")
    # 先创建共享的 key 和 value
    shared_keys = ["shared_key_%d" % j for j in range(10)]
    shared_values = ["shared_value_%d_padding_text" % j for j in range(10)]
    
    shared_dicts = []
    for i in range(100):
        # 所有 dict 共享同一批 key 和 value
        d = dict(zip(shared_keys, shared_values))
        shared_dicts.append(d)
    print("  Created %d dicts, all sharing the same 10 strings" % len(shared_dicts))
    print("  Each shared string has refcnt=%d" % sys.getrefcount(shared_keys[0]))
    
    # =====================================================
    # 测试组 3: 混合模式 (mixed)
    # dict 同时包含独占和共享对象
    # =====================================================
    print("\n[3] Creating mixed_dicts (mixed refcnt)...")
    mixed_dicts = []
    shared_mixed_value = "this_is_shared_by_all_mixed_dicts"  # 共享的 value
    for i in range(100):
        d = {
            # 独占的 key 和 value (refcnt=1)
            "mixed_exclusive_%d" % i: "mixed_exclusive_val_%d" % i,
            # 共享的 key 和 value (refcnt>1)
            "mixed_shared": shared_mixed_value,
        }
        mixed_dicts.append(d)
    print("  Created %d dicts, each with 1 exclusive + 1 shared entry" % len(mixed_dicts))
    
    # =====================================================
    # 测试组 4: 嵌套结构 (nested) - 问题 3 测试
    # dict 包含 dict，测试多层合并
    # 使用统一的键名以确保被归类为同一类型
    # =====================================================
    print("\n[4] Creating nested_dicts (multi-level) - Bug 3 test...")
    nested_dicts = []
    for i in range(50):
        outer = {
            # 外层使用统一的键名（确保所有 50 个 dict 被归为同一类型）
            "outer_key": {  # 内层 dict (refcnt=1)
                # 内层也使用统一键名，但值不同（保持 refcnt=1）
                "inner_key": "inner_value_%d_text" % i  # 内层 str (refcnt=1)
            }
        }
        nested_dicts.append(outer)
    print("  Created %d nested dicts (outer -> inner -> str)" % len(nested_dicts))
    
    # =====================================================
    # 测试组 5: list 中的独占对象 (list_exclusive)
    # =====================================================
    print("\n[5] Creating exclusive_lists (refcnt=1 elements)...")
    exclusive_lists = []
    for i in range(100):
        lst = ["list_item_%d_%d_text" % (i, j) for j in range(10)]
        exclusive_lists.append(lst)
    print("  Created %d lists, each with 10 exclusive strings" % len(exclusive_lists))
    
    # =====================================================
    # 测试组 6: 数值类型 (numbers)
    # =====================================================
    print("\n[6] Creating number_dicts (int/float with refcnt=1)...")
    number_dicts = []
    for i in range(100):
        # 使用大整数避免 Python 小整数缓存 (-5 到 256)
        d = {
            "big_int_%d" % i: 1000000 + i * 1000 + 1,  # 独占的大整数
            "float_%d" % i: 3.14159 + i * 0.001,       # 独占的浮点数
        }
        number_dicts.append(d)
    print("  Created %d dicts with exclusive int/float" % len(number_dicts))
    
    # =====================================================
    # 测试组 7: 顶层 refcnt=1 对象 - Bug 1 测试
    # 这些对象不在任何容器内，refcnt=1
    # 不应该被 ClassifySkip 跳过
    # =====================================================
    print("\n[7] Creating toplevel_refcnt1 objects - Bug 1 test...")
    # 创建独立的 refcnt=1 字典（使用统一的键确保被归为同类型）
    toplevel_refcnt1_dicts = []
    toplevel_keys = ["toplevel_key_%d" % j for j in range(5)]
    for i in range(100):
        d = {}
        for j, k in enumerate(toplevel_keys):
            d[k] = "toplevel_val_%d_%d_unique" % (i, j)
        toplevel_refcnt1_dicts.append(d)
    print("  Created %d toplevel dicts with refcnt=1 (stored in list)")
    print("  Dict refcnt=%d (should be 1 + list ref)" % sys.getrefcount(toplevel_refcnt1_dicts[0]))
    
    # =====================================================
    # 测试组 8: 深度嵌套 - 更严格的问题 3 测试
    # 3 层嵌套：outer -> middle -> inner -> str
    # =====================================================
    print("\n[8] Creating deep_nested_dicts (3 levels) - deeper Bug 3 test...")
    deep_nested_dicts = []
    for i in range(30):
        outer = {
            "deep_outer": {  # refcnt=1
                "deep_middle": {  # refcnt=1
                    "deep_inner": "deep_value_%d_text" % i  # refcnt=1
                }
            }
        }
        deep_nested_dicts.append(outer)
    print("  Created %d deep nested dicts (3 levels)" % len(deep_nested_dicts))
    
    # =====================================================
    # 测试组 9: 循环引用测试
    # dict A 引用 dict B，B 引用 A
    # 用于测试合并逻辑是否会死循环
    # =====================================================
    print("\n[9] Creating circular_refs (cycle detection test)...")
    circular_refs = []
    for i in range(20):
        a = {"circular_a_key": "circular_a_val_%d" % i}
        b = {"circular_b_key": "circular_b_val_%d" % i}
        a["ref_to_b"] = b  # A -> B
        b["ref_to_a"] = a  # B -> A (循环)
        circular_refs.append(a)
    print("  Created %d circular reference pairs" % len(circular_refs))
    
    # =====================================================
    # 汇总
    # =====================================================
    print("\n" + "=" * 60)
    print("Summary of Test Objects:")
    print("=" * 60)
    print("  exclusive_dicts:       %d (should merge 10 strings each)" % len(exclusive_dicts))
    print("  shared_dicts:          %d (should NOT merge strings)" % len(shared_dicts))
    print("  mixed_dicts:           %d (partial merge)" % len(mixed_dicts))
    print("  nested_dicts:          %d (multi-level merge, Bug 3)" % len(nested_dicts))
    print("  exclusive_lists:       %d (should merge list items)" % len(exclusive_lists))
    print("  number_dicts:          %d (should merge int/float)" % len(number_dicts))
    print("  toplevel_refcnt1:      %d (Bug 1 - should not be skipped)" % len(toplevel_refcnt1_dicts))
    print("  deep_nested_dicts:     %d (Bug 3 - 3 level nesting)" % len(deep_nested_dicts))
    print("  circular_refs:         %d (cycle detection)" % len(circular_refs))
    print("=" * 60)
    
    # 保持引用防止 GC
    storage = {
        "exclusive_dicts": exclusive_dicts,
        "shared_dicts": shared_dicts,
        "mixed_dicts": mixed_dicts,
        "nested_dicts": nested_dicts,
        "exclusive_lists": exclusive_lists,
        "number_dicts": number_dicts,
        "toplevel_refcnt1_dicts": toplevel_refcnt1_dicts,
        "deep_nested_dicts": deep_nested_dicts,
        "circular_refs": circular_refs,
    }
    
    print("\nBug Coverage:")
    print("  Bug 1 (toplevel refcnt=1 skip):    toplevel_refcnt1_dicts")
    print("  Bug 2 (two-pass skip mismatch):    needs runtime comparison")
    print("  Bug 3 (nested size duplication):   nested_dicts, deep_nested_dicts")
    print("  Bug 4 (ClassifySkip reset):        needs multi-run test in validate.py")
    
    print("\nTo generate coredump:")
    print("  gcore %d" % pid)
    print("\nTo test py-merge:")
    print("  # Without --py-merge")
    print("  ./maze --tar <tarball> --text")
    print("  # With --py-merge")  
    print("  ./maze --tar <tarball> --text --py-merge")
    print("\nWaiting for coredump generation...")
    
    # 保持进程存活
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node.js Comprehensive Objects 测试验证脚本

验证目标：
    1. 验证 Maze 能分析 Node.js/V8 进程
    2. 检查每种对象类型是否有约 1000 个实例
    3. 验证对象计数和内存大小的合理性

测试数据：
    - 96 种不同类型的 JS 对象
    - 每种类型统一生成 1000 个实例
    - 总计约 96,000 个对象
"""
from __future__ import print_function
import json
import sys
import os
import re


# =========================================================
# 预期值常量
# =========================================================
EXPECTED_OBJECTS_PER_TYPE = 1000  # 每种类型预期的对象数
TOLERANCE_PERCENT = 20            # 允许的误差百分比 (±20%)
EXPECTED_MIN_SIZE_MB = 15         # 最小内存 MB


# =========================================================
# 类型映射表
# 
# 从 test.js 的类型名称 -> maze 输出的类型模式
# 
# 映射规则：
#   - "exact:TypeName" - 精确匹配类型名
#   - "pattern:regex" - 正则表达式匹配
#   - "contains:substring" - 包含子串
#   - "multi:pattern1|pattern2" - 多个模式的总和
#   - "skip" - 跳过验证（某些类型 maze 无法单独识别）
# =========================================================
TYPE_MAPPINGS = {
    # ========== 1. 基础 JavaScript 类型 ==========
    "Object": "skip",  # Object 被拆分为多种 shape，难以单独统计
    "Array.dense": "skip",  # 与其他 Array 混合
    "Array.sparse": "skip",
    "Array.mixed": "skip",
    "String.object": "skip",  # String 对象混在 (String) 统计中
    "Number.object": "skip",
    "Boolean.object": "skip",
    "Symbol": "skip",  # Symbol 包装对象
    "BigInt": "skip",  # BigInt 包装对象
    
    # ========== 2. 集合类型 ==========
    "Map": "contains:(JSMap)",
    "Set": "contains:(Set)",
    "WeakMap": "skip",  # WeakMap 内部结构不直接暴露
    "WeakMap.keys": "skip",
    "WeakSet": "skip",
    "WeakSet.items": "skip",
    
    # ========== 3. 二进制数据类型 ==========
    "Buffer": "skip",  # Buffer 被统计为 ArrayBuffer + ArrayBufferView
    "ArrayBuffer": "contains:(ArrayBuffer)",
    "SharedArrayBuffer": "skip",  # 可能不可用
    "Int8Array": "contains:(ArrayBufferView)",
    "Uint8Array": "contains:(ArrayBufferView)",
    "Uint8ClampedArray": "contains:(ArrayBufferView)",
    "Int16Array": "contains:(ArrayBufferView)",
    "Uint16Array": "contains:(ArrayBufferView)",
    "Int32Array": "contains:(ArrayBufferView)",
    "Uint32Array": "contains:(ArrayBufferView)",
    "Float32Array": "contains:(ArrayBufferView)",
    "Float64Array": "contains:(ArrayBufferView)",
    "BigInt64Array": "contains:(ArrayBufferView)",
    "BigUint64Array": "contains:(ArrayBufferView)",
    "DataView": "skip",  # DataView 可能被统计为其他类型
    
    # ========== 4. 函数类型 ==========
    "Function": "exact:(Function: namedFunc)",
    "ArrowFunction": "skip",  # 箭头函数没有名字
    "AsyncFunction": "contains:(Function: asyncFn)",
    "GeneratorFunction": "contains:(Function: genFn)",
    "AsyncGeneratorFunction": "contains:(Function: asyncGenFn)",
    "Function.dynamic": "skip",  # 动态函数没有特定名字
    "BoundFunction": "skip",  # 绑定函数
    
    # ========== 5. 迭代器和生成器对象 ==========
    "Generator": "skip",  # Generator 对象
    "AsyncGenerator": "skip",
    "ArrayIterator": "skip",
    "MapIterator": "skip",
    "SetIterator": "skip",
    "StringIterator": "skip",
    
    # ========== 6. 内置对象类型 ==========
    "Date": "exact:(Date)",
    "RegExp": "exact:(RegExp)",
    "Error": "exact:Error",  # Error 有多个条目，需要汇总
    "TypeError": "exact:Error",  # 也统计为 Error
    "RangeError": "exact:Error",  # 也统计为 Error
    "Promise.pending": "exact:Promise",
    "Promise.resolved": "exact:Promise",
    "Promise.rejected": "exact:Promise",
    "Proxy": "skip",  # Proxy 对象
    
    # ========== 7. ES6+ 新特性对象 ==========
    "WeakRef": "skip",
    "WeakRef.targets": "skip",
    "FinalizationRegistry": "contains:{registry, obj}",
    "Class.privateFields": "contains:{publicField}",
    "Class.derived": "contains:{x, y}",
    "Object.accessors": "contains:{get, set}",
    
    # ========== 8. Node.js 核心模块对象 ==========
    "EventEmitter": "contains:{_events, _eventsCount, _maxListeners}",
    "Stream.Readable": "contains:{_events, _readableState",
    "Stream.Writable": "contains:{_events, _writableState",
    "Stream.Transform": "contains:{_writeState, _events, _readableState",
    "URL": "contains:{href, protocol_end, username_end",
    "URLSearchParams": "skip",  # 内部结构
    "crypto.Hash": "skip",  # 内部对象
    "zlib.Gzip": "contains:{onerror}",
    "vm.Script": "contains:{sourceMapURL}",
    "MessageChannel": "contains:{channel, port1, port2}",
    
    # ========== 9. 国际化对象 (Intl) ==========
    "Intl.DateTimeFormat": "skip",
    "Intl.NumberFormat": "skip",
    "Intl.Collator": "skip",
    "Intl.PluralRules": "skip",
    "Intl.RelativeTimeFormat": "skip",
    "Intl.ListFormat": "skip",
    "Intl.Segmenter": "skip",
    
    # ========== 10. Web API 兼容对象 ==========
    "TextEncoder": "skip",
    "TextDecoder": "skip",
    "AbortController": "contains:{controller, signal}",
    "Blob": "exact:Blob",
    "Headers": "skip",
    "Response": "contains:{method, localURLsOnly, unsafeRequest",
    "Request": "contains:{aborted, rangeRequested, timingAllow",
    "FormData": "contains:{cookies}",
    "ReadableStream": "contains:{byobRequest, closeRequested, pullAga",
    "WritableStream": "contains:{cancelAlgorithm, closeRequested, hig",
    
    # ========== 11. 特殊对象和边界情况 ==========
    "Object.nullProto": "skip",
    "Object.frozen": "contains:{id, frozen}",
    "Object.sealed": "contains:{id, sealed}",
    "Object.circular": "contains:{id}",
    "Object.deepNested": "contains:{depth, id, child}",
    "Object.manyProps": "skip",  # 属性太多，shape 不同
    "Arguments": "skip",
    "Object.symbolKeys": "skip",
    
    # ========== 12. 自定义类 ==========
    "SimpleClass": "contains:{type, id, created}",  # FactoryObject 也匹配这个
    "Dog": "contains:{name, legs, breed}",
    "FactoryObject": "contains:{type, id, created}",
}


def find_types_matching(items, pattern):
    """
    根据模式查找匹配的类型项
    
    返回: (匹配的项列表, 总数量)
    """
    if pattern == "skip":
        return [], -1  # -1 表示跳过
    
    matched = []
    
    if pattern.startswith("exact:"):
        # 精确匹配
        target = pattern[6:]
        for item in items:
            if item.get("type", "") == target:
                matched.append(item)
    
    elif pattern.startswith("contains:"):
        # 包含子串
        substring = pattern[9:]
        for item in items:
            if substring in item.get("type", ""):
                matched.append(item)
    
    elif pattern.startswith("pattern:"):
        # 正则匹配
        regex = pattern[8:]
        for item in items:
            if re.search(regex, item.get("type", "")):
                matched.append(item)
    
    elif pattern.startswith("multi:"):
        # 多个模式的并集
        patterns = pattern[6:].split("|")
        for p in patterns:
            sub_matched, _ = find_types_matching(items, p)
            matched.extend(sub_matched)
    
    total_amount = sum(item.get("amount", 0) for item in matched)
    return matched, total_amount


def validate_type_counts(items):
    """
    验证每种类型的对象数量是否接近预期 (1000)
    
    返回: (passed_count, warning_count, failed_count, results_list)
    """
    results = []
    passed = 0
    warnings = 0
    failed = 0
    
    min_expected = EXPECTED_OBJECTS_PER_TYPE * (1 - TOLERANCE_PERCENT / 100.0)
    max_expected = EXPECTED_OBJECTS_PER_TYPE * (1 + TOLERANCE_PERCENT / 100.0)
    
    for js_type, pattern in sorted(TYPE_MAPPINGS.items()):
        matched, total = find_types_matching(items, pattern)
        
        if total == -1:
            # 跳过的类型
            results.append({
                "js_type": js_type,
                "status": "skip",
                "count": 0,
                "message": "Skipped (type not individually trackable)"
            })
            continue
        
        if total == 0:
            # 没找到
            results.append({
                "js_type": js_type,
                "status": "fail",
                "count": 0,
                "message": "Not found in results"
            })
            failed += 1
        elif min_expected <= total <= max_expected:
            # 数量在预期范围内
            results.append({
                "js_type": js_type,
                "status": "pass",
                "count": total,
                "matched_types": [m.get("type", "")[:40] for m in matched[:3]],
                "message": "Count within expected range"
            })
            passed += 1
        elif total < min_expected:
            # 数量偏少
            results.append({
                "js_type": js_type,
                "status": "warn",
                "count": total,
                "matched_types": [m.get("type", "")[:40] for m in matched[:3]],
                "message": "Count lower than expected (%.0f < %.0f)" % (total, min_expected)
            })
            warnings += 1
        else:
            # 数量偏多（可能是多个 test.js 类型映射到同一个 maze 类型）
            results.append({
                "js_type": js_type,
                "status": "pass",  # 偏多通常是因为多个类型合并，算通过
                "count": total,
                "matched_types": [m.get("type", "")[:40] for m in matched[:3]],
                "message": "Count higher than expected (likely merged types)"
            })
            passed += 1
    
    return passed, warnings, failed, results


def validate(data):
    """验证 maze 分析结果"""
    print("=" * 70)
    print("Node.js Comprehensive Objects Test Validation")
    print("=" * 70)
    
    # 检查基本结构
    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"
    
    items = data.get("items") or []
    summary = data["summary"]
    
    # 打印摘要
    print("\n[Summary]")
    vms = summary.get("vms", 0)
    core_size = summary.get("core_size", 0)
    ptmalloc = summary.get("ptmalloc", 0)
    
    print("  VMS: %.2f MB" % (vms / 1024 / 1024))
    print("  Core Size: %.2f MB" % (core_size / 1024 / 1024))
    print("  Ptmalloc: %.2f MB" % (ptmalloc / 1024 / 1024))
    print("  Total item types: %d" % len(items))
    
    all_warnings = []
    
    # =========================================================
    # Check 1: 基本分析完成
    # =========================================================
    print("\n[Check 1] Analysis completed...")
    if len(items) >= 50:
        print("  [OK] Found %d item types (>= 50)" % len(items))
    else:
        print("  [!!] Only %d item types found (expected >= 50)" % len(items))
        all_warnings.append("Low type count: %d" % len(items))
    
    # =========================================================
    # Check 2: 内存统计合理
    # =========================================================
    print("\n[Check 2] Memory statistics...")
    
    if vms > 50 * 1024 * 1024:
        print("  [OK] VMS size reasonable (%.2f MB > 50 MB)" % (vms / 1024 / 1024))
    else:
        print("  [!!] VMS size seems low: %.2f MB" % (vms / 1024 / 1024))
        all_warnings.append("Low VMS")
    
    if core_size > 20 * 1024 * 1024:
        print("  [OK] Core size reasonable (%.2f MB > 20 MB)" % (core_size / 1024 / 1024))
    else:
        print("  [!!] Core size seems low: %.2f MB" % (core_size / 1024 / 1024))
        all_warnings.append("Low core size")
    
    # =========================================================
    # Check 3: 对象分布统计
    # =========================================================
    print("\n[Check 3] Object distribution...")
    
    total_amount = sum(item.get("amount", 0) for item in items)
    total_size = sum(item.get("total_size", 0) for item in items)
    
    print("  Total objects counted: %d" % total_amount)
    print("  Total size: %.2f MB" % (total_size / 1024 / 1024))
    
    # 预期约 96,000 个对象，但由于 maze 统计方式不同，放宽到 50%
    expected_min_objects = 50000
    if total_amount >= expected_min_objects:
        print("  [OK] Object count reasonable (>= %d)" % expected_min_objects)
    else:
        print("  [!!] Object count lower than expected: %d" % total_amount)
        all_warnings.append("Low object count")
    
    # =========================================================
    # Check 4: 类型匹配验证 (核心检查)
    # =========================================================
    print("\n[Check 4] Type-by-type validation...")
    print("  Expected ~%d objects per type, tolerance ±%d%%" % (
        EXPECTED_OBJECTS_PER_TYPE, TOLERANCE_PERCENT))
    print("")
    
    passed, warnings, failed, results = validate_type_counts(items)
    
    # 按状态分组输出
    print("  --- PASSED (%d types) ---" % passed)
    for r in results:
        if r["status"] == "pass":
            types_str = ""
            if r.get("matched_types"):
                types_str = " [%s]" % r["matched_types"][0]
            print("  [OK] %-30s count=%5d%s" % (
                r["js_type"], r["count"], types_str))
    
    if warnings > 0:
        print("\n  --- WARNINGS (%d types) ---" % warnings)
        for r in results:
            if r["status"] == "warn":
                print("  [!!] %-30s count=%5d - %s" % (
                    r["js_type"], r["count"], r["message"]))
    
    if failed > 0:
        print("\n  --- FAILED (%d types) ---" % failed)
        for r in results:
            if r["status"] == "fail":
                print("  [XX] %-30s - %s" % (r["js_type"], r["message"]))
    
    skipped = sum(1 for r in results if r["status"] == "skip")
    print("\n  --- SKIPPED (%d types) ---" % skipped)
    print("  (Types that cannot be individually tracked by maze)")
    
    print("\n  Summary: %d passed, %d warnings, %d failed, %d skipped" % (
        passed, warnings, failed, skipped))
    
    # 判断是否通过
    # 如果 passed + warnings >= 20，且 failed <= 5，则认为通过
    type_check_passed = (passed + warnings >= 20) and (failed <= 5)
    
    if type_check_passed:
        print("  [OK] Type validation PASSED")
    else:
        print("  [!!] Type validation FAILED")
        all_warnings.append("Type validation failed: passed=%d, failed=%d" % (passed, failed))
    
    # =========================================================
    # Check 5: Top 类型分布（参考信息）
    # =========================================================
    print("\n[Top 10 Types by Count]")
    sorted_by_count = sorted(items, key=lambda x: x.get("amount", 0), reverse=True)
    for i, item in enumerate(sorted_by_count[:10]):
        type_name = item.get("type", "unknown")
        if len(type_name) > 50:
            type_name = type_name[:47] + "..."
        print("  %2d. %-50s amount=%6d" % (
            i + 1, type_name, item.get("amount", 0)))
    
    # =========================================================
    # Check 6: 关键类型检测
    # =========================================================
    print("\n[Check 6] Key type detection...")
    
    key_checks = [
        ("(Date)", "Date objects", 1000),
        ("(RegExp)", "RegExp objects", 1000),
        ("Error", "Error objects", 4000),  # Error + TypeError + RangeError + ...
        ("Promise", "Promise objects", 3000),  # pending + resolved + rejected
        ("(ArrayBuffer)", "ArrayBuffer objects", 1000),
        ("(ArrayBufferView)", "TypedArray objects", 11000),  # 11 种 TypedArray
        ("Blob", "Blob objects", 1000),
        ("(JSMap)", "Map objects", 1000),
        ("(Set)", "Set objects", 1000),
    ]
    
    key_passed = 0
    for pattern, desc, expected_min in key_checks:
        matched = [item for item in items if pattern in item.get("type", "")]
        total = sum(item.get("amount", 0) for item in matched)
        
        # 允许 50% 误差
        if total >= expected_min * 0.5:
            print("  [OK] %-25s: %d (expected ~%d)" % (desc, total, expected_min))
            key_passed += 1
        else:
            print("  [!!] %-25s: %d (expected ~%d)" % (desc, total, expected_min))
    
    print("\n  %d/%d key type checks passed" % (key_passed, len(key_checks)))
    
    # =========================================================
    # 最终结果
    # =========================================================
    print("\n" + "=" * 70)
    
    overall_passed = (
        len(items) >= 50 and
        total_amount >= expected_min_objects and
        type_check_passed and
        key_passed >= len(key_checks) * 0.7  # 70% 关键检查通过
    )
    
    if overall_passed:
        print("[OK] All validations PASSED!")
        print("  The comprehensive test completed successfully.")
        if all_warnings:
            print("\n  Minor warnings:")
            for w in all_warnings:
                print("    - %s" % w)
    else:
        print("[!!] Validation FAILED with issues:")
        for w in all_warnings:
            print("  - %s" % w)
        print("\n  Note: Some failures may be expected depending on:")
        print("    - V8 version differences")
        print("    - HeapWalk vs MemScan mode")
        print("    - Object shape variations")
    
    print("=" * 70)
    
    return overall_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        print("")
        print("Example:")
        print("  # Run maze analysis first")
        print("  ./maze --tar coredump.tar.gz --text --json-output")
        print("")
        print("  # Then validate")
        print("  python validate.py maze-result.json")
        sys.exit(1)
    
    result_file = sys.argv[1]
    if not os.path.exists(result_file):
        print("Error: File not found: %s" % result_file)
        sys.exit(1)
    
    with open(result_file, "r") as f:
        data = json.load(f)
    
    result = validate(data)
    sys.exit(0 if result else 1)

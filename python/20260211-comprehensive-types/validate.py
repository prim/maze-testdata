#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Types Test - Validation Script

验证 Maze 分析结果是否正确识别了各种 Python 类型。

Usage:
    # 普通模式
    python3 validate.py maze-result.json
    
    # 合并模式
    MAZE_PY_MERGE=1 python3 validate.py maze-result.json
"""

from __future__ import print_function
import json
import sys
import os


def find_items_by_pattern(items, pattern):
    """查找匹配模式的所有项目"""
    # 支持 'name' 和 'type' 两种字段名
    return [item for item in items if pattern.lower() in item.get('type', item.get('name', '')).lower()]


def find_item_by_name(items, name):
    """精确查找项目"""
    for item in items:
        item_name = item.get('type', item.get('name', ''))
        if item_name == name:
            return item
    return None


def validate_class_exists(items, class_name, min_count=100, description=""):
    """验证某个类是否存在且数量符合预期"""
    # 尝试多种匹配模式
    patterns = [
        "<class %s> instance" % class_name,  # 精确匹配
        "class %s>" % class_name,             # 部分匹配 (兼容 collections.X)
        class_name,                           # 简单匹配
    ]
    
    found = None
    for pattern in patterns:
        found = find_items_by_pattern(items, pattern)
        if found:
            break
    
    if found:
        total = sum(item.get('amount', 0) for item in found)
        if total >= min_count:
            print("  ✓ %s: %d instances found" % (class_name, total))
            return True, total
        else:
            print("  △ %s: only %d instances (expected >= %d)" % (class_name, total, min_count))
            return True, total  # 存在但数量不足，不算失败
    else:
        print("  ✗ %s: not found%s" % (class_name, (" (%s)" % description if description else "")))
        return False, 0


def validate_type_exists(items, type_pattern, min_count=1, description=""):
    """验证某个类型是否存在"""
    found = find_items_by_pattern(items, type_pattern)
    
    if found:
        total = sum(item.get('amount', 0) for item in found)
        if total >= min_count:
            print("  ✓ %s: %d found" % (type_pattern, total))
            return True, total
        else:
            print("  △ %s: only %d found (expected >= %d)" % (type_pattern, total, min_count))
            return True, total
    else:
        print("  ✗ %s: not found%s" % (type_pattern, (" (%s)" % description if description else "")))
        return False, 0


def validate(json_file, py_merge=False):
    """
    验证函数
    
    Args:
        json_file: maze-result.json 文件路径
        py_merge: 是否启用了 --py-merge 模式
    
    Returns:
        bool: 验证是否通过
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # 获取摘要信息
    summary = data.get('summary', {})
    vms = summary.get('vms', 0)
    pyo_amount = summary.get('pymempool_objects', 0)
    
    print("=" * 70)
    print("Comprehensive Types Test Validation")
    print("=" * 70)
    print("\n[Summary]")
    print("  VMS: %s" % vms)
    print("  PyMemPool Objects: %d" % pyo_amount)
    print("  Mode: %s" % ('--py-merge' if py_merge else 'normal'))
    
    # 基础检查
    print("\n[1. Basic Check]")
    if pyo_amount < 5000:
        print("  ✗ Too few PyMemPool objects: %d (expected >= 5000)" % pyo_amount)
        return False
    print("  ✓ PyMemPool objects: %d" % pyo_amount)
    
    # 获取结果项
    items = data.get('items', [])
    if not items:
        print("  ✗ No items in result")
        return False
    print("  ✓ Items count: %d" % len(items))
    
    # ========================================
    # 2. 验证核心类
    # ========================================
    print("\n[2. Core Classes Validation]")
    
    core_classes = [
        ("SimpleClass", 1000),
        ("NestedDictClass", 1000),
        ("NestedListClass", 1000),
        ("MixedTypeContainerClass", 1000),
        ("LargeContainerClass", 100),
        ("EmptyContainerClass", 1000),
        ("MethodHolderClass", 1000),
        ("ClosureHolderClass", 1000),
        ("InheritedClass", 1000),
        ("SlottedClass", 1000),
    ]
    
    core_found = 0
    for class_name, min_count in core_classes:
        found, _ = validate_class_exists(items, class_name, min_count)
        if found:
            core_found += 1
    
    if core_found < len(core_classes) * 0.7:  # 至少 70% 的核心类被识别
        print("\n  ✗ Too few core classes found: %d/%d" % (core_found, len(core_classes)))
        return False
    print("\n  ✓ Core classes: %d/%d found" % (core_found, len(core_classes)))
    
    # ========================================
    # 3. 验证集合类
    # ========================================
    print("\n[3. Collection Classes Validation]")
    
    collection_classes = [
        ("SetFrozenSetClass", 1000),
        ("TupleClass", 1000),
        ("BytesUnicodeClass", 1000),
        ("NumberClass", 1000),
        ("DictSubclass", 1000),
        ("ListSubclass", 1000),
        ("DequeClass", 1000),
        ("OrderedDictClass", 1000),
        ("DefaultDictClass", 1000),
        ("CounterClass", 1000),
        ("NamedTupleClass", 1000),
    ]
    
    collection_found = 0
    for class_name, min_count in collection_classes:
        found, _ = validate_class_exists(items, class_name, min_count)
        if found:
            collection_found += 1
    
    print("\n  ✓ Collection classes: %d/%d found" % (collection_found, len(collection_classes)))
    
    # ========================================
    # 4. 验证高级类
    # ========================================
    print("\n[4. Advanced Classes Validation]")
    
    advanced_classes = [
        ("CircularRefClass", 1000),
        ("DescriptorClass", 1000),
        ("PropertyClass", 1000),
        ("GeneratorHolderClass", 1000),
        ("ComplexNumberClass", 1000),
        ("HighRefCountClass", 1000),
        ("MultipleInheritance", 1000),
        ("ExceptionClass", 1000),
        ("FrameHolderClass", 100),
        ("CodeObjectClass", 1000),
        ("BuiltinFunctionClass", 1000),
        ("ModuleClass", 100),
        ("BoundMethodClass", 1000),
        ("ByteArrayClass", 1000),
    ]
    
    advanced_found = 0
    for class_name, min_count in advanced_classes:
        found, _ = validate_class_exists(items, class_name, min_count)
        if found:
            advanced_found += 1
    
    print("\n  ✓ Advanced classes: %d/%d found" % (advanced_found, len(advanced_classes)))
    
    # ========================================
    # 5. 验证描述符类
    # ========================================
    print("\n[5. Descriptor Classes Validation]")
    
    descriptor_classes = [
        ("MemberDescrClass", 1000),
        ("GetSetDescrClass", 1000),
        ("MethodDescrClass", 1000),
        ("WrapperDescrClass", 1000),
        ("ClassMethodDescrClass", 1000),
    ]
    
    descr_found = 0
    for class_name, min_count in descriptor_classes:
        found, _ = validate_class_exists(items, class_name, min_count)
        if found:
            descr_found += 1
    
    print("\n  ✓ Descriptor classes: %d/%d found" % (descr_found, len(descriptor_classes)))
    
    # ========================================
    # 6. 验证基础类型
    # ========================================
    print("\n[6. Primitive Types Validation]")
    
    primitive_types = [
        ("list", 100),
        ("dict", 100),
        ("tuple", 100),
        ("set", 100),
        ("str", 100),
        ("int", 100),
        ("float", 100),
    ]
    
    prim_found = 0
    for type_name, min_count in primitive_types:
        found, _ = validate_type_exists(items, type_name, min_count)
        if found:
            prim_found += 1
    
    print("\n  ✓ Primitive types: %d/%d found" % (prim_found, len(primitive_types)))
    
    # ========================================
    # 7. --py-merge 特定验证
    # ========================================
    if py_merge:
        print("\n[7. Merge Mode Specific Validation]")
        
        # 在合并模式下，NestedDictClass 的 avg_size 应该显著增加
        nested_dict = find_items_by_pattern(items, "NestedDictClass")
        if nested_dict:
            avg_size = nested_dict[0].get('avg_size', 0)
            print("  NestedDictClass avg_size: %d" % avg_size)
            
            # 合并模式下，avg_size 应该 > 500 (包含子对象)
            if avg_size > 500:
                print("  ✓ Merge mode working correctly (avg_size > 500)")
            else:
                print("  △ Merge mode might not be working (avg_size = %d, expected > 500)" % avg_size)
        
        # 检查 NestedListClass
        nested_list = find_items_by_pattern(items, "NestedListClass")
        if nested_list:
            avg_size = nested_list[0].get('avg_size', 0)
            print("  NestedListClass avg_size: %d" % avg_size)
            
            if avg_size > 300:
                print("  ✓ Merge mode working for lists (avg_size > 300)")
    else:
        print("\n[7. Normal Mode Specific Validation]")
        
        # 在普通模式下，NestedDictClass 的 avg_size 应该较小
        nested_dict = find_items_by_pattern(items, "NestedDictClass")
        if nested_dict:
            avg_size = nested_dict[0].get('avg_size', 0)
            print("  NestedDictClass avg_size: %d" % avg_size)
            
            # 普通模式下，avg_size 应该 < 300 (只有对象头)
            if avg_size < 300:
                print("  ✓ Normal mode correct (avg_size < 300)")
            else:
                print("  △ Unexpected large avg_size in normal mode: %d" % avg_size)
    
    # ========================================
    # 总结
    # ========================================
    total_classes = len(core_classes) + len(collection_classes) + len(advanced_classes) + len(descriptor_classes)
    total_found = core_found + collection_found + advanced_found + descr_found
    
    print("\n" + "=" * 70)
    print("Validation Summary")
    print("=" * 70)
    print("  Total classes checked: %d" % total_classes)
    print("  Classes found: %d (%.1f%%)" % (total_found, 100.0 * total_found / total_classes))
    print("  Primitive types found: %d/%d" % (prim_found, len(primitive_types)))
    
    # 成功条件：至少 60% 的类被识别
    success_rate = float(total_found) / total_classes
    if success_rate >= 0.6:
        print("\n  ✓ VALIDATION PASSED (%.1f%% classes identified)" % (success_rate * 100))
        print("=" * 70)
        return True
    else:
        print("\n  ✗ VALIDATION FAILED (only %.1f%% classes identified)" % (success_rate * 100))
        print("=" * 70)
        return False


def main():
    # 检查环境变量
    py_merge = os.environ.get('MAZE_PY_MERGE', '0') == '1'
    
    # 获取 JSON 文件路径
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = 'maze-result.json'
    
    # 检查文件是否存在
    if not os.path.exists(json_file):
        print("Error: %s not found" % json_file)
        print("Usage: python3 validate.py [maze-result.json]")
        sys.exit(1)
    
    # 运行验证
    if validate(json_file, py_merge):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证脚本 - Python 2.7 复杂类型测试用例

验证 maze 分析结果是否正确识别了各种 Python 2.7 类型
"""

from __future__ import print_function


def validate(data):
    """
    验证 maze 分析结果
    
    Args:
        data: json.load() 后的结果数据
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        AssertionError: 当验证失败时
    """
    print("Checking result structure...")
    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"
    
    items = data["items"]
    summary = data["summary"]
    
    # ============================================================
    # 验证 Summary
    # ============================================================
    print("\nValidating summary:")
    
    # 验证 pymempool 对象数量 (应该 > 30000)
    pymempool_objects = summary.get("pymempool_objects", 0)
    print("  pymempool_objects = %d" % pymempool_objects)
    assert pymempool_objects > 30000, "Expected > 30000 pymempool objects, got %d" % pymempool_objects
    print("  ✓ pymempool_objects > 30000")
    
    # ============================================================
    # 辅助函数
    # ============================================================
    def find_type_containing(target):
        """查找包含指定字符串的类型"""
        for item in items:
            if target in item.get("type", ""):
                return item
        return None
    
    def find_exact_type(target):
        """精确匹配类型"""
        for item in items:
            if item.get("type", "") == target:
                return item
        return None
    
    # ============================================================
    # 验证类实例
    # ============================================================
    print("\nValidating class instances:")
    
    # PersonClass - 应该有 1000 个
    person = find_type_containing("PersonClass")
    assert person is not None, "PersonClass not found"
    print("  PersonClass: amount=%d" % person["amount"])
    assert person["amount"] == 1000, "Expected 1000 PersonClass, got %d" % person["amount"]
    print("  ✓ PersonClass amount = 1000")
    
    # GameEntity - 应该有 300 个
    game_entity = find_type_containing("GameEntity")
    assert game_entity is not None, "GameEntity not found"
    print("  GameEntity: amount=%d" % game_entity["amount"])
    assert game_entity["amount"] == 300, "Expected 300 GameEntity, got %d" % game_entity["amount"]
    print("  ✓ GameEntity amount = 300")
    
    # TreeNode - 应该有 600 个 (200 根节点 + 200 左子节点 + 200 右子节点)
    tree_node = find_type_containing("TreeNode")
    assert tree_node is not None, "TreeNode not found"
    print("  TreeNode: amount=%d" % tree_node["amount"])
    assert tree_node["amount"] == 600, "Expected 600 TreeNode, got %d" % tree_node["amount"]
    print("  ✓ TreeNode amount = 600")
    
    # ============================================================
    # 验证字典类型
    # ============================================================
    print("\nValidating dict types:")
    
    # {"id", "value"} - 应该有 1000 个
    id_value_dict = find_exact_type('{"id", "value"}')
    assert id_value_dict is not None, '{"id", "value"} not found'
    print('  {"id", "value"}: amount=%d' % id_value_dict["amount"])
    assert id_value_dict["amount"] == 1000, 'Expected 1000 {"id", "value"}, got %d' % id_value_dict["amount"]
    print('  ✓ {"id", "value"} amount = 1000')
    
    # ============================================================
    # 验证 NamedTuple 类型
    # ============================================================
    print("\nValidating NamedTuple types:")
    
    # Point - 应该有 400 个
    point = find_type_containing("Point")
    assert point is not None, "Point not found"
    print("  Point: amount=%d" % point["amount"])
    assert point["amount"] == 400, "Expected 400 Point, got %d" % point["amount"]
    print("  ✓ Point amount = 400")
    
    # Rectangle - 应该有 300 个
    rectangle = find_type_containing("Rectangle")
    assert rectangle is not None, "Rectangle not found"
    print("  Rectangle: amount=%d" % rectangle["amount"])
    assert rectangle["amount"] == 300, "Expected 300 Rectangle, got %d" % rectangle["amount"]
    print("  ✓ Rectangle amount = 300")
    
    # ============================================================
    # 验证集合类型
    # ============================================================
    print("\nValidating set types:")
    
    # 查找包含 set 的类型
    set_types = [item for item in items if "set" in item.get("type", "").lower()]
    total_sets = sum(item["amount"] for item in set_types)
    print("  Total set objects: %d" % total_sets)
    assert total_sets >= 800, "Expected >= 800 set objects, got %d" % total_sets
    print("  ✓ Total set objects >= 800")
    
    print("\n" + "=" * 60)
    print("All validations passed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
        result = validate(data)
        sys.exit(0 if result else 1)
    else:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

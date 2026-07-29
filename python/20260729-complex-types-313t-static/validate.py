#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证脚本 - CPython 3.13 free-threaded static 复杂类型测试用例

除常见对象类型外，明确验证 Maze 选择 CPython 内嵌 mimalloc，并识别
debug allocator 的 PyMem domain。该用例不能静默退化到 ptmalloc/pymalloc。
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

    allocator = summary.get("allocator", "")
    print("  allocator = %s" % allocator)
    assert allocator == "mimalloc", "Expected mimalloc allocator, got %r" % allocator
    print("  ✓ allocator = mimalloc")

    unknown = summary.get("unknown", -1)
    print("  unknown = %d" % unknown)
    assert unknown == 0, "Expected no unknown memory, got %d bytes" % unknown
    print("  ✓ unknown = 0")

    pymempool = summary.get("pymempool", -1)
    print("  pymempool = %d" % pymempool)
    assert pymempool == 0, "Expected no pymalloc pools, got %d bytes" % pymempool
    print("  ✓ pymempool = 0")

    pymempool_objects = summary.get("pymempool_objects", 0)
    print("  pymempool_objects = %d" % pymempool_objects)
    assert pymempool_objects == 0, "Expected no pymempool objects, got %d" % pymempool_objects
    print("  ✓ pymempool_objects = 0")

    malloc_objects = summary.get("malloc_objects", 0)
    print("  malloc_objects = %d" % malloc_objects)
    assert malloc_objects > 50000, "Expected > 50000 mimalloc objects, got %d" % malloc_objects
    print("  ✓ malloc_objects > 50000")

    # ============================================================
    # 辅助函数
    # ============================================================
    def find_type_containing(target):
        """查找包含指定字符串的类型 (精确匹配 instance 类型)"""
        # 优先匹配精确的 instance 类型 (Python 3.x 格式: <class ClassName> instance)
        exact_pattern = "<class %s> instance" % target
        for item in items:
            t = item.get("type", "")
            if exact_pattern in t:
                return item
        # 兼容 Python 2.7 格式: <class ClassName'> instance
        exact_pattern_27 = "<%s'> instance" % target
        for item in items:
            t = item.get("type", "")
            if exact_pattern_27 in t:
                return item
        # 退回到简单包含匹配 (但排除列表类型签名)
        for item in items:
            t = item.get("type", "")
            if target in t and not t.startswith("["):
                return item
        return None

    def find_exact_type(target):
        """精确匹配类型"""
        for item in items:
            if item.get("type", "") == target:
                return item
        return None

    py_mem_domain = [
        item for item in items
        if "{CPython PyMem domain}" in item.get("type", "")
    ]
    py_mem_domain_amount = sum(item.get("amount", 0) for item in py_mem_domain)
    print("\nValidating CPython debug allocator:")
    print("  CPython PyMem domain objects: %d" % py_mem_domain_amount)
    assert py_mem_domain_amount > 0, "CPython PyMem domain allocations not found"
    print("  ✓ CPython PyMem domain allocations identified")

    # ============================================================
    # 验证类实例
    # ============================================================
    print("\nValidating class instances:")

    # CPython 3.13 的分类结果还包含每个用户类型自身的 1 个类型对象。
    person = find_type_containing("PersonClass")
    assert person is not None, "PersonClass not found"
    print("  PersonClass: amount=%d" % person["amount"])
    assert person["amount"] == 1001, "Expected 1001 PersonClass, got %d" % person["amount"]
    print("  ✓ PersonClass amount = 1001")

    # GameEntity - 应该有 300 个
    game_entity = find_type_containing("GameEntity")
    assert game_entity is not None, "GameEntity not found"
    print("  GameEntity: amount=%d" % game_entity["amount"])
    assert game_entity["amount"] == 301, "Expected 301 GameEntity, got %d" % game_entity["amount"]
    print("  ✓ GameEntity amount = 301")

    # TreeNode - 应该有 600 个
    tree_node = find_type_containing("TreeNode")
    assert tree_node is not None, "TreeNode not found"
    print("  TreeNode: amount=%d" % tree_node["amount"])
    assert tree_node["amount"] == 601, "Expected 601 TreeNode, got %d" % tree_node["amount"]
    print("  ✓ TreeNode amount = 601")

    # SimpleClass - 应该有 500 个
    simple_class = find_type_containing("SimpleClass")
    assert simple_class is not None, "SimpleClass not found"
    print("  SimpleClass: amount=%d" % simple_class["amount"])
    assert simple_class["amount"] == 501, "Expected 501 SimpleClass, got %d" % simple_class["amount"]
    print("  ✓ SimpleClass amount = 501")

    # ============================================================
    # 验证 dataclass 类型 (Python 3.7+)
    # ============================================================
    print("\nValidating dataclass instances:")

    # Player dataclass - 应该有 500 个
    player = find_type_containing("Player")
    assert player is not None, "Player dataclass not found"
    print("  Player: amount=%d" % player["amount"])
    assert player["amount"] == 501, "Expected 501 Player, got %d" % player["amount"]
    print("  ✓ Player dataclass amount = 501")

    # Config frozen dataclass - 应该有 300 个
    config = find_type_containing("Config")
    assert config is not None, "Config dataclass not found"
    print("  Config: amount=%d" % config["amount"])
    assert config["amount"] == 301, "Expected 301 Config, got %d" % config["amount"]
    print("  ✓ Config dataclass amount = 301")

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
    # 验证 NamedTuple 类型 (typing.NamedTuple)
    # ============================================================
    print("\nValidating NamedTuple types:")

    # NamedTuple 实例按底层 tuple 归类；这里验证类型标记存在。
    point = find_type_containing("Point")
    assert point is not None, "Point not found"
    print("  Point: amount=%d" % point["amount"])
    print("  ✓ Point type marker identified")

    rectangle = find_type_containing("Rectangle")
    assert rectangle is not None, "Rectangle not found"
    print("  Rectangle: amount=%d" % rectangle["amount"])
    print("  ✓ Rectangle type marker identified")

    # ============================================================
    # 验证 collections.deque 类型
    # ============================================================
    print("\nValidating collections types:")

    # deque 实例的内部块按 allocator 大小分类；这里验证类型标记存在。
    deque_type = find_type_containing("deque")
    assert deque_type is not None, "deque not found"
    print("  deque: amount=%d" % deque_type["amount"])
    print("  ✓ deque type marker identified")

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

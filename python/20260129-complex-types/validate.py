#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证脚本 - python/20260129-complex-types

验证 maze 分析结果是否符合预期:
- 测试用例创建了多种类型的对象，包括:
  - 2800 个 list 对象
  - 2500 个 tuple 对象
  - 2400 个 class 实例 (SimpleClass, PersonClass, GameEntity, TreeNode)
  - 1200 个 set/frozenset 对象
  - 1400 个 bytes/bytearray 对象
  - 2400 个 dict 对象 (包括 defaultdict, OrderedDict, Counter)
  - 2000 个 string 对象
  - 1300 个 numeric 对象 (int, float, complex)
  - 1000 个 collections 对象 (deque, namedtuple)

预期 maze 应该能够识别和统计这些类型
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
    
    # 检查基本结构
    assert "items" in data, "Missing 'items' in result"
    assert "summary" in data, "Missing 'summary' in result"
    
    items = data["items"]
    summary = data["summary"]
    
    assert len(items) > 0, "items list is empty"
    
    print("items count: %d" % len(items))
    print("summary: %s" % summary)
    print("")
    
    # ============================================================
    # 验证 summary
    # ============================================================
    print("Validating summary...")
    
    # pymempool_objects 应该有大量对象 (我们创建了约 17000 个)
    pymempool_objects = summary.get("pymempool_objects", 0)
    assert pymempool_objects > 10000, \
        "Expected pymempool_objects > 10000, got %s" % pymempool_objects
    print("  ✓ pymempool_objects = %d (> 10000)" % pymempool_objects)
    
    # ============================================================
    # 验证各种类型的存在
    # ============================================================
    print("")
    print("Validating type presence...")
    
    # 构建类型到数量的映射
    type_amounts = {}
    for item in items:
        type_name = item.get("type", "")
        amount = item.get("amount", 0)
        type_amounts[type_name] = amount
    
    # 打印前 20 个类型
    print("")
    print("Top 20 types by amount:")
    sorted_items = sorted(items, key=lambda x: x.get("amount", 0), reverse=True)[:20]
    for i, item in enumerate(sorted_items):
        print("  %2d. [%5d] %s" % (i + 1, item.get("amount", 0), item.get("type", "")))
    print("")
    
    # ============================================================
    # 验证特定类型的存在和数量
    # ============================================================
    print("Validating specific types...")
    
    # 辅助函数: 检查是否存在包含特定子串的类型
    def find_type_containing(substring):
        for type_name, amount in type_amounts.items():
            if substring in type_name:
                return type_name, amount
        return None, 0
    
    # 辅助函数: 检查是否存在数量在范围内的类型
    def assert_type_exists(substring, min_amount=1, description=None):
        type_name, amount = find_type_containing(substring)
        if type_name is None:
            # 尝试列出所有类型
            print("  Available types: %s" % list(type_amounts.keys())[:50])
            raise AssertionError(
                "Expected type containing '%s', not found" % substring
            )
        if amount < min_amount:
            raise AssertionError(
                "Expected type '%s' with amount >= %d, got %d" % 
                (substring, min_amount, amount)
            )
        desc = description or substring
        print("  ✓ Found '%s' (type='%s', amount=%d)" % (desc, type_name, amount))
        return type_name, amount
    
    # 验证 PersonClass 实例 (1000 个)
    # 注意: 具体的类型表示可能取决于 maze 的实现
    # 可能表示为 "PersonClass instance" 或带有属性签名
    assert_type_exists("PersonClass", 100, "PersonClass instances")
    
    # 验证 GameEntity 实例 (300 个)
    assert_type_exists("GameEntity", 100, "GameEntity instances")
    
    # 验证 TreeNode 实例 (600 个)
    assert_type_exists("TreeNode", 100, "TreeNode instances")
    
    # 验证 SimpleClass 实例 (500 个)
    assert_type_exists("SimpleClass", 100, "SimpleClass instances")
    
    # ============================================================
    # 验证字典类型
    # ============================================================
    print("")
    print("Validating dict types...")
    
    # 我们创建了多种字典:
    # - 1000 个 {"id": ..., "value": ...}
    # - 500 个嵌套字典 {"user": {...}}
    # - 300 个多键字典
    # - 200 个 defaultdict
    # - 200 个 OrderedDict
    # - 200 个 Counter
    
    # 检查是否有字典类型存在
    dict_found = False
    total_dict_count = 0
    for type_name, amount in type_amounts.items():
        # 字典类型可能表示为 {key1, key2} 或 dict 等
        if "{" in type_name and "}" in type_name:
            dict_found = True
            total_dict_count += amount
    
    if dict_found:
        print("  ✓ Found dict types, total count: %d" % total_dict_count)
    else:
        # 可能字典以其他方式表示
        print("  ? Dict types might be represented differently")
    
    # ============================================================
    # 验证嵌套字典的具体类型 (500 个嵌套字典结构)
    # ============================================================
    print("")
    print("Validating nested dict types...")
    
    # 嵌套字典结构:
    # {"user": {"id": i, "profile": {"name": "...", "settings": {"theme": "dark", "lang": "zh"}}}}
    # 这会产生 4 层字典，每层 500 个
    
    # 辅助函数: 精确匹配类型
    def find_exact_type(target_type):
        for item in items:
            if item.get("type", "") == target_type:
                return item
        return None
    
    # 验证 {"id", "profile"} - 500 个
    item_id_profile = find_exact_type('{"id", "profile"}')
    assert item_id_profile is not None, \
        'Expected type {"id", "profile"} not found'
    assert item_id_profile["amount"] == 500, \
        'Expected {"id", "profile"} amount=500, got %s' % item_id_profile["amount"]
    assert item_id_profile["total_size"] == 96000, \
        'Expected {"id", "profile"} total_size=96000, got %s' % item_id_profile["total_size"]
    assert item_id_profile["avg_size"] == 192, \
        'Expected {"id", "profile"} avg_size=192, got %s' % item_id_profile["avg_size"]
    print('  ✓ {"id", "profile"}: amount=500, total_size=96000, avg_size=192')
    
    # 验证 {"name", "settings"} - 500 个
    item_name_settings = find_exact_type('{"name", "settings"}')
    assert item_name_settings is not None, \
        'Expected type {"name", "settings"} not found'
    assert item_name_settings["amount"] == 500, \
        'Expected {"name", "settings"} amount=500, got %s' % item_name_settings["amount"]
    assert item_name_settings["total_size"] == 96000, \
        'Expected {"name", "settings"} total_size=96000, got %s' % item_name_settings["total_size"]
    assert item_name_settings["avg_size"] == 192, \
        'Expected {"name", "settings"} avg_size=192, got %s' % item_name_settings["avg_size"]
    print('  ✓ {"name", "settings"}: amount=500, total_size=96000, avg_size=192')
    
    # 验证 {"lang", "theme"} - 500 个
    item_lang_theme = find_exact_type('{"lang", "theme"}')
    assert item_lang_theme is not None, \
        'Expected type {"lang", "theme"} not found'
    assert item_lang_theme["amount"] == 500, \
        'Expected {"lang", "theme"} amount=500, got %s' % item_lang_theme["amount"]
    assert item_lang_theme["total_size"] == 96000, \
        'Expected {"lang", "theme"} total_size=96000, got %s' % item_lang_theme["total_size"]
    assert item_lang_theme["avg_size"] == 192, \
        'Expected {"lang", "theme"} avg_size=192, got %s' % item_lang_theme["avg_size"]
    print('  ✓ {"lang", "theme"}: amount=500, total_size=96000, avg_size=192')
    
    # ============================================================
    # 验证 items 结构完整性
    # ============================================================
    print("")
    print("Validating items structure...")
    
    for i, item in enumerate(items[:5]):
        assert "order" in item, "Missing 'order' in items[%d]" % i
        assert "amount" in item, "Missing 'amount' in items[%d]" % i
        assert "total_size" in item, "Missing 'total_size' in items[%d]" % i
        assert "avg_size" in item, "Missing 'avg_size' in items[%d]" % i
        assert "type" in item, "Missing 'type' in items[%d]" % i
        assert "type_id" in item, "Missing 'type_id' in items[%d]" % i
        
        # avg_size 应该合理 (> 0)
        assert item["avg_size"] > 0, \
            "items[%d].avg_size should be > 0, got %s" % (i, item["avg_size"])
    
    print("  ✓ First 5 items have valid structure")
    
    # ============================================================
    # 验证总对象数量
    # ============================================================
    print("")
    print("Validating total object count...")
    
    total_objects = sum(item.get("amount", 0) for item in items)
    
    # 我们创建了约 17000 个对象，加上 Python 内部对象，应该更多
    assert total_objects > 15000, \
        "Expected total objects > 15000, got %d" % total_objects
    print("  ✓ Total objects in items: %d (> 15000)" % total_objects)
    
    print("")
    print("All validations passed!")
    return True


if __name__ == "__main__":
    # 用于独立测试
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

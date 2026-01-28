#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证脚本 - python/20260128-basic

验证 maze 分析结果是否符合预期:
- 测试用例创建了 10000 个 {"a": 1} 字典对象
- 预期 items[0] 应该是这些字典对象的汇总
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
    assert len(items) > 0, "items list is empty"
    
    # 获取第一个 item
    item0 = items[0]
    print("items[0]: %s" % item0)
    
    # 验证 items[0] 的结构
    assert "order" in item0, "Missing 'order' in items[0]"
    assert "amount" in item0, "Missing 'amount' in items[0]"
    assert "total_size" in item0, "Missing 'total_size' in items[0]"
    assert "avg_size" in item0, "Missing 'avg_size' in items[0]"
    assert "type" in item0, "Missing 'type' in items[0]"
    assert "type_id" in item0, "Missing 'type_id' in items[0]"
    
    # 验证 items[0] 的值
    print("")
    print("Validating items[0] values:")
    
    # order 应该是 1
    assert item0["order"] == 1, \
        "Expected order=1, got %s" % item0["order"]
    print("  ✓ order = 1")
    
    # amount 应该是 10000 (创建了 10000 个字典)
    assert item0["amount"] == 10000, \
        "Expected amount=10000, got %s" % item0["amount"]
    print("  ✓ amount = 10000")
    
    # total_size 应该是 1920000
    assert item0["total_size"] == 1920000, \
        "Expected total_size=1920000, got %s" % item0["total_size"]
    print("  ✓ total_size = 1920000")
    
    # avg_size 应该是 192
    assert item0["avg_size"] == 192, \
        "Expected avg_size=192, got %s" % item0["avg_size"]
    print("  ✓ avg_size = 192")
    
    # type 应该是 '{"a"}'
    expected_type = '{"a"}'
    assert item0["type"] == expected_type, \
        "Expected type=%r, got %r" % (expected_type, item0["type"])
    print("  ✓ type = %r" % expected_type)
    
    # type_id 应该是 300000022000000
    assert item0["type_id"] == 300000022000000, \
        "Expected type_id=300000022000000, got %s" % item0["type_id"]
    print("  ✓ type_id = 300000022000000")
    
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

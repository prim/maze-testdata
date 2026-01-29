#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证脚本 - Python 3.5 复杂类型测试用例

Python 3.5 特点:
- 无 f-string (Python 3.6+)
- 无 dataclass (Python 3.7+)
- 类实例识别方式可能与 Python 3.11 不同

此验证脚本针对 Python 3.5 的实际输出进行调整
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
    
    # Python 3.5 的 pymempool 对象数量较少 (约 26000)
    pymempool_objects = summary.get("pymempool_objects", 0)
    print("  pymempool_objects = %d" % pymempool_objects)
    assert pymempool_objects > 20000, "Expected > 20000 pymempool objects, got %d" % pymempool_objects
    print("  ✓ pymempool_objects > 20000")
    
    # ============================================================
    # 辅助函数
    # ============================================================
    def find_type_containing(target):
        """查找包含指定字符串的类型"""
        for item in items:
            t = item.get("type", "")
            if target in t:
                return item
        return None
    
    def find_exact_type(target):
        """精确匹配类型"""
        for item in items:
            if item.get("type", "") == target:
                return item
        return None
    
    # ============================================================
    # 验证基础类型
    # ============================================================
    print("\nValidating basic types:")
    
    # unicode - 应该有很多
    unicode_type = find_exact_type("unicode")
    assert unicode_type is not None, "unicode not found"
    print("  unicode: amount=%d" % unicode_type["amount"])
    assert unicode_type["amount"] > 10000, "Expected > 10000 unicode, got %d" % unicode_type["amount"]
    print("  ✓ unicode amount > 10000")
    
    # bytes
    bytes_type = find_type_containing("bytes")
    assert bytes_type is not None, "bytes not found"
    print("  bytes: amount=%d" % bytes_type["amount"])
    assert bytes_type["amount"] > 1000, "Expected > 1000 bytes, got %d" % bytes_type["amount"]
    print("  ✓ bytes amount > 1000")
    
    # ============================================================
    # 验证集合类型
    # ============================================================
    print("\nValidating set types:")
    
    # 查找包含 set 的类型
    set_types = [item for item in items if "set" in item.get("type", "").lower()]
    total_sets = sum(item["amount"] for item in set_types)
    print("  Total set objects: %d" % total_sets)
    assert total_sets >= 500, "Expected >= 500 set objects, got %d" % total_sets
    print("  ✓ Total set objects >= 500")
    
    # ============================================================
    # 验证 function 和 code 对象
    # ============================================================
    print("\nValidating function types:")
    
    # function instance
    func_type = find_type_containing("function")
    assert func_type is not None, "function not found"
    print("  function: amount=%d" % func_type["amount"])
    assert func_type["amount"] > 500, "Expected > 500 function, got %d" % func_type["amount"]
    print("  ✓ function amount > 500")
    
    # code instance
    code_type = find_type_containing("code")
    assert code_type is not None, "code not found"
    print("  code: amount=%d" % code_type["amount"])
    assert code_type["amount"] > 500, "Expected > 500 code, got %d" % code_type["amount"]
    print("  ✓ code amount > 500")
    
    # ============================================================
    # 验证 type 对象
    # ============================================================
    print("\nValidating type objects:")
    
    # 尝试多种匹配方式（不同 Python 版本格式不同）
    type_obj = find_type_containing("type> instance")
    if type_obj is None:
        type_obj = find_exact_type("type instance")
    assert type_obj is not None, "type instance not found"
    print("  type instance: amount=%d" % type_obj["amount"])
    assert type_obj["amount"] > 50, "Expected > 50 type instances, got %d" % type_obj["amount"]
    print("  ✓ type instance amount > 50")
    
    # ============================================================
    # 验证 malloc 对象
    # ============================================================
    print("\nValidating malloc objects:")
    
    malloc_objects = summary.get("malloc_objects", 0)
    print("  malloc_objects = %d" % malloc_objects)
    assert malloc_objects > 100, "Expected > 100 malloc objects, got %d" % malloc_objects
    print("  ✓ malloc_objects > 100")
    
    print("\n" + "=" * 60)
    print("All validations passed!")
    print("Python 3.5 test case validated successfully.")
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复杂类型测试进程 - 用于测试 Maze 对各种 Python 类型的内存分析

创建多种类型的对象:
- list (列表)
- tuple (元组)
- class 实例 (自定义类)
- set (集合)
- frozenset (不可变集合)
- bytes (字节串)
- bytearray (可变字节数组)
- dict (嵌套字典)
- str/unicode (不同大小的字符串)
- complex (复数)
- deque (双端队列)
- defaultdict (默认字典)
- OrderedDict (有序字典)
- Counter (计数器)
- namedtuple 实例

使用方法:
    python complex_types.py

生成 core dump:
    gcore <pid>
    # 或
    kill -ABRT <pid>
"""

from __future__ import print_function
import os
import sys
import time
from collections import deque, defaultdict, OrderedDict, Counter, namedtuple


# ============================================================
# 自定义类定义
# ============================================================

class SimpleClass:
    """简单的类 - 没有属性"""
    pass


class PersonClass:
    """带属性的类 - 模拟用户数据"""
    def __init__(self, name, age, email):
        self.name = name
        self.age = age
        self.email = email


class GameEntity:
    """游戏实体类 - 更复杂的属性"""
    def __init__(self, entity_id, x, y, hp, inventory):
        self.entity_id = entity_id
        self.x = x
        self.y = y
        self.hp = hp
        self.inventory = inventory  # 这是一个列表
        self.status = {"alive": True, "level": 1}


class TreeNode:
    """树节点 - 带有引用关系"""
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


# NamedTuple 类型
Point = namedtuple('Point', ['x', 'y'])
Rectangle = namedtuple('Rectangle', ['x', 'y', 'width', 'height'])


# ============================================================
# 对象创建函数
# ============================================================

def create_lists(storage):
    """创建各种列表"""
    print("Creating lists...")
    
    # 1000 个空列表
    for i in range(1000):
        storage.append([])
    
    # 1000 个单元素列表
    for i in range(1000):
        storage.append([i])
    
    # 500 个包含 10 个整数的列表
    for i in range(500):
        storage.append(list(range(10)))
    
    # 200 个包含混合类型的列表
    for i in range(200):
        storage.append([1, "hello", 3.14, None, True])
    
    # 100 个嵌套列表
    for i in range(100):
        storage.append([[1, 2], [3, 4], [5, 6]])
    
    print("  Created 2800 list objects")


def create_tuples(storage):
    """创建各种元组"""
    print("Creating tuples...")
    
    # 1000 个空元组会被优化为同一个对象，所以创建带内容的
    # 1000 个单元素元组
    for i in range(1000):
        storage.append((i,))
    
    # 800 个两元素元组
    for i in range(800):
        storage.append((i, i * 2))
    
    # 500 个三元素元组
    for i in range(500):
        storage.append((i, "item", float(i)))
    
    # 200 个混合类型元组
    for i in range(200):
        storage.append((1, "hello", 3.14, None, True, [1, 2, 3]))
    
    print("  Created 2500 tuple objects")


def create_class_instances(storage):
    """创建类实例"""
    print("Creating class instances...")
    
    # 500 个 SimpleClass 实例
    for i in range(500):
        storage.append(SimpleClass())
    
    # 1000 个 PersonClass 实例
    for i in range(1000):
        storage.append(PersonClass(
            name="user_%d" % i,
            age=20 + (i % 50),
            email="user%d@example.com" % i
        ))
    
    # 300 个 GameEntity 实例
    for i in range(300):
        storage.append(GameEntity(
            entity_id=i,
            x=float(i * 10),
            y=float(i * 20),
            hp=100,
            inventory=["sword", "shield", "potion"]
        ))
    
    # 200 个 TreeNode 实例 (构建一些简单的树结构)
    for i in range(200):
        left = TreeNode(i * 2)
        right = TreeNode(i * 2 + 1)
        storage.append(TreeNode(i, left, right))
        storage.append(left)
        storage.append(right)
    
    print("  Created 2400 class instances (500 Simple + 1000 Person + 300 GameEntity + 600 TreeNode)")


def create_sets(storage):
    """创建集合类型"""
    print("Creating sets...")
    
    # 500 个小集合
    for i in range(500):
        storage.append({i, i + 1, i + 2})
    
    # 300 个中等集合
    for i in range(300):
        storage.append(set(range(i, i + 20)))
    
    # 400 个 frozenset
    for i in range(400):
        storage.append(frozenset([i, i + 1, i + 2, i + 3]))
    
    print("  Created 1200 set objects (500 set + 300 medium set + 400 frozenset)")


def create_bytes_types(storage):
    """创建字节类型"""
    print("Creating bytes types...")
    
    # 500 个短 bytes
    for i in range(500):
        storage.append(b"hello%d" % i if sys.version_info[0] == 2 else ("hello%d" % i).encode())
    
    # 300 个中等长度 bytes
    for i in range(300):
        storage.append(b"x" * 100)
    
    # 200 个长 bytes
    for i in range(200):
        storage.append(b"y" * 1000)
    
    # 400 个 bytearray
    for i in range(400):
        storage.append(bytearray(b"data_%d" % i if sys.version_info[0] == 2 else ("data_%d" % i).encode()))
    
    print("  Created 1400 bytes/bytearray objects")


def create_dicts(storage):
    """创建各种字典"""
    print("Creating dicts...")
    
    # 1000 个简单字典
    for i in range(1000):
        storage.append({"id": i, "value": i * 10})
    
    # 500 个嵌套字典
    for i in range(500):
        storage.append({
            "user": {
                "id": i,
                "profile": {
                    "name": "user_%d" % i,
                    "settings": {"theme": "dark", "lang": "zh"}
                }
            }
        })
    
    # 300 个多键字典
    for i in range(300):
        d = {}
        for j in range(20):
            d["key_%d" % j] = j
        storage.append(d)
    
    # 200 个 defaultdict
    for i in range(200):
        dd = defaultdict(list)
        dd["items"].append(i)
        dd["items"].append(i + 1)
        storage.append(dd)
    
    # 200 个 OrderedDict
    for i in range(200):
        od = OrderedDict()
        od["first"] = i
        od["second"] = i + 1
        od["third"] = i + 2
        storage.append(od)
    
    # 200 个 Counter
    for i in range(200):
        c = Counter(["a", "b", "a", "c", "a", "b"])
        storage.append(c)
    
    print("  Created 2400 dict objects (1000 simple + 500 nested + 300 multi-key + 200 defaultdict + 200 OrderedDict + 200 Counter)")


def create_strings(storage):
    """创建各种字符串"""
    print("Creating strings...")
    
    # 1000 个短字符串
    for i in range(1000):
        storage.append("str_%d" % i)
    
    # 500 个中等字符串
    for i in range(500):
        storage.append("medium_string_%d_" % i + "x" * 50)
    
    # 200 个长字符串
    for i in range(200):
        storage.append("long_string_%d_" % i + "y" * 500)
    
    # 300 个 Unicode 字符串
    for i in range(300):
        storage.append(u"中文字符串_%d_你好世界" % i)
    
    print("  Created 2000 string objects")


def create_numeric_types(storage):
    """创建数值类型"""
    print("Creating numeric types...")
    
    # 注意: 小整数 (-5 to 256) 在 Python 中是共享的
    # 所以我们创建大整数
    
    # 500 个大整数
    for i in range(500):
        storage.append(10000000 + i)
    
    # 500 个浮点数
    for i in range(500):
        storage.append(float(i) * 3.14159)
    
    # 300 个复数
    for i in range(300):
        storage.append(complex(i, i + 1))
    
    print("  Created 1300 numeric objects")


def create_collections_types(storage):
    """创建 collections 模块类型"""
    print("Creating collections types...")
    
    # 300 个 deque
    for i in range(300):
        d = deque([1, 2, 3, 4, 5])
        d.append(i)
        storage.append(d)
    
    # 400 个 namedtuple - Point
    for i in range(400):
        storage.append(Point(x=float(i), y=float(i * 2)))
    
    # 300 个 namedtuple - Rectangle
    for i in range(300):
        storage.append(Rectangle(x=i, y=i, width=100, height=50))
    
    print("  Created 1000 collections objects (300 deque + 400 Point + 300 Rectangle)")


def main():
    pid = os.getpid()
    print("=" * 60)
    print("Complex Types Test Process Started")
    print("PID: %d" % pid)
    print("Python Version: %s" % sys.version)
    print("=" * 60)
    print("")
    
    # 使用一个大列表存储所有对象，防止被 GC
    storage = []
    
    # 创建各种类型的对象
    create_lists(storage)
    create_tuples(storage)
    create_class_instances(storage)
    create_sets(storage)
    create_bytes_types(storage)
    create_dicts(storage)
    create_strings(storage)
    create_numeric_types(storage)
    create_collections_types(storage)
    
    print("")
    print("=" * 60)
    print("Summary:")
    print("  Total objects in storage: %d" % len(storage))
    print("=" * 60)
    print("")
    print("To generate core dump, run:")
    print("  gcore %d" % pid)
    print("")
    print("Or use maze-tar-coredump.py:")
    print("  python cmd/maze-tar-coredump.py %d complex-types" % pid)
    print("")
    print("Sleeping forever... (Ctrl+C to exit)")
    
    # Sleep forever
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复杂类型测试进程 - Python 3.11 版本

测试 Maze 对 Python 3.11 各种类型的内存分析
使用 Python 3.11+ 特有的语法特性

使用方法:
    pyenv shell 3.11.2
    python complex_types.py
"""

import os
import sys
import time
from collections import deque, defaultdict, OrderedDict, Counter
from typing import NamedTuple
from dataclasses import dataclass


# ============================================================
# 自定义类定义
# ============================================================

class SimpleClass:
    """简单的类 - 没有属性"""
    pass


class PersonClass:
    """带属性的类 - 模拟用户数据"""
    def __init__(self, name: str, age: int, email: str):
        self.name = name
        self.age = age
        self.email = email


class GameEntity:
    """游戏实体类 - 更复杂的属性"""
    def __init__(self, entity_id: int, x: float, y: float, hp: int, inventory: list):
        self.entity_id = entity_id
        self.x = x
        self.y = y
        self.hp = hp
        self.inventory = inventory
        self.status = {"alive": True, "level": 1}


class TreeNode:
    """树节点 - 带有引用关系"""
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


# Python 3.11 typing.NamedTuple
class Point(NamedTuple):
    x: float
    y: float


class Rectangle(NamedTuple):
    x: int
    y: int
    width: int
    height: int


# Python 3.7+ dataclass
@dataclass
class Player:
    name: str
    level: int
    health: float
    items: list


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    debug: bool


# ============================================================
# 对象创建函数
# ============================================================

def create_lists(storage: list) -> None:
    """创建各种列表"""
    print("Creating lists...")
    
    # 空列表
    for _ in range(1000):
        storage.append([])
    
    # 单元素列表
    for i in range(1000):
        storage.append([i])
    
    # 10 个整数的列表
    for _ in range(500):
        storage.append(list(range(10)))
    
    # 混合类型列表
    for _ in range(200):
        storage.append([1, "hello", 3.14, None, True])
    
    # 嵌套列表
    for _ in range(100):
        storage.append([[1, 2], [3, 4], [5, 6]])
    
    print("  Created 2800 list objects")


def create_tuples(storage: list) -> None:
    """创建各种元组"""
    print("Creating tuples...")
    
    for i in range(1000):
        storage.append((i,))
    
    for i in range(800):
        storage.append((i, i * 2))
    
    for i in range(500):
        storage.append((i, "item", float(i)))
    
    for _ in range(200):
        storage.append((1, "hello", 3.14, None, True, [1, 2, 3]))
    
    print("  Created 2500 tuple objects")


def create_class_instances(storage: list) -> None:
    """创建类实例"""
    print("Creating class instances...")
    
    # SimpleClass
    for _ in range(500):
        storage.append(SimpleClass())
    
    # PersonClass
    for i in range(1000):
        storage.append(PersonClass(
            name=f"user_{i}",
            age=20 + (i % 50),
            email=f"user{i}@example.com"
        ))
    
    # GameEntity
    for i in range(300):
        storage.append(GameEntity(
            entity_id=i,
            x=float(i * 10),
            y=float(i * 20),
            hp=100,
            inventory=["sword", "shield", "potion"]
        ))
    
    # TreeNode
    for i in range(200):
        left = TreeNode(i * 2)
        right = TreeNode(i * 2 + 1)
        storage.append(TreeNode(i, left, right))
        storage.append(left)
        storage.append(right)
    
    print("  Created 2400 class instances")


def create_dataclasses(storage: list) -> None:
    """创建 dataclass 实例 - Python 3.7+"""
    print("Creating dataclass instances...")
    
    # Player dataclass
    for i in range(500):
        storage.append(Player(
            name=f"player_{i}",
            level=i % 100,
            health=100.0 - (i % 50),
            items=["sword", "potion"]
        ))
    
    # Config frozen dataclass
    for i in range(300):
        storage.append(Config(
            host=f"server{i}.example.com",
            port=8000 + i,
            debug=i % 2 == 0
        ))
    
    print("  Created 800 dataclass instances")


def create_sets(storage: list) -> None:
    """创建集合类型"""
    print("Creating sets...")
    
    for i in range(500):
        storage.append({i, i + 1, i + 2})
    
    for i in range(300):
        storage.append(set(range(i, i + 20)))
    
    for i in range(400):
        storage.append(frozenset([i, i + 1, i + 2, i + 3]))
    
    print("  Created 1200 set objects")


def create_bytes_types(storage: list) -> None:
    """创建字节类型"""
    print("Creating bytes types...")
    
    for i in range(500):
        storage.append(f"hello{i}".encode())
    
    for _ in range(300):
        storage.append(b"x" * 100)
    
    for _ in range(200):
        storage.append(b"y" * 1000)
    
    for i in range(400):
        storage.append(bytearray(f"data_{i}".encode()))
    
    print("  Created 1400 bytes/bytearray objects")


def create_dicts(storage: list) -> None:
    """创建各种字典"""
    print("Creating dicts...")
    
    for i in range(1000):
        storage.append({"id": i, "value": i * 10})
    
    # 嵌套字典
    for i in range(500):
        storage.append({
            "user": {
                "id": i,
                "profile": {
                    "name": f"user_{i}",
                    "settings": {"theme": "dark", "lang": "zh"}
                }
            }
        })
    
    # 多键字典
    for i in range(300):
        storage.append({f"key_{j}": j for j in range(20)})
    
    # defaultdict
    for i in range(200):
        dd = defaultdict(list)
        dd["items"].extend([i, i + 1])
        storage.append(dd)
    
    # OrderedDict
    for i in range(200):
        od = OrderedDict([("first", i), ("second", i + 1), ("third", i + 2)])
        storage.append(od)
    
    # Counter
    for _ in range(200):
        storage.append(Counter(["a", "b", "a", "c", "a", "b"]))
    
    print("  Created 2400 dict objects")


def create_strings(storage: list) -> None:
    """创建各种字符串"""
    print("Creating strings...")
    
    # 短字符串
    for i in range(1000):
        storage.append(f"str_{i}")
    
    # 中等字符串
    for i in range(500):
        storage.append(f"medium_string_{i}_" + "x" * 50)
    
    # 长字符串
    for i in range(200):
        storage.append(f"long_string_{i}_" + "y" * 500)
    
    # Unicode 字符串
    for i in range(300):
        storage.append(f"中文字符串_{i}_你好世界")
    
    print("  Created 2000 string objects")


def create_numeric_types(storage: list) -> None:
    """创建数值类型"""
    print("Creating numeric types...")
    
    # 大整数
    for i in range(500):
        storage.append(10000000 + i)
    
    # 浮点数
    for i in range(500):
        storage.append(float(i) * 3.14159)
    
    # 复数
    for i in range(300):
        storage.append(complex(i, i + 1))
    
    print("  Created 1300 numeric objects")


def create_collections_types(storage: list) -> None:
    """创建 collections 模块类型"""
    print("Creating collections types...")
    
    # deque
    for i in range(300):
        d = deque([1, 2, 3, 4, 5], maxlen=10)
        d.append(i)
        storage.append(d)
    
    # Point NamedTuple
    for i in range(400):
        storage.append(Point(x=float(i), y=float(i * 2)))
    
    # Rectangle NamedTuple
    for i in range(300):
        storage.append(Rectangle(x=i, y=i, width=100, height=50))
    
    print("  Created 1000 collections objects")


def main():
    pid = os.getpid()
    print("=" * 60)
    print("Complex Types Test Process - Python 3.11")
    print(f"PID: {pid}")
    print(f"Python Version: {sys.version}")
    print("=" * 60)
    print()
    
    storage: list = []
    
    create_lists(storage)
    create_tuples(storage)
    create_class_instances(storage)
    create_dataclasses(storage)  # Python 3.7+
    create_sets(storage)
    create_bytes_types(storage)
    create_dicts(storage)
    create_strings(storage)
    create_numeric_types(storage)
    create_collections_types(storage)
    
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Total objects in storage: {len(storage)}")
    print("=" * 60)
    print()
    print("To generate core dump, run:")
    print(f"  gcore {pid}")
    print()
    print("Sleeping forever... (Ctrl+C to exit)")
    
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

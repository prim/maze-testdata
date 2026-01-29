#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复杂类型测试进程 - Python 3.5/3.6 版本
不使用 dataclass (Python 3.7+) 和 f-string (Python 3.6+)
"""

import os
import sys
import time
from collections import deque, defaultdict, OrderedDict, Counter, namedtuple


class SimpleClass:
    pass


class PersonClass:
    def __init__(self, name, age, email):
        self.name = name
        self.age = age
        self.email = email


class GameEntity:
    def __init__(self, entity_id, x, y, hp, inventory):
        self.entity_id = entity_id
        self.x = x
        self.y = y
        self.hp = hp
        self.inventory = inventory
        self.status = {"alive": True, "level": 1}


class TreeNode:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


Point = namedtuple('Point', ['x', 'y'])
Rectangle = namedtuple('Rectangle', ['x', 'y', 'width', 'height'])


def create_lists(storage):
    print("Creating lists...")
    for i in range(1000):
        storage.append([])
    for i in range(1000):
        storage.append([i])
    for i in range(500):
        storage.append(list(range(10)))
    for i in range(200):
        storage.append([1, "hello", 3.14, None, True])
    for i in range(100):
        storage.append([[1, 2], [3, 4], [5, 6]])
    print("  Created 2800 list objects")


def create_tuples(storage):
    print("Creating tuples...")
    for i in range(1000):
        storage.append((i,))
    for i in range(800):
        storage.append((i, i * 2))
    for i in range(500):
        storage.append((i, "item", float(i)))
    for i in range(200):
        storage.append((1, "hello", 3.14, None, True, [1, 2, 3]))
    print("  Created 2500 tuple objects")


def create_class_instances(storage):
    print("Creating class instances...")
    for i in range(500):
        storage.append(SimpleClass())
    for i in range(1000):
        storage.append(PersonClass(
            name="user_%d" % i,
            age=20 + (i % 50),
            email="user%d@example.com" % i
        ))
    for i in range(300):
        storage.append(GameEntity(
            entity_id=i,
            x=float(i * 10),
            y=float(i * 20),
            hp=100,
            inventory=["sword", "shield", "potion"]
        ))
    for i in range(200):
        left = TreeNode(i * 2)
        right = TreeNode(i * 2 + 1)
        storage.append(TreeNode(i, left, right))
        storage.append(left)
        storage.append(right)
    print("  Created 2400 class instances")


def create_sets(storage):
    print("Creating sets...")
    for i in range(500):
        storage.append({i, i + 1, i + 2})
    for i in range(300):
        storage.append(set(range(i, i + 20)))
    for i in range(400):
        storage.append(frozenset([i, i + 1, i + 2, i + 3]))
    print("  Created 1200 set objects")


def create_bytes_types(storage):
    print("Creating bytes types...")
    for i in range(500):
        storage.append(("hello%d" % i).encode())
    for i in range(300):
        storage.append(b"x" * 100)
    for i in range(200):
        storage.append(b"y" * 1000)
    for i in range(400):
        storage.append(bytearray(("data_%d" % i).encode()))
    print("  Created 1400 bytes/bytearray objects")


def create_dicts(storage):
    print("Creating dicts...")
    for i in range(1000):
        storage.append({"id": i, "value": i * 10})
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
    for i in range(300):
        d = {}
        for j in range(20):
            d["key_%d" % j] = j
        storage.append(d)
    for i in range(200):
        dd = defaultdict(list)
        dd["items"].append(i)
        dd["items"].append(i + 1)
        storage.append(dd)
    for i in range(200):
        od = OrderedDict()
        od["first"] = i
        od["second"] = i + 1
        od["third"] = i + 2
        storage.append(od)
    for i in range(200):
        c = Counter(["a", "b", "a", "c", "a", "b"])
        storage.append(c)
    print("  Created 2400 dict objects")


def create_strings(storage):
    print("Creating strings...")
    for i in range(1000):
        storage.append("str_%d" % i)
    for i in range(500):
        storage.append("medium_string_%d_" % i + "x" * 50)
    for i in range(200):
        storage.append("long_string_%d_" % i + "y" * 500)
    for i in range(300):
        storage.append("中文字符串_%d_你好世界" % i)
    print("  Created 2000 string objects")


def create_numeric_types(storage):
    print("Creating numeric types...")
    for i in range(500):
        storage.append(10000000 + i)
    for i in range(500):
        storage.append(float(i) * 3.14159)
    for i in range(300):
        storage.append(complex(i, i + 1))
    print("  Created 1300 numeric objects")


def create_collections_types(storage):
    print("Creating collections types...")
    for i in range(300):
        d = deque([1, 2, 3, 4, 5])
        d.append(i)
        storage.append(d)
    for i in range(400):
        storage.append(Point(x=float(i), y=float(i * 2)))
    for i in range(300):
        storage.append(Rectangle(x=i, y=i, width=100, height=50))
    print("  Created 1000 collections objects")


def main():
    pid = os.getpid()
    print("=" * 60)
    print("Complex Types Test Process - Python 3.5/3.6")
    print("PID: %d" % pid)
    print("Python Version: %s" % sys.version)
    print("=" * 60)
    print("")
    
    storage = []
    
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
    print("Sleeping forever... (Ctrl+C to exit)")
    
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

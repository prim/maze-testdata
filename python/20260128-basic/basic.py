#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的测试进程 - 用于测试 Maze 内存分析

创建 10000 个字典对象，然后 sleep 等待被分析。

使用方法:
    python simple.py

生成 core dump:
    gcore <pid>
    # 或
    kill -ABRT <pid>
"""

from __future__ import print_function
import os
import sys
import time


def main():
    pid = os.getpid()
    print("=" * 50)
    print("Test Process Started")
    print("PID: %d" % pid)
    print("=" * 50)
    
    # 创建 10000 个字典对象
    print("Creating 10000 dict objects...")
    objects = []
    for i in range(10000):
        objects.append({"a": 1})
    
    print("Done! Created %d objects" % len(objects))
    print("")
    print("To generate core dump, run:")
    print("  gcore %d" % pid)
    print("")
    print("Or to attach with GDB:")
    print("  gdb -p %d" % pid)
    print("")
    print("Sleeping forever... (Ctrl+C to exit)")
    
    # Sleep forever
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

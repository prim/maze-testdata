#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Class Merge 模式测试程序

测试目标：
    验证 --py-merge 选项能正确地将类实例中的 refcnt=1 属性合并到实例

测试场景：
    类 A: 包含嵌套 dict，内层 dict 是大字典 (256 个键值对)
    每个实例包含 {"a": 1, "b": {i:i for i in range(256)}}
    内层大字典 (256 entries) 应该被合并到实例

预期结果：
    启用 --py-merge 后：
    - 类 A 实例的 avg_size 应该包含内层大字典的大小
"""
from __future__ import print_function
import os
import sys
import time

# Python 2/3 兼容
if sys.version_info[0] >= 3:
    xrange = range


class A(object):
    """
    测试嵌套字典合并
    
    结构:
        self.items = {"a": 1, "b": {大字典}}
        
    预期合并:
        外层 dict 的 "b" 值是一个 256 条目的大字典 (refcnt=1)
        --py-merge 应该将这个大字典的大小合并到 A 实例
    """
    def __init__(self):
        self.items = {"a": 1, "b": {i: i for i in xrange(256)}}


def main():
    pid = os.getpid()
    print("=" * 70)
    print("Class Merge Test - PID: %d" % pid)
    print("Python version: %s" % sys.version)
    print("=" * 70)
    
    # 创建 10000 个 A 实例
    print("\nCreating 10000 Class A instances...")
    print("  Each A.items = {'a': 1, 'b': {i:i for i in range(256)}}")
    
    l0 = [A() for _ in xrange(10000)]
    
    print("  Created %d A instances" % len(l0))
    print("  Inner dict refcnt = %d (should be 2: attr + getrefcount)" % 
          sys.getrefcount(l0[0].items["b"]))
    
    print("\n" + "=" * 70)
    print("To generate coredump:")
    print("  gcore %d" % pid)
    print("\nTo test py-merge:")
    print("  ./maze --tar <tarball> --text --limit 500")
    print("  ./maze --tar <tarball> --text --limit 500 --py-merge")
    print("=" * 70)
    
    print("\nWaiting for coredump generation...")
    
    # 保持进程存活
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
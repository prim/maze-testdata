#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ 虚继承 vtable address point 测试验证脚本

测试目标：
    带虚基类的类，主 vtable address point 在 _ZTV + 24（或更多），
    Maze 需要用真实 address point 识别这些堆对象，而不是退化为 malloc(N)。

程序：testdata/cpp/virtual_inherit_test.cpp
    VSingle  : public virtual VBase            3000 个
    VDiamond : VLeft, VRight（均虚继承 VBase） 2000 个
    VMixed   : Plain, public virtual VBase     2500 个
    Control  : 无虚基类对照组                    4000 个
    std::ostringstream                          1500 个
    Payload（只被虚基类 VBase::payload 引用）   7500 个
    所有对象只经 std::vector<void*> 持有，类型只能来自 vptr 识别。
"""
from __future__ import print_function
import json
import re
import sys


EXPECTED = [
    ("VSingle", 3000),
    ("VDiamond", 2000),
    ("VMixed", 2500),
    ("Control", 4000),
    # libstdc++ iostream 族通过 basic_ios 虚继承，vptr 同样不在 _ZTV + 16
    ("std::__cxx11::basic_ostringstream<char, std::char_traits<char>, std::allocator<char> >", 1500),
    # 只经 VBase::payload 引用；虚基类偏移需运行时从 vbase offset 槽读取
    ("Payload", 7500),
]


def strip_size_bucket(type_name):
    return re.sub(r"^\(<\d+\)\s*", "", type_name)


def exact_type_amount(items, name):
    # type 形如 "(<64) C++ VSingle"；"C++ VSingle **" 是 std::vector<T*> 缓冲区，不计入。
    matches = [i for i in items if strip_size_bucket(i.get("type", "")) == "C++ " + name]
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0), m.get("avg_size", 0)))
    return sum(i.get("amount", 0) for i in matches)


def validate(data):
    print("=" * 60)
    print("C++ Virtual-Inherit Test Validation")
    print("=" * 60)

    assert "items" in data and "summary" in data
    items = data["items"]
    ok = True

    for index, (name, expected) in enumerate(EXPECTED, 1):
        print("\n[Check %d] %s..." % (index, name))
        total = exact_type_amount(items, name)
        print("  Total: %d (expected ~%d)" % (total, expected))
        if expected * 9 // 10 <= total <= expected * 11 // 10:
            print("  PASS")
        else:
            print("  FAIL")
            ok = False

    print("\n" + "=" * 60)
    print("All passed!" if ok else "Some FAILED")
    print("=" * 60)
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    sys.exit(0 if validate(data) else 1)

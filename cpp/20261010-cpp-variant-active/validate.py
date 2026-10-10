#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ std::variant 活跃成员测试验证脚本

程序：testdata/cpp/variant_active_test.cpp
    std::variant<Payload*, long>：1000 个存 Payload*，1000 个存 Other 地址的整数。
    std::variant<Payload2*, Other2*>：各 1000 个，Payload2 与 Other2 同为 32 字节。

修复前：Payload ~2000（整数成员被当指针）、Payload2 0、Other2 ~2000（按类型名裁决）。
修复后：三者各 ~1000。
"""
from __future__ import print_function
import json
import re
import sys

EXPECTED = [("Payload", 1000), ("Payload2", 1000), ("Other2", 1000)]


def strip_size_bucket(type_name):
    return re.sub(r"^\(<\d+\)\s*", "", type_name)


def validate(data):
    print("=" * 60)
    print("C++ Variant Active Validation")
    print("=" * 60)
    assert "items" in data and "summary" in data
    ok = True
    for index, (name, expected) in enumerate(EXPECTED, 1):
        matches = [i for i in data["items"] if strip_size_bucket(i.get("type", "")) == "C++ " + name]
        for m in matches:
            print("    - %s: amount=%d, avg_size=%d" % (m.get("type", ""), m.get("amount", 0), m.get("avg_size", 0)))
        total = sum(i.get("amount", 0) for i in matches)
        print("[Check %d] %s total: %d (expected ~%d)" % (index, name, total, expected))
        if expected * 9 // 10 <= total <= expected * 11 // 10:
            print("  PASS")
        else:
            print("  FAIL")
            ok = False
    print("=" * 60)
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

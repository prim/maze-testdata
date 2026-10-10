#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ std::optional 残留指针测试验证脚本

程序：testdata/cpp/optional_stale_test.cpp
    1000 个 engaged 的 std::optional<Payload*>：Payload 只经 optional 引用，应被识别。
    1000 个 reset() 后的 optional：payload 字节残留旧指针，旧 Payload 已释放，
    内存被只经 void* 持有的 Other 复用，不应被识别为 Payload。

修复前：C++ Payload 约 2000 个（Other 被残留指针误认）；修复后约 1000 个。
"""
from __future__ import print_function
import json
import re
import sys


def strip_size_bucket(type_name):
    return re.sub(r"^\(<\d+\)\s*", "", type_name)


def validate(data):
    print("=" * 60)
    print("C++ Optional Stale Validation")
    print("=" * 60)
    assert "items" in data and "summary" in data
    matches = [i for i in data["items"] if strip_size_bucket(i.get("type", "")) == "C++ Payload"]
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (m.get("type", ""), m.get("amount", 0), m.get("avg_size", 0)))
    total = sum(i.get("amount", 0) for i in matches)
    print("[Check 1] Payload total: %d (expected ~1000, stale optionals must not add ~1000 more)" % total)
    ok = 900 <= total <= 1100
    print("  PASS" if ok else "  FAIL")
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

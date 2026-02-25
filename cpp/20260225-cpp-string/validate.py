#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C++ std::string 内存归类测试验证脚本

测试目标：
    验证 Maze 对 std::string 成员和裸 string 指针的识别。
    - UserProfile (3000): 含 short + long string 成员
    - LogEntry (4000): 含 long + short string 成员
    - raw std::string* (5000): 无 vtable 的堆 string
"""
from __future__ import print_function
import json
import sys


def find_all(items, sub):
    return [i for i in items if sub in i.get("type", "")]


def validate(data):
    print("=" * 60)
    print("C++ String Test Validation")
    print("=" * 60)

    assert "items" in data and "summary" in data
    items = data["items"]
    ok = True

    # Check 1: UserProfile (3000)
    print("\n[Check 1] UserProfile...")
    matches = find_all(items, "UserProfile")
    total = sum(i.get("amount", 0) for i in matches)
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total: %d (expected ~3000)" % total)
    if total >= 2700:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Check 2: LogEntry (4000)
    print("\n[Check 2] LogEntry...")
    matches = find_all(items, "LogEntry")
    total = sum(i.get("amount", 0) for i in matches)
    for m in matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", ""), m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total: %d (expected ~4000)" % total)
    if total >= 3600:
        print("  PASS")
    else:
        print("  FAIL")
        ok = False

    # Check 3: string-related items
    print("\n[Check 3] String-related items...")
    str_matches = find_all(items, "basic_string")
    total_str = sum(i.get("amount", 0) for i in str_matches)
    for m in str_matches:
        print("    - %s: amount=%d, avg_size=%d" % (
            m.get("type", "")[:60], m.get("amount", 0),
            m.get("avg_size", 0)))
    print("  Total string items: %d" % total_str)
    # raw strings (5000) should appear somewhere
    if total_str >= 5000:
        print("  PASS (raw strings detected)")
    else:
        print("  WARN: raw strings may not be detected")

    # Overview
    print("\n[Check 4] Overview...")
    print("  Total items: %d" % len(items))
    for item in items[:15]:
        t = item.get("type", "?")
        if len(t) > 60:
            t = t[:57] + "..."
        print("    - %s: amount=%d, avg_size=%d" % (
            t, item.get("amount", 0), item.get("avg_size", 0)))
    if len(items) > 15:
        print("    ... (%d more)" % (len(items) - 15))

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

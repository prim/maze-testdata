#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jemalloc multithread validation.

Validation:
    - 16B..3MB buckets must achieve >= 99% detection rate.
    - Large buckets (1MB/2MB/3MB) must not exceed 110% of expected count.
"""
from __future__ import print_function
import json
import sys


EXPECTED = [
    (16, 20000, 0.99, None),
    (32, 20000, 0.99, None),
    (64, 20000, 0.99, None),
    (128, 10000, 0.99, None),
    (256, 10000, 0.99, None),
    (512, 10000, 0.99, None),
    (1024, 10000, 0.99, None),
    (1048576, 100, 0.99, 1.10),
    (2097152, 100, 0.99, 1.10),
    (3145728, 100, 0.99, 1.10),
]


def count_chunks_in_range(items, min_size, max_size):
    total = 0
    for item in items:
        avg_size = item.get("avg_size", 0)
        if min_size <= avg_size <= max_size:
            total += item.get("amount", 0)
    return total


def bucket_range(target_size):
    if target_size <= 1024:
        return target_size, target_size * 1.5
    return target_size * 0.85, target_size * 1.15


def format_size(target_size):
    if target_size >= 1048576:
        return "%dMB" % (target_size // 1048576)
    return "%dB" % target_size


def validate(data):
    print("=" * 70)
    print("jemalloc Multithread Test Validation")
    print("=" * 70)

    assert "items" in data, "Missing 'items'"
    assert "summary" in data, "Missing 'summary'"

    items = data["items"]
    summary = data["summary"]

    print("\n[Summary]")
    print("  VMS: %s" % summary.get("vms", "N/A"))
    print("  Total items: %d" % len(items))

    all_passed = True
    results = []

    print("\n[Per-Size Validation]")
    print("-" * 70)
    print("  %-10s %10s %10s %10s %8s %8s %s" % (
        "Size", "Expected", "Found", "Ratio", "MinReq", "MaxReq", "Status"))
    print("-" * 70)

    for target_size, expected_count, min_ratio, max_ratio in EXPECTED:
        min_size, max_size = bucket_range(target_size)
        found_count = count_chunks_in_range(items, min_size, max_size)
        ratio = found_count / float(expected_count) if expected_count > 0 else 0
        passed = ratio >= min_ratio
        if max_ratio is not None and ratio > max_ratio:
            passed = False

        size_str = format_size(target_size)
        max_req = ("%.0f%%" % (max_ratio * 100)) if max_ratio is not None else "-"
        status = "PASS" if passed else "FAIL"
        status_mark = "+" if passed else "x"

        print("  %-10s %10d %10d %9.2f%% %7.0f%% %8s [%s] %s" % (
            size_str, expected_count, found_count,
            ratio * 100, min_ratio * 100, max_req, status_mark, status))

        results.append({
            "size": target_size,
            "expected": expected_count,
            "found": found_count,
            "ratio": ratio,
            "passed": passed,
            "max_ratio": max_ratio,
        })
        if not passed:
            all_passed = False

    print("-" * 70)

    total_expected = sum(e[1] for e in EXPECTED)
    total_found = sum(r["found"] for r in results)
    overall_ratio = total_found / float(total_expected) if total_expected > 0 else 0

    print("\n[Overall Statistics]")
    print("  Total expected: %d" % total_expected)
    print("  Total found: %d" % total_found)
    print("  Overall ratio: %.2f%%" % (overall_ratio * 100))
    print("  Passed checks: %d/%d" % (sum(1 for r in results if r["passed"]), len(results)))

    print("\n" + "=" * 70)
    if all_passed:
        print("VALIDATION PASSED: All size categories meet configured thresholds")
    else:
        print("VALIDATION FAILED: Some size categories violate thresholds")
        print("\nFailed categories:")
        for r in results:
            if not r["passed"]:
                size_str = format_size(r["size"])
                if r["ratio"] < 0.99:
                    print("  - %s: %.2f%% (need >= 99%%)" % (size_str, r["ratio"] * 100))
                else:
                    print("  - %s: %.2f%% (need <= %.0f%%)" % (
                        size_str, r["ratio"] * 100, r["max_ratio"] * 100))
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    sys.exit(0 if validate(data) else 1)

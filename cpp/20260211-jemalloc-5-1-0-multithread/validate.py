#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jemalloc 5.1.0 Multithread Test Validation Script

Test program allocations:
    - 20000 x malloc(16)
    - 20000 x malloc(32)
    - 20000 x malloc(64)
    - 10000 x malloc(128)
    - 10000 x malloc(256)
    - 10000 x malloc(512)
    - 10000 x malloc(1024)
    - 100 x malloc(1MB)
    - 100 x malloc(2MB)
    - 100 x malloc(3MB)

Validation: Each size must achieve >= 99% detection rate.
"""
from __future__ import print_function
import json
import sys


# Expected allocations: (size_bytes, expected_count, min_ratio)
EXPECTED = [
    (16, 20000, 0.99),
    (32, 20000, 0.99),
    (64, 20000, 0.99),
    (128, 10000, 0.99),
    (256, 10000, 0.99),
    (512, 10000, 0.99),
    (1024, 10000, 0.99),
    (1048576, 100, 0.99),   # 1MB
    (2097152, 100, 0.99),   # 2MB
    (3145728, 100, 0.99),   # 3MB
]


def find_chunks_by_size(items, target_size, tolerance=0.15):
    """
    Find items matching the target size within tolerance.
    
    For small sizes (<=1024), jemalloc may round up:
      - 16 -> 16 or 24
      - 32 -> 32 or 40
      - 64 -> 64 or 72
      - etc.
    
    For large sizes (>=1MB), match within tolerance range.
    """
    results = []
    
    if target_size <= 1024:
        # Small blocks: match within +50% (jemalloc size class overhead)
        min_size = target_size
        max_size = target_size * 1.5
    else:
        # Large blocks: match within tolerance
        min_size = target_size * (1 - tolerance)
        max_size = target_size * (1 + tolerance)
    
    for item in items:
        avg_size = item.get("avg_size", 0)
        if min_size <= avg_size <= max_size:
            results.append(item)
    
    return results


def count_chunks_in_range(items, min_size, max_size):
    """Count total chunks within size range."""
    total = 0
    for item in items:
        avg_size = item.get("avg_size", 0)
        if min_size <= avg_size <= max_size:
            total += item.get("amount", 0)
    return total


def validate(data):
    """Validate maze analysis results."""
    print("=" * 70)
    print("jemalloc 5.1.0 Multithread Test Validation")
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
    print("  %-10s %10s %10s %10s %8s %s" % (
        "Size", "Expected", "Found", "Ratio", "MinReq", "Status"))
    print("-" * 70)

    for target_size, expected_count, min_ratio in EXPECTED:
        # Determine size range for matching
        if target_size <= 1024:
            # Small blocks: jemalloc rounds up, use size class matching
            min_size = target_size
            max_size = target_size * 1.5
        else:
            # Large blocks: 15% tolerance
            min_size = target_size * 0.85
            max_size = target_size * 1.15

        found_count = count_chunks_in_range(items, min_size, max_size)
        ratio = found_count / float(expected_count) if expected_count > 0 else 0
        passed = ratio >= min_ratio

        # Format size for display
        if target_size >= 1048576:
            size_str = "%dMB" % (target_size // 1048576)
        else:
            size_str = "%dB" % target_size

        status = "PASS" if passed else "FAIL"
        status_mark = "+" if passed else "x"

        print("  %-10s %10d %10d %9.2f%% %7.0f%% [%s] %s" % (
            size_str, expected_count, found_count, 
            ratio * 100, min_ratio * 100, status_mark, status))

        results.append({
            "size": target_size,
            "expected": expected_count,
            "found": found_count,
            "ratio": ratio,
            "passed": passed
        })

        if not passed:
            all_passed = False

    print("-" * 70)

    # Summary statistics
    total_expected = sum(e[1] for e in EXPECTED)
    total_found = sum(r["found"] for r in results)
    overall_ratio = total_found / float(total_expected) if total_expected > 0 else 0

    print("\n[Overall Statistics]")
    print("  Total expected: %d" % total_expected)
    print("  Total found: %d" % total_found)
    print("  Overall ratio: %.2f%%" % (overall_ratio * 100))

    passed_count = sum(1 for r in results if r["passed"])
    print("  Passed checks: %d/%d" % (passed_count, len(results)))

    # Final result
    print("\n" + "=" * 70)
    if all_passed:
        print("VALIDATION PASSED: All size categories meet 99%% detection threshold")
    else:
        print("VALIDATION FAILED: Some size categories below 99%% threshold")
        print("\nFailed categories:")
        for r in results:
            if not r["passed"]:
                if r["size"] >= 1048576:
                    size_str = "%dMB" % (r["size"] // 1048576)
                else:
                    size_str = "%dB" % r["size"]
                print("  - %s: %.2f%% (need >= 99%%)" % (size_str, r["ratio"] * 100))
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <maze-result.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    result = validate(data)
    sys.exit(0 if result else 1)

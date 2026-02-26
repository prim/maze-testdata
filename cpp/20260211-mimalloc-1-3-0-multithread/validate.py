#!/usr/bin/env python3
"""
Validation script for mimalloc 1.0.0 multithread test case.

Expected allocations:
- 20000 x 16 bytes
- 20000 x 32 bytes
- 20000 x 64 bytes
- 10000 x 128 bytes
- 10000 x 256 bytes
- 10000 x 512 bytes
- 10000 x 1024 bytes
- 100 x 1MB
- 100 x 2MB
- 100 x 3MB
"""

import json
import sys

def validate(data):
    """Validate maze analysis results.

    Args:
        data: dict (from run_test.py) or str (file path, from CLI)
    """
    if isinstance(data, str):
        with open(data, 'r') as f:
            data = json.load(f)

    items = data.get('items', [])

    # Build a map of size -> amount for all malloc items (including those with sub-structure)
    # mimalloc 不同版本的 huge page xblock_size 不同（1.8.0+ 用 page available space），
    # 同一个 size 的大块可能被 maze 拆成多条记录（有/无子结构），需要全部累加。
    #
    # 大块（>=1MB）也统计 "C++ unsigned char" 类型的条目：
    # maze 的分类器可能将 0xaa 填充的大块识别为原始内存而非 malloc 块，
    # 但这些块确实被 mimalloc walker 找到了，只是分类不同。
    size_to_amount = {}
    for item in items:
        t = item.get('type', '')
        avg_size = item.get('avg_size', 0)
        amount = item.get('amount', 0)
        if 'malloc(' in t:
            size_to_amount[avg_size] = size_to_amount.get(avg_size, 0) + amount
        elif 'C++ unsigned char' in t and avg_size >= 1048576:
            size_to_amount[avg_size] = size_to_amount.get(avg_size, 0) + amount

    print("=== mimalloc Multithread Test Validation ===")
    print()

    # 小块：精确匹配 size
    small_expected = {
        16: (20000, 0.95),
        32: (20000, 0.95),
        64: (20000, 0.95),
        128: (10000, 0.95),
        256: (10000, 0.95),
        512: (10000, 0.95),
        1024: (10000, 0.95),
    }

    # 大块：用范围匹配，因为 mimalloc 不同版本 xblock_size 不同
    # 1MB = 1048576, 2MB = 2097152, 3MB = 3145728
    # 实际 xblock_size 可能略大（如 2359040, 3407616），用 1.5x 上界
    large_expected = [
        ("1MB", 1048576, 1048576 * 1.5, 100, 0.95),
        ("2MB", 2097152, 2097152 * 1.5, 100, 0.95),
        ("3MB", 3145728, 3145728 * 1.5, 100, 0.95),
    ]

    all_passed = True

    for size, (expected_amount, tolerance) in small_expected.items():
        actual = size_to_amount.get(size, 0)
        min_expected = int(expected_amount * tolerance)
        passed = actual >= min_expected
        if not passed:
            all_passed = False
        status = "PASS" if passed else "FAIL"
        print(f"  {size:>10} bytes: {actual:>6} / {expected_amount:>6} (min: {min_expected}) {status}")

    for label, lo, hi, expected_amount, tolerance in large_expected:
        actual = sum(amt for sz, amt in size_to_amount.items() if lo <= sz < hi)
        min_expected = int(expected_amount * tolerance)
        # 找到实际匹配的 size 用于显示
        matched_sizes = [sz for sz in size_to_amount if lo <= sz < hi]
        size_info = f"{matched_sizes[0]}" if len(matched_sizes) == 1 else f"{label}"
        passed = actual >= min_expected
        if not passed:
            all_passed = False
        status = "PASS" if passed else "FAIL"
        print(f"  {size_info:>10} bytes: {actual:>6} / {expected_amount:>6} (min: {min_expected}) {status}  [{label}]")
    
    print()
    
    if all_passed:
        print("All validations passed!")
        return True
    else:
        print("Some validations failed!")
        return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <maze-result.json>")
        sys.exit(1)

    result = validate(sys.argv[1])
    sys.exit(0 if result else 1)

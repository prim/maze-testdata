#!/usr/bin/env python3
"""
Validation script for mimalloc 1.2.0 multithread test case.

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

    # Build a map of size -> amount for exact weak malloc items
    # Only match exact "(weak) malloc(N)" without sub-structure like "{...}"
    size_to_amount = {}
    for item in items:
        t = item.get('type', '')
        if t.startswith('(weak) malloc(') and '{' not in t:
            avg_size = item.get('avg_size', 0)
            amount = item.get('amount', 0)
            size_to_amount[avg_size] = size_to_amount.get(avg_size, 0) + amount

    print("=== mimalloc 1.2.0 Multithread Test Validation ===")
    print()

    # Expected allocations with tolerance
    # Small sizes: 95% tolerance (mimalloc tracks these precisely)
    # Large sizes: 95% tolerance
    expected = {
        16: (20000, 0.95),
        32: (20000, 0.95),
        64: (20000, 0.95),
        128: (10000, 0.95),
        256: (10000, 0.95),
        512: (10000, 0.95),
        1024: (10000, 0.95),
        1048576: (100, 0.95),   # 1MB
        2097152: (100, 0.95),   # 2MB
        3145728: (100, 0.95),   # 3MB
    }

    all_passed = True

    for size, (expected_amount, tolerance) in expected.items():
        actual = size_to_amount.get(size, 0)
        min_expected = int(expected_amount * tolerance)

        if actual >= min_expected:
            status = "PASS"
        else:
            status = "FAIL"
            all_passed = False

        print(f"  {size:>10} bytes: {actual:>6} / {expected_amount:>6} (min: {min_expected}) {status}")

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

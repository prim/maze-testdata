#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20260226-container-size 验证脚本

验证 Maze 对不同大小 Map/Set 的 size 计算是否准确。
用 heapsnapshot CLI (chrome-heapsnapshot-parser) 作为 ground truth。

注意: Maze 按 V8 Map (hidden class) 分组，所有 JSMap 实例共享同一个
hidden class，因此不同 entry 数的 Map 会合并到同一行 (如 <Map(50)>)。
验证策略: 对比合并后的 total_size 和 count。

用法:
  # Part 1 only: 验证类型计数
  python3 validate.py maze-result.json

  # Part 1 + Part 2: 验证类型计数 + size 对比
  python3 validate.py maze-result.json --heapsnapshot <file.heapsnapshot>
"""
from __future__ import print_function
import json, re, sys, os, subprocess


N = 200
SIZES = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
TOTAL_MAP = N * len(SIZES)  # 1100
TOTAL_SET = N * len(SIZES)  # 1100


# =====================================================================
# Helpers
# =====================================================================

def normalize_items(data):
    """兼容 maze-result.json (items/type) 和 postman.result.json (l0/name)。"""
    items = data.get("items") or []
    if items:
        return items
    l0 = data.get("l0") or []
    return [{"type": it.get("name", ""), "amount": it.get("amount", 0),
             "total_size": it.get("totalSizeBytes", 0),
             "avg_size": it.get("avgSize", 0)} for it in l0]


def find_all_matching(items, regex):
    """找到所有匹配正则的 item。"""
    return [it for it in items if regex.search(it.get("type", ""))]


def parse_size(size_str):
    """解析 '12.50 KB' 格式的大小字符串，返回字节数。"""
    parts = size_str.strip().split()
    if len(parts) != 2:
        return 0
    try:
        value = float(parts[0])
    except ValueError:
        return 0
    unit = parts[1].upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    return int(value * multipliers.get(unit, 1))


def human_size(n):
    """字节数转可读格式。"""
    if n < 1024:
        return "%d B" % n
    elif n < 1024 * 1024:
        return "%.1f KB" % (n / 1024.0)
    else:
        return "%.1f MB" % (n / (1024.0 * 1024))


# =====================================================================
# Part 1: 类型计数验证
# =====================================================================

def validate_counts(data, ok):
    """验证 Map/Set 的总 count >= TOTAL_MAP/TOTAL_SET。"""
    print("=" * 60)
    print("Part 1: Type Count Validation")
    print("=" * 60)

    items = normalize_items(data)
    if not items:
        print("  x No items found")
        ok[0] = False
        return None, None

    # 所有 Map 行合并计数
    map_items = find_all_matching(items, re.compile(r"^<Map\(\d+\)>$"))
    map_total = sum(it["amount"] for it in map_items)
    s = "v" if map_total >= TOTAL_MAP else "x"
    print("  %s Map total: %d (>= %d)" % (s, map_total, TOTAL_MAP))
    for it in map_items:
        print("    %s: amount=%d" % (it["type"], it["amount"]))
    if map_total < TOTAL_MAP:
        ok[0] = False

    # 所有 Set 行合并计数
    set_items = find_all_matching(items, re.compile(r"^<Set\(\d+\)>$"))
    set_total = sum(it["amount"] for it in set_items)
    s = "v" if set_total >= TOTAL_SET else "x"
    print("  %s Set total: %d (>= %d)" % (s, set_total, TOTAL_SET))
    for it in set_items:
        print("    %s: amount=%d" % (it["type"], it["amount"]))
    if set_total < TOTAL_SET:
        ok[0] = False

    return map_items, set_items


# =====================================================================
# Part 2: Heapsnapshot CLI 解析 + Size 对比
# =====================================================================

def run_heapsnapshot_cli(snapshot_path):
    """运行 heapsnapshot CLI，解析输出，返回 {name: {count, self_size}}。"""
    cmd = ["heapsnapshot", snapshot_path, "500"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = proc.stdout
    except FileNotFoundError:
        print("  Error: heapsnapshot command not found in PATH")
        return None
    except subprocess.TimeoutExpired:
        print("  Error: heapsnapshot timed out")
        return None

    result = {}
    in_table = False
    for line in output.split("\n"):
        if line.startswith("----"):
            in_table = not in_table
            continue
        if not in_table:
            continue
        line = line.rstrip()
        if not line or line.startswith("Total"):
            continue

        m = re.match(
            r"\s*(\d+)\s+"           # rank
            r"(\S+)\s+"              # type
            r"(.{1,40}?)\s{2,}"     # name
            r"(\d+)\s+"             # count
            r"([\d.]+\s+\w+)\s+"    # self size
            r"([\d.]+\s+\w+)",      # retained size
            line
        )
        if not m:
            continue

        name = m.group(3).strip()
        count = int(m.group(4))
        self_size = parse_size(m.group(5).strip())

        result[name] = {
            "count": count,
            "self_size": self_size,
        }

    return result


def validate_sizes(maze_data, snapshot_path, ok):
    """Part 2: 对比 Maze 和 heapsnapshot CLI 的 Map/Set size。"""
    print("\n" + "=" * 60)
    print("Part 2: Size Comparison (Maze vs heapsnapshot CLI)")
    print("=" * 60)

    heap = run_heapsnapshot_cli(snapshot_path)
    if heap is None:
        print("  x Failed to run heapsnapshot CLI")
        ok[0] = False
        return

    print("  Heapsnapshot types loaded: %d" % len(heap))

    items = normalize_items(maze_data)

    for kind in ("Map", "Set"):
        print("\n  --- %s ---" % kind)

        # Maze: 合并所有 <Map(N)> / <Set(N)> 行
        regex = re.compile(r"^<%s\(\d+\)>$" % kind)
        maze_items = find_all_matching(items, regex)
        maze_count = sum(it["amount"] for it in maze_items)
        maze_total = sum(it["total_size"] for it in maze_items)

        # Heapsnapshot CLI
        heap_info = heap.get(kind)
        if not heap_info:
            print("  x %s not found in heapsnapshot output" % kind)
            ok[0] = False
            continue

        heap_count = heap_info["count"]
        heap_total = heap_info["self_size"]

        print("  Maze:  count=%d  total_size=%s (%d)" % (
            maze_count, human_size(maze_total), maze_total))
        print("  Heap:  count=%d  self_size=%s (%d)" % (
            heap_count, human_size(heap_total), heap_total))

        # count 对比: Maze >= heap (Maze 可能多几个系统内置的)
        count_ok = maze_count >= heap_count - 5  # 允许少量差异
        s = "v" if count_ok else "x"
        print("  %s count: maze=%d heap=%d (diff=%+d)" % (
            s, maze_count, heap_count, maze_count - heap_count))
        if not count_ok:
            ok[0] = False

        # size 对比: 允许 5% 误差
        if heap_total > 0:
            ratio = maze_total / float(heap_total)
            pct = abs(ratio - 1.0) * 100
            size_ok = pct < 5.0
            s = "v" if size_ok else "x"
            print("  %s total_size: ratio=%.4f (%.1f%% diff)" % (
                s, ratio, pct))
            if not size_ok:
                ok[0] = False
        else:
            print("  ? heap total_size is 0, skip ratio check")


# =====================================================================
# Main
# =====================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate.py <maze-result.json> "
              "[--heapsnapshot <file.heapsnapshot>]")
        sys.exit(1)

    json_path = sys.argv[1]
    snapshot_path = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--heapsnapshot" and i + 1 < len(sys.argv):
            snapshot_path = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    ok = [True]

    # Part 1: 类型计数验证
    with open(json_path, "r") as f:
        data = json.load(f)
    validate_counts(data, ok)

    # Part 2: size 对比
    if snapshot_path:
        validate_sizes(data, snapshot_path, ok)
    else:
        print("\n  (no --heapsnapshot provided, skipping Part 2)")

    # Summary
    print("\n" + "=" * 60)
    if ok[0]:
        print("All validations passed!")
    else:
        print("FAILED: some validations did not pass")
    print("=" * 60)
    sys.exit(0 if ok[0] else 1)


if __name__ == "__main__":
    main()

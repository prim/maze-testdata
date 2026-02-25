#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maze vs chrome-heapsnapshot-parser 对比脚本

用法:
    python3 compare.py <maze-result.json> <heapsnapshot-file>

功能:
    1. 读取 maze-result.json
    2. 运行 heapsnapshot CLI 并解析输出
    3. 建立类型映射表
    4. 对比每种类型的 count 和 size
    5. 输出差异报告
"""
from __future__ import print_function

import json
import re
import subprocess
import sys
import os


def parse_maze_result(json_path):
    """解析 maze-result.json，返回 {type_name: {amount, total_size}} 字典"""
    with open(json_path, 'r') as f:
        data = json.load(f)

    items = data.get('items', [])
    result = {}
    for item in items:
        result[item['type']] = {
            'amount': item.get('amount', 0),
            'total_size': item.get('total_size', 0),
            'avg_size': item.get('avg_size', 0),
        }
    return result


def parse_size(size_str):
    """解析 '12.50 KB' 格式的大小字符串，返回字节数"""
    parts = size_str.strip().split()
    if len(parts) != 2:
        return 0
    try:
        value = float(parts[0])
    except ValueError:
        return 0
    unit = parts[1].upper()
    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
    return int(value * multipliers.get(unit, 1))


def parse_heapsnapshot_output(snapshot_path, top_n=500):
    """运行 heapsnapshot CLI 并解析文本输出，返回 {class_name: {count, self_size, retained_size}} 字典"""
    cmd = ['heapsnapshot', snapshot_path, str(top_n)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = proc.stdout
    except FileNotFoundError:
        print("Error: heapsnapshot command not found in PATH")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: heapsnapshot timed out")
        sys.exit(1)

    result = {}
    # 解析表格行: "   1  object               ClassName                                    500     12.50 KB       25.00 KB"
    # 格式: Rank  Type(22)  Name(40)  Count(8)  SelfSize(12)  RetainedSize(15)
    in_table = False
    for line in output.split('\n'):
        if line.startswith('----'):
            in_table = not in_table
            continue
        if not in_table:
            continue
        line = line.rstrip()
        if not line or line.startswith('Total'):
            continue

        # 用固定宽度解析
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            int(parts[0])  # rank 必须是数字
        except ValueError:
            continue

        # 重新用正则解析，更可靠
        m = re.match(
            r'\s*(\d+)\s+'           # rank
            r'(\S+)\s+'              # type
            r'(.{1,40}?)\s{2,}'     # name (可能含空格，用 2+ 空格分隔)
            r'(\d+)\s+'             # count
            r'([\d.]+\s+\w+)\s+'    # self size
            r'([\d.]+\s+\w+)',      # retained size
            line
        )
        if not m:
            continue

        type_field = m.group(2).strip()
        name_field = m.group(3).strip()
        count = int(m.group(4))
        self_size_str = m.group(5).strip()
        retained_size_str = m.group(6).strip()

        self_size = parse_size(self_size_str)
        retained_size = parse_size(retained_size_str)

        # 用 "type::name" 作为 key
        key = name_field if name_field else type_field
        result[key] = {
            'type': type_field,
            'name': name_field,
            'count': count,
            'self_size': self_size,
            'retained_size': retained_size,
        }

    return result


# 对比映射表
# 每行: (描述, maze_pattern, heap_pattern)
#   maze_pattern: 在 maze type 名中搜索的子串
#   heap_pattern: 在 heapsnapshot name 中搜索的子串
#
# 注意: Maze 的类型名格式如 "{Object: id, name}", "<Uint8Array(2)>", "(Date)" 等
#       heapsnapshot 的 name 字段是 V8 className，如 "Object", "Uint8Array", "Date" 等
TYPE_MAPPINGS = [
    # 基础类型
    ('Object',          'Object: id, name, value, nested',  'Object'),
    ('Array(dense+sparse)', None,                           'Array'),       # Maze 不单独列 Array
    ('String wrapper',  '{String: length}',                 'String'),      # Maze: {String: length}
    ('Number wrapper',  None,                               'Number'),      # Maze 未识别为独立类型
    ('Boolean wrapper', None,                               'Boolean'),     # Maze 未识别为独立类型
    # 集合
    ('Map',             '<Map(',                             'Map'),
    ('Set',             '<Set(',                             'Set'),
    ('WeakMap',         '<WeakMap(',                         'WeakMap'),
    ('WeakSet',         '<WeakSet(',                         'WeakSet'),
    # TypedArray
    ('Uint8Array',      '<Uint8Array(2)>',                  'Uint8Array'),
    ('Int32Array',      '<Int32Array',                       'Int32Array'),
    ('Float64Array',    '<Float64Array',                     'Float64Array'),
    # 内置对象
    ('Date',            '(Date)',                            'Date'),
    ('RegExp',          '(RegExp)',                          'RegExp'),
    ('Error',           'errors @errors',                    'Error'),
    ('TypeError',       'TypeError',                         'TypeError'),
    ('Promise',         '<Promise(pending)>',                'Promise'),
    # 函数
    ('Function',        'namedFunc @test.js',                'Function'),
    ('ArrowFunction',   'ArrowFunction: test.js',            'Function'),
    ('AsyncFunction',   'AsyncFunction: asyncFn',            'Function'),
    # 自定义类
    ('SimpleClass',     'SimpleClass',                       'SimpleClass'),
    ('Dog',             'Dog',                               'Dog'),
    # Node.js 核心
    ('EventEmitter',    'EventEmitter',                      'EventEmitter'),
    ('Buffer',          'ArrayBuffer',                       'ArrayBuffer'),
    ('URL',             'URLContext',                         'URL'),
]


def human_size(n):
    """字节数转可读格式"""
    if n < 1024:
        return '%d B' % n
    elif n < 1024 * 1024:
        return '%.1f KB' % (n / 1024.0)
    else:
        return '%.1f MB' % (n / (1024.0 * 1024))


def find_maze_type(maze_data, pattern):
    """在 maze 结果中查找包含 pattern 的类型"""
    for type_name, info in maze_data.items():
        if pattern.lower() in type_name.lower():
            return type_name, info
    return None, None


def find_heap_type(heap_data, pattern):
    """在 heapsnapshot 结果中查找匹配 pattern 的类型"""
    for key, info in heap_data.items():
        if pattern.lower() == key.lower() or pattern.lower() == info.get('name', '').lower():
            return key, info
    # 模糊匹配
    for key, info in heap_data.items():
        if pattern.lower() in key.lower() or pattern.lower() in info.get('name', '').lower():
            return key, info
    return None, None


def compare(maze_data, heap_data):
    """对比两个工具的分析结果"""
    print('=' * 100)
    print('Maze vs chrome-heapsnapshot-parser 对比报告')
    print('=' * 100)
    print()

    # 表头
    hdr = '%-20s  %8s %10s  |  %8s %10s  |  %8s' % (
        'Type', 'Maze#', 'MazeSize', 'Heap#', 'HeapSize', 'CountDiff')
    print(hdr)
    print('-' * 100)

    matched = 0
    missing_maze = 0
    missing_heap = 0

    for desc, maze_pattern, heap_pattern in TYPE_MAPPINGS:
        # 在 maze 结果中查找
        if maze_pattern:
            maze_name, maze_info = find_maze_type(maze_data, maze_pattern)
        else:
            maze_name, maze_info = None, None
        # 在 heapsnapshot 结果中查找
        heap_name, heap_info = find_heap_type(heap_data, heap_pattern)

        maze_count = maze_info['amount'] if maze_info else 0
        maze_size = human_size(maze_info['total_size']) if maze_info else '-'
        heap_count = heap_info['count'] if heap_info else 0
        heap_size = human_size(heap_info['self_size']) if heap_info else '-'

        if maze_count > 0 and heap_count > 0:
            diff = maze_count - heap_count
            diff_str = '%+d' % diff if diff != 0 else '='
            matched += 1
        elif maze_count == 0:
            diff_str = 'NO MAZE'
            missing_maze += 1
        else:
            diff_str = 'NO HEAP'
            missing_heap += 1

        label = desc
        if len(label) > 20:
            label = label[:17] + '...'
        print('%-20s  %8d %10s  |  %8d %10s  |  %8s' % (
            label, maze_count, maze_size, heap_count, heap_size, diff_str))

    print('-' * 100)
    print()
    print('Summary:')
    print('  Matched types:      %d' % matched)
    print('  Missing in Maze:    %d' % missing_maze)
    print('  Missing in Heap:    %d' % missing_heap)
    print()

    # 输出 Maze 中的 top 20 类型
    print('=' * 100)
    print('Maze Top 20 (by total_size)')
    print('=' * 100)
    sorted_maze = sorted(maze_data.items(), key=lambda x: x[1]['total_size'], reverse=True)
    for i, (name, info) in enumerate(sorted_maze[:20]):
        print('  %3d  %8d  %10s  %s' % (
            i + 1, info['amount'], human_size(info['total_size']), name))
    print()

    # 输出 heapsnapshot 中的 top 20 类型
    print('=' * 100)
    print('Heapsnapshot Top 20 (by self_size)')
    print('=' * 100)
    sorted_heap = sorted(heap_data.items(), key=lambda x: x[1]['self_size'], reverse=True)
    for i, (name, info) in enumerate(sorted_heap[:20]):
        print('  %3d  %8d  %10s  %s [%s]' % (
            i + 1, info['count'], human_size(info['self_size']),
            info.get('name', name), info.get('type', '')))
    print()


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 compare.py <maze-result.json> <heapsnapshot-file>')
        print()
        print('Example:')
        print('  python3 compare.py /tmp/maze-result-comparison.json *.heapsnapshot')
        sys.exit(1)

    maze_json = sys.argv[1]
    snapshot_file = sys.argv[2]

    if not os.path.exists(maze_json):
        print('Error: %s not found' % maze_json)
        sys.exit(1)
    if not os.path.exists(snapshot_file):
        print('Error: %s not found' % snapshot_file)
        sys.exit(1)

    print('Maze result:    %s' % maze_json)
    print('Heapsnapshot:   %s' % snapshot_file)
    print()

    maze_data = parse_maze_result(maze_json)
    print('Maze types loaded: %d' % len(maze_data))

    heap_data = parse_heapsnapshot_output(snapshot_file)
    print('Heapsnapshot types loaded: %d' % len(heap_data))
    print()

    if not heap_data:
        print('Warning: No data parsed from heapsnapshot output.')
        print('Try running manually: heapsnapshot %s 500' % snapshot_file)
        sys.exit(1)

    compare(maze_data, heap_data)


if __name__ == '__main__':
    main()

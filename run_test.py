#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Maze 测试运行器

用法:
    python testdata/run_test.py python/20260128-basic

功能:
    1. 进入指定测试目录
    2. 执行 maze --tar 分析 coredump
    3. 加载 maze-result.json
    4. 调用测试目录下的 validate.py 进行验证
"""

from __future__ import print_function

import os
import sys
import json
import glob
import importlib
import subprocess


def find_tarball(test_dir):
    """查找测试目录下的 tar.gz 文件"""
    pattern = os.path.join(test_dir, "*.tar.gz")
    files = glob.glob(pattern)
    if not files:
        raise RuntimeError("No tar.gz file found in %s" % test_dir)
    if len(files) > 1:
        print("Warning: Multiple tar.gz files found, using: %s" % files[0])
    return files[0]


def run_maze_analysis(tarball_path):
    """执行 maze 分析"""
    # 获取 maze 根目录（testdata 的父目录）
    testdata_dir = os.path.dirname(os.path.abspath(__file__))
    maze_root = os.path.dirname(testdata_dir)
    maze_script = os.path.join(maze_root, "maze")
    
    cmd = [
        sys.executable,
        maze_script,
        "--tar", tarball_path,
        "--text",
        "--json-output",
        "--limit", "500"
    ]
    
    print("=" * 60)
    print("Running Maze Analysis")
    print("=" * 60)
    print("Command: %s" % " ".join(cmd))
    print("-" * 60)
    
    # 在 maze 根目录执行
    ret = subprocess.call(cmd, cwd=maze_root)
    
    if ret != 0:
        raise RuntimeError("Maze analysis failed with exit code %d" % ret)
    
    # 返回结果文件路径
    result_path = os.path.join(maze_root, "maze-result.json")
    return result_path


def load_validate_module(test_dir):
    """加载测试目录下的 validate.py 模块"""
    validate_path = os.path.join(test_dir, "validate.py")
    
    if not os.path.exists(validate_path):
        raise RuntimeError("validate.py not found in %s" % test_dir)
    
    # Python 2/3 兼容的模块加载
    if sys.version_info[0] >= 3:
        import importlib.util
        spec = importlib.util.spec_from_file_location("validate", validate_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        import imp
        module = imp.load_source("validate", validate_path)
    
    return module


def run_test(test_dir):
    """
    运行单个测试
    
    Args:
        test_dir: 测试目录路径 (相对于 testdata 目录)
    
    Returns:
        bool: 测试是否通过
    """
    # 转换为绝对路径
    testdata_dir = os.path.dirname(os.path.abspath(__file__))
    abs_test_dir = os.path.join(testdata_dir, test_dir)
    
    if not os.path.isdir(abs_test_dir):
        raise RuntimeError("Test directory not found: %s" % abs_test_dir)
    
    print("")
    print("=" * 60)
    print("Test: %s" % test_dir)
    print("=" * 60)
    
    # 1. 查找 tarball
    tarball = find_tarball(abs_test_dir)
    print("Tarball: %s" % tarball)
    
    # 2. 执行 maze 分析
    result_path = run_maze_analysis(tarball)
    
    # 3. 加载结果
    if not os.path.exists(result_path):
        raise RuntimeError("Result file not found: %s" % result_path)
    
    with open(result_path, "r") as f:
        data = json.load(f)
    
    print("")
    print("=" * 60)
    print("Validating Results")
    print("=" * 60)
    
    # 4. 加载验证模块
    validate_module = load_validate_module(abs_test_dir)
    
    # 5. 执行验证
    try:
        result = validate_module.validate(data)
        if result:
            print("")
            print("✅ Test PASSED: %s" % test_dir)
            return True
        else:
            print("")
            print("❌ Test FAILED: %s" % test_dir)
            return False
    except AssertionError as e:
        print("")
        print("❌ Test FAILED: %s" % test_dir)
        print("   Assertion Error: %s" % str(e))
        return False
    except Exception as e:
        print("")
        print("❌ Test ERROR: %s" % test_dir)
        print("   Exception: %s" % str(e))
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_test.py <test_dir>")
        print("")
        print("Examples:")
        print("  python testdata/run_test.py python/20260128-basic")
        print("  python testdata/run_test.py python/20260128-basic python/20260129-leak")
        sys.exit(1)
    
    test_dirs = sys.argv[1:]
    results = []
    
    for test_dir in test_dirs:
        try:
            passed = run_test(test_dir)
            results.append((test_dir, passed))
        except Exception as e:
            print("")
            print("❌ Test ERROR: %s" % test_dir)
            print("   %s" % str(e))
            results.append((test_dir, False))
    
    # 打印汇总
    print("")
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed_count = 0
    failed_count = 0
    
    for test_dir, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print("  %s: %s" % (test_dir, status))
        if passed:
            passed_count += 1
        else:
            failed_count += 1
    
    print("-" * 60)
    print("Total: %d passed, %d failed" % (passed_count, failed_count))
    print("=" * 60)
    
    # 返回退出码
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()

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


def run_maze_analysis(tarball_path, py_merge=False):
    """执行 maze 分析
    
    Args:
        tarball_path: tar.gz 文件路径
        py_merge: 是否启用 --py-merge 模式
    """
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
    
    if py_merge:
        cmd.append("--py-merge")
    
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


def run_test(test_dir, py_merge=False):
    """
    运行单个测试
    
    Args:
        test_dir: 测试目录路径 (相对于 testdata 目录)
        py_merge: 是否启用 --py-merge 模式
    
    Returns:
        bool: 测试是否通过
    """
    # 转换为绝对路径
    testdata_dir = os.path.dirname(os.path.abspath(__file__))
    maze_root = os.path.dirname(testdata_dir)
    abs_test_dir = os.path.join(testdata_dir, test_dir)
    
    if not os.path.isdir(abs_test_dir):
        raise RuntimeError("Test directory not found: %s" % abs_test_dir)
    
    mode_str = " (--py-merge)" if py_merge else ""
    print("")
    print("=" * 60)
    print("Test: %s%s" % (test_dir, mode_str))
    print("=" * 60)
    
    # 1. 查找 tarball
    tarball = find_tarball(abs_test_dir)
    print("Tarball: %s" % tarball)
    
    # 2. 执行 maze 分析
    result_path = run_maze_analysis(tarball, py_merge=py_merge)
    
    # 3. 加载结果
    if not os.path.exists(result_path):
        raise RuntimeError("Result file not found: %s" % result_path)
    
    with open(result_path, "r") as f:
        data = json.load(f)
    
    # 如果是 py_merge 模式，保存结果到单独文件
    if py_merge:
        merge_result_path = os.path.join(maze_root, "maze-result-with-merge.json")
        with open(merge_result_path, "w") as f:
            json.dump(data, f, indent=2)
        print("PyMerge result saved to: %s" % merge_result_path)
    
    print("")
    print("=" * 60)
    print("Validating Results%s" % mode_str)
    print("=" * 60)
    
    # 4. 加载验证模块
    validate_module = load_validate_module(abs_test_dir)
    
    # 5. 设置环境变量告知 validate.py 当前模式
    if py_merge:
        os.environ["MAZE_PY_MERGE"] = "1"
    else:
        os.environ["MAZE_PY_MERGE"] = "0"
    
    # 6. 执行验证
    try:
        result = validate_module.validate(data)
        if result:
            print("")
            print("✅ Test PASSED: %s%s" % (test_dir, mode_str))
            return True
        else:
            print("")
            print("❌ Test FAILED: %s%s" % (test_dir, mode_str))
            return False
    except AssertionError as e:
        print("")
        print("❌ Test FAILED: %s%s" % (test_dir, mode_str))
        print("   Assertion Error: %s" % str(e))
        return False
    except Exception as e:
        print("")
        print("❌ Test ERROR: %s%s" % (test_dir, mode_str))
        print("   Exception: %s" % str(e))
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_test.py [--py-merge] <test_dir> [test_dir2 ...]")
        print("")
        print("Options:")
        print("  --py-merge    Also run tests with --py-merge mode")
        print("")
        print("Examples:")
        print("  python testdata/run_test.py python/20260128-basic")
        print("  python testdata/run_test.py --py-merge python/20260201-class-merge")
        sys.exit(1)
    
    # 解析参数
    args = sys.argv[1:]
    enable_py_merge = False
    test_dirs = []
    
    for arg in args:
        if arg == "--py-merge":
            enable_py_merge = True
        else:
            test_dirs.append(arg)
    
    if not test_dirs:
        print("Error: No test directories specified")
        sys.exit(1)
    
    results = []
    
    for test_dir in test_dirs:
        # 普通模式测试
        try:
            passed = run_test(test_dir)
            results.append((test_dir, passed))
        except Exception as e:
            print("")
            print("❌ Test ERROR: %s" % test_dir)
            print("   %s" % str(e))
            results.append((test_dir, False))
        
        # --py-merge 模式测试
        if enable_py_merge:
            try:
                passed = run_test(test_dir, py_merge=True)
                results.append(("%s (--py-merge)" % test_dir, passed))
            except Exception as e:
                print("")
                print("❌ Test ERROR: %s (--py-merge)" % test_dir)
                print("   %s" % str(e))
                results.append(("%s (--py-merge)" % test_dir, False))
    
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

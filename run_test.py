#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import io
import sys
import os
import json
import glob
import importlib
import subprocess
import shutil
import tarfile
import errno


if sys.version_info[0] >= 3:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def make_log_name(test_dir, py_merge=False):
    """生成稳定的日志文件名"""
    name = test_dir.replace(os.sep, "-").replace("/", "-")
    if py_merge:
        name += "-py-merge"
    return name


def ensure_dir(path):
    """确保目录存在，兼容 Python 2/3"""
    if os.path.isdir(path):
        return

    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            return
        raise RuntimeError("Failed to create directory %s: %s" % (path, str(e)))


def print_output_excerpt(output, max_lines=40):
    """打印输出末尾片段，便于快速定位问题"""
    if not output:
        return

    lines = output.splitlines()
    if len(lines) <= max_lines:
        print(output)
        return

    print("Maze output tail (%d/%d lines):" % (max_lines, len(lines)))
    print("...")
    print("\n".join(lines[-max_lines:]))


def find_tarball(test_dir):
    """查找测试目录下的 tar.gz 文件"""
    pattern = os.path.join(test_dir, "*.tar.gz")
    files = glob.glob(pattern)
    if not files:
        raise RuntimeError("No tar.gz file found in %s" % test_dir)
    if len(files) > 1:
        print("Warning: Multiple tar.gz files found, using: %s" % files[0])
    return files[0]


def cleanup_postman_db(maze_root, tarball_path):
    """清理 postman-db 目录中与当前测试相关的子目录

    根据 tarball 文件名解析 pid，清理对应的 postman-db 子目录，
    避免多个测试之间的状态干扰。
    """
    import tarfile
    import re

    postman_db_dir = os.path.join(maze_root, "postman-db")
    if not os.path.exists(postman_db_dir):
        return

    # 从 tar 文件中解析 pid
    pid = None
    try:
        with tarfile.open(tarball_path, "r:gz") as tf:
            for member in tf:
                name = member.name
                if name.startswith("./core."):
                    pid = name.split("./core.")[1]
                    break
                if name.startswith("core."):
                    pid = name.split("core.")[1]
                    break
    except Exception:
        pass

    if not pid:
        return

    # 清理匹配的 postman-db 子目录
    # 目录格式: coredump-default-{pid} 或类似格式
    cleaned = False
    for dirname in os.listdir(postman_db_dir):
        if pid in dirname:
            dir_path = os.path.join(postman_db_dir, dirname)
            if os.path.isdir(dir_path):
                try:
                    import shutil

                    shutil.rmtree(dir_path)
                    cleaned = True
                    print("Cleaned postman-db cache: %s" % dirname)
                except Exception as e:
                    print(
                        "Warning: Failed to clean postman-db cache %s: %s"
                        % (dirname, str(e))
                    )


def snapshot_log_files(maze_root):
    """记录当前可见的 maze 日志文件及其 mtime。"""
    snapshots = {}
    patterns = [
        os.path.join(maze_root, "postman-db", "*", "maze.log"),
        os.path.join(maze_root, "postman-db", "*", "maze.py.log"),
        os.path.join(maze_root, "maze.log"),
        os.path.join(maze_root, "maze.py.log"),
    ]

    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                snapshots[path] = os.path.getmtime(path)
            except OSError:
                pass

    return snapshots


def detect_updated_log_files(maze_root, before_snapshots):
    """查找本次运行更新过的日志文件。"""
    current_snapshots = snapshot_log_files(maze_root)
    updated = []

    for path, mtime in current_snapshots.items():
        if path not in before_snapshots or before_snapshots[path] != mtime:
            updated.append((mtime, path))

    updated.sort(reverse=True)
    return [path for _, path in updated]


def find_latest_log_file(maze_root, filename):
    """返回最新的指定日志文件路径。"""
    candidates = []
    patterns = [
        os.path.join(maze_root, filename),
        os.path.join(maze_root, "postman-db", "*", filename),
    ]

    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                candidates.append((os.path.getmtime(path), path))
            except OSError:
                pass

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]


def extract_log_paths_from_output(output, maze_root):
    """从 maze 控制台输出中提取日志路径。"""
    maze_log_path = None
    maze_py_log_path = None

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("log file "):
            candidate = line[len("log file ") :].strip()
            if candidate:
                maze_log_path = os.path.abspath(os.path.join(maze_root, candidate))
        elif line.startswith("python log file "):
            candidate = line[len("python log file ") :].strip()
            if candidate:
                maze_py_log_path = os.path.abspath(os.path.join(maze_root, candidate))

    return maze_log_path, maze_py_log_path


def run_maze_analysis(
    tarball_path, test_dir, py_merge=False, no_cpp=False, verbose_maze=False
):
    """执行 maze 分析

    Args:
        tarball_path: tar.gz 文件路径
        test_dir: 测试目录路径（用于日志命名）
        py_merge: 是否启用 --py-merge 模式
        no_cpp: 是否禁用 C++ 对象分析
        verbose_maze: 是否直接打印完整 maze 输出
    """
    # 获取 maze 根目录（testdata 的父目录）
    testdata_dir = os.path.dirname(os.path.abspath(__file__))
    maze_root = os.path.dirname(testdata_dir)
    maze_script = os.path.join(maze_root, "maze")

    cmd = [
        sys.executable,
        maze_script,
        "--tar",
        tarball_path,
        "--text",
        "--json-output",
        "--rmlog",
        "--limit",
        "500",
    ]

    if py_merge:
        cmd.append("--py-merge")

    if no_cpp:
        cmd.append("--no-cpp")

    print("Running Maze Analysis")
    print("Command: %s" % " ".join(cmd))

    # 清理旧的结果文件，避免残留文件导致误判
    result_path = os.path.join(maze_root, "maze-result.json")
    if os.path.exists(result_path):
        os.remove(result_path)

    # 清理 postman-db 缓存，避免测试之间的状态干扰
    cleanup_postman_db(maze_root, tarball_path)

    before_log_snapshots = snapshot_log_files(maze_root)

    tmp_dir = os.path.join(maze_root, "tmp")
    ensure_dir(tmp_dir)

    log_name = make_log_name(test_dir, py_merge=py_merge)
    maze_output_path = os.path.join(tmp_dir, "%s.maze-output.log" % log_name)

    # 在 maze 根目录执行
    process = subprocess.Popen(
        cmd,
        cwd=maze_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    output, _ = process.communicate()

    try:
        with io.open(maze_output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(output)
    except IOError as e:
        raise RuntimeError(
            "Failed to write maze output log %s: %s" % (maze_output_path, str(e))
        )

    ret = process.returncode

    if verbose_maze and output:
        print(output)
    else:
        print("Maze output saved to: %s" % maze_output_path)

    maze_log_path, maze_py_log_path = extract_log_paths_from_output(output, maze_root)
    updated_log_files = detect_updated_log_files(maze_root, before_log_snapshots)

    for path in updated_log_files:
        if path.endswith("maze.log") and maze_log_path is None:
            maze_log_path = path
        elif path.endswith("maze.py.log") and maze_py_log_path is None:
            maze_py_log_path = path

    if maze_log_path is None:
        maze_log_path = find_latest_log_file(maze_root, "maze.log")
    if maze_py_log_path is None:
        maze_py_log_path = find_latest_log_file(maze_root, "maze.py.log")

    if maze_log_path:
        print("Maze log: %s" % maze_log_path)
    if maze_py_log_path:
        print("Maze py log: %s" % maze_py_log_path)

    if ret != 0:
        print_output_excerpt(output)
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


def run_test(test_dir, py_merge=False, verbose_maze=False):
    """
    运行单个测试

    Args:
        test_dir: 测试目录路径 (相对于 testdata 目录)
        py_merge: 是否启用 --py-merge 模式
        verbose_maze: 是否直接打印完整 maze 输出

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
    print("Test: %s%s" % (test_dir, mode_str))

    # 1. 查找 tarball
    tarball = find_tarball(abs_test_dir)
    print("Tarball: %s" % tarball)

    # 检测 no-cpp 标记文件
    no_cpp = os.path.exists(os.path.join(abs_test_dir, "no-cpp"))

    # 2. 执行 maze 分析
    result_path = run_maze_analysis(
        tarball,
        test_dir,
        py_merge=py_merge,
        no_cpp=no_cpp,
        verbose_maze=verbose_maze,
    )

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
    print("Validating Results%s" % mode_str)

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
        print(
            "Usage: python run_test.py [--py-merge] [--verbose-maze] <test_dir> [test_dir2 ...]"
        )
        print("")
        print("Options:")
        print("  --py-merge    Also run tests with --py-merge mode")
        print("  --verbose-maze  Print full maze output instead of saving it to tmp/")
        print("")
        print("Examples:")
        print("  python testdata/run_test.py python/20260128-basic")
        print("  python testdata/run_test.py --py-merge python/20260201-class-merge")
        sys.exit(1)

    # 解析参数
    args = sys.argv[1:]
    enable_py_merge = False
    verbose_maze = False
    test_dirs = []

    for arg in args:
        if arg == "--py-merge":
            enable_py_merge = True
        elif arg == "--verbose-maze":
            verbose_maze = True
        else:
            test_dirs.append(arg)

    if not test_dirs:
        print("Error: No test directories specified")
        sys.exit(1)

    results = []

    for test_dir in test_dirs:
        # 普通模式测试
        try:
            passed = run_test(test_dir, verbose_maze=verbose_maze)
            results.append((test_dir, passed))
        except Exception as e:
            print("")
            print("❌ Test ERROR: %s" % test_dir)
            print("   %s" % str(e))
            results.append((test_dir, False))

        # --py-merge 模式测试
        if enable_py_merge:
            try:
                passed = run_test(test_dir, py_merge=True, verbose_maze=verbose_maze)
                results.append(("%s (--py-merge)" % test_dir, passed))
            except Exception as e:
                print("")
                print("❌ Test ERROR: %s (--py-merge)" % test_dir)
                print("   %s" % str(e))
                results.append(("%s (--py-merge)" % test_dir, False))

    # 打印汇总
    print("")
    print("Test Summary")

    passed_count = 0
    failed_count = 0

    for test_dir, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print("  %s: %s" % (test_dir, status))
        if passed:
            passed_count += 1
        else:
            failed_count += 1

    print("Total: %d passed, %d failed" % (passed_count, failed_count))

    # 返回退出码
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()

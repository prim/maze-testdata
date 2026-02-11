#!/usr/bin/env python3
"""
Create mimalloc test cases for versions 1.1 to 1.9
Based on the 1.0.0 test case template

Usage:
    python3 create_mimalloc_testcases.py [--version 1-1-0] [--all]
    
Reference: dev-log/2026-02-01-how-to-create-testcase.md
"""

import os
import sys
import shutil
import subprocess
import time
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
TESTDATA_CPP = SCRIPT_DIR
CMD_DIR = ROOT_DIR / "cmd"

# mimalloc versions to test
ALL_VERSIONS = [
    "1-1-0",
    "1-2-0",
    "1-3-0",
    "1-4-0",
    "1-5-0",
    "1-6-0",
    "1-7-0",
    "1-8-0",
    "1-9-2",
]

# Date prefix for test case directories
DATE_PREFIX = "20260211"

# Source template directory
TEMPLATE_DIR = TESTDATA_CPP / "20260211-mimalloc-1-0-0-multithread"


def run_cmd(cmd, cwd=None, timeout=None, check=False):
    """Run a command and return the result"""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr}")
        if check:
            raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def create_testcase(version):
    """Create a test case for a specific mimalloc version"""
    print(f"\n{'='*60}")
    print(f"Processing mimalloc-{version}")
    print(f"{'='*60}")
    
    # Paths
    target_dir = TESTDATA_CPP / f"{DATE_PREFIX}-mimalloc-{version}-multithread"
    mimalloc_dir = ROOT_DIR / "3rd" / f"mimalloc-{version}"
    mimalloc_lib = mimalloc_dir / "build" / "libmimalloc.so"
    mimalloc_include = mimalloc_dir / "include"
    
    # Check mimalloc exists
    if not mimalloc_dir.exists():
        print(f"WARNING: mimalloc-{version} not found at {mimalloc_dir}, skipping...")
        return False
    
    # Try both debug and release library names
    mimalloc_lib_debug = mimalloc_dir / "build" / "libmimalloc-debug.so"
    if mimalloc_lib_debug.exists():
        mimalloc_lib = mimalloc_lib_debug
        lib_name = "mimalloc-debug"
    elif mimalloc_lib.exists():
        lib_name = "mimalloc"
    else:
        print(f"WARNING: libmimalloc*.so not found at {mimalloc_dir}/build, skipping...")
        return False
    
    # Create target directory
    print(f"Creating directory: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy source file
    print("Copying source file...")
    shutil.copy(TEMPLATE_DIR / "mi_alloc_multithread_test.cpp", target_dir)
    
    # Copy validate.py
    print("Copying validate.py...")
    shutil.copy(TEMPLATE_DIR / "validate.py", target_dir)
    
    # Compile the test program
    print(f"Compiling test program with mimalloc-{version}...")
    test_binary = target_dir / "mi_alloc_multithread_test"
    
    compile_cmd = [
        "g++", "-g", "-O0", "-pthread",
        f"-I{mimalloc_include}",
        f"-L{mimalloc_dir}/build",
        f"-Wl,-rpath,{mimalloc_dir}/build",
        "-o", str(test_binary),
        str(target_dir / "mi_alloc_multithread_test.cpp"),
        f"-l{lib_name}", "-ldl"
    ]
    
    result = run_cmd(compile_cmd)
    if result.returncode != 0:
        print(f"ERROR: Compilation failed for mimalloc-{version}")
        return False
    
    print(f"Compiled: {test_binary}")
    
    # Run the test program
    print("Running test program...")
    os.chdir(target_dir)
    
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{mimalloc_dir}/build:" + env.get("LD_LIBRARY_PATH", "")
    
    with open("test_output.log", "w") as log_file:
        proc = subprocess.Popen(
            [str(test_binary)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env
        )
    
    test_pid = proc.pid
    print(f"Test PID: {test_pid}")
    
    # Wait for "READY FOR GCORE" message
    print("Waiting for allocations to complete...")
    ready = False
    for i in range(120):  # Wait up to 2 minutes
        time.sleep(1)
        try:
            with open("test_output.log", "r") as f:
                if "READY FOR GCORE" in f.read():
                    ready = True
                    break
        except:
            pass
    
    if not ready:
        print("ERROR: Test program did not complete in time")
        proc.kill()
        return False
    
    print("Allocations complete! Waiting 2 seconds for stability...")
    time.sleep(2)
    
    # Generate coredump using gcore
    print("Generating coredump...")
    corefile_prefix = "coredump"
    gcore_result = run_cmd(["gcore", "-o", corefile_prefix, str(test_pid)])
    
    if gcore_result.returncode != 0:
        print(f"ERROR: gcore failed")
        proc.terminate()
        return False
    
    # The corefile is named coredump.<pid>
    corefile = f"{corefile_prefix}.{test_pid}"
    if not os.path.exists(corefile):
        print(f"ERROR: Coredump not found: {corefile}")
        proc.terminate()
        return False
    
    print(f"Coredump generated: {corefile}")
    
    # ========================================
    # Use cmd/maze-tar-coredump.py to package
    # IMPORTANT: Must be done BEFORE killing the process
    # ========================================
    print("Packaging coredump using maze-tar-coredump.py...")
    
    # maze-tar-coredump.py must be run from its directory or provide absolute path
    tar_script = CMD_DIR / "maze-tar-coredump.py"
    corefile_abs = target_dir / corefile
    
    tar_result = run_cmd(
        ["python3", str(tar_script), str(corefile_abs)],
        cwd=target_dir
    )
    
    if tar_result.returncode != 0:
        print(f"ERROR: maze-tar-coredump.py failed")
        print(f"STDOUT: {tar_result.stdout}")
        proc.terminate()
        return False
    
    # Find the generated tarball
    tarballs = list(target_dir.glob("coredump-*.tar.gz"))
    if not tarballs:
        print("ERROR: No tarball generated")
        proc.terminate()
        return False
    
    tarball = tarballs[0]
    print(f"Tarball created: {tarball}")
    
    # Stop the test program
    print("Stopping test program...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()
    
    # Cleanup temporary files
    print("Cleaning up...")
    for tmp_file in [corefile, "test_output.log"]:
        tmp_path = target_dir / tmp_file
        if tmp_path.exists():
            tmp_path.unlink()
            print(f"  Removed: {tmp_file}")
    
    print(f"\n✅ Test case created: {target_dir}")
    print(f"   Tarball: {tarball.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Create mimalloc test cases")
    parser.add_argument("--version", "-v", help="Specific version to create (e.g., 1-1-0)")
    parser.add_argument("--all", "-a", action="store_true", help="Create all versions")
    parser.add_argument("--list", "-l", action="store_true", help="List available versions")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Creating mimalloc test cases")
    print("=" * 60)
    print(f"Root directory: {ROOT_DIR}")
    print(f"Template: {TEMPLATE_DIR}")
    print(f"Tar script: {CMD_DIR / 'maze-tar-coredump.py'}")
    
    # Check template exists
    if not TEMPLATE_DIR.exists():
        print(f"ERROR: Template directory not found: {TEMPLATE_DIR}")
        sys.exit(1)
    
    if not (TEMPLATE_DIR / "mi_alloc_multithread_test.cpp").exists():
        print(f"ERROR: Source file not found in template")
        sys.exit(1)
    
    if not (CMD_DIR / "maze-tar-coredump.py").exists():
        print(f"ERROR: maze-tar-coredump.py not found in {CMD_DIR}")
        sys.exit(1)
    
    if args.list:
        print("\nAvailable versions:")
        for v in ALL_VERSIONS:
            mimalloc_dir = ROOT_DIR / "3rd" / f"mimalloc-{v}"
            status = "✅" if mimalloc_dir.exists() else "❌ (not found)"
            print(f"  - {v} {status}")
        sys.exit(0)
    
    versions = []
    if args.version:
        versions = [args.version]
    elif args.all:
        versions = ALL_VERSIONS
    else:
        print("\nUsage:")
        print("  python3 create_mimalloc_testcases.py --all")
        print("  python3 create_mimalloc_testcases.py --version 1-1-0")
        print("  python3 create_mimalloc_testcases.py --list")
        sys.exit(1)
    
    # Save original directory
    original_cwd = os.getcwd()
    
    results = {}
    for version in versions:
        try:
            success = create_testcase(version)
            results[version] = success
        except Exception as e:
            print(f"ERROR: Exception during processing mimalloc-{version}: {e}")
            results[version] = False
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    success_count = 0
    for version, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  mimalloc-{version}: {status}")
        if success:
            success_count += 1
    
    print(f"\nTotal: {success_count}/{len(results)} succeeded")
    
    print("\nTo run tests:")
    print(f"  cd {ROOT_DIR}/testdata")
    print(f"  python3 run_test.py cpp/{DATE_PREFIX}-mimalloc-*")


if __name__ == "__main__":
    main()
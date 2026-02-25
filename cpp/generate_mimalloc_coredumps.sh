#!/bin/bash
# 自动化生成 mimalloc 测试用例的 coredump
# 使用方法: ./generate_mimalloc_coredumps.sh

set -e

MAZE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$MAZE_ROOT"

# 版本映射: 测试目录版本 -> 3rd目录版本
declare -A VERSION_MAP
VERSION_MAP["1-1-0"]="1-1-0"
VERSION_MAP["1-2-0"]="1-2-0"
VERSION_MAP["1-3-0"]="1-3-0"
VERSION_MAP["1-4-0"]="1-4-0"
VERSION_MAP["1-5-0"]="1-5-0"
VERSION_MAP["1-6-0"]="1-6-0"
VERSION_MAP["1-7-0"]="1-7-0"
VERSION_MAP["1-8-0"]="1-8-0"
VERSION_MAP["1-9-0"]="1-9-2"  # 1.9.0 测试使用 1.9.2 库

generate_coredump() {
    local TEST_VERSION=$1
    local LIB_VERSION=${VERSION_MAP[$TEST_VERSION]}
    local TEST_DIR="testdata/cpp/20260211-mimalloc-${TEST_VERSION}-multithread"
    local LIB_PATH="$MAZE_ROOT/3rd/mimalloc-${LIB_VERSION}/build/libmimalloc-debug.so"
    
    echo "============================================================"
    echo "Generating coredump for mimalloc $TEST_VERSION"
    echo "Using library: $LIB_PATH"
    echo "============================================================"
    
    if [ ! -f "$LIB_PATH" ]; then
        echo "ERROR: Library not found: $LIB_PATH"
        return 1
    fi
    
    if [ ! -f "$TEST_DIR/mi_alloc_multithread_test" ]; then
        echo "ERROR: Test binary not found: $TEST_DIR/mi_alloc_multithread_test"
        return 1
    fi
    
    # 检查是否已有 coredump
    if ls "$TEST_DIR"/coredump-*.tar.gz 1>/dev/null 2>&1; then
        echo "Coredump already exists in $TEST_DIR, skipping..."
        return 0
    fi
    
    # 启动测试程序
    cd "$TEST_DIR"
    LD_PRELOAD="$LIB_PATH" ./mi_alloc_multithread_test > test_output.log 2>&1 &
    local PID=$!
    echo "Started test process with PID: $PID"
    
    # 等待程序准备好
    echo "Waiting for 'READY FOR GCORE'..."
    for i in {1..60}; do
        if grep -q "READY FOR GCORE" test_output.log 2>/dev/null; then
            echo "Program is ready!"
            break
        fi
        sleep 1
    done
    
    if ! grep -q "READY FOR GCORE" test_output.log 2>/dev/null; then
        echo "ERROR: Program did not become ready within 60 seconds"
        kill $PID 2>/dev/null || true
        cd "$MAZE_ROOT"
        return 1
    fi
    
    # 生成 coredump
    echo "Generating coredump..."
    gcore -o coredump $PID
    
    # 打包 coredump
    echo "Packaging coredump..."
    cd "$MAZE_ROOT/cmd"
    python3 maze-tar-coredump.py "../$TEST_DIR/coredump.$PID"
    
    # 移动打包文件
    mv coredump-$PID-*.tar.gz "../$TEST_DIR/"
    
    # 清理临时文件
    rm -f $PID.exe $PID.md5 maps
    
    # 停止测试进程
    echo "Stopping test process..."
    kill $PID 2>/dev/null || true
    
    # 清理原始 coredump
    rm -f "../$TEST_DIR/coredump.$PID"
    
    cd "$MAZE_ROOT"
    echo "Done with mimalloc $TEST_VERSION"
    echo ""
}

# 处理所有版本
for version in "${!VERSION_MAP[@]}"; do
    generate_coredump "$version"
done

echo "============================================================"
echo "All coredumps generated!"
echo "============================================================"

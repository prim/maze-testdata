#!/bin/bash
# 为单个 mimalloc 版本生成 coredump
# 使用方法: ./gen_one_coredump.sh <TEST_VERSION> <LIB_VERSION>
# 例如: ./gen_one_coredump.sh 1-2-0 1-2-0

set -e

TEST_VERSION=$1
LIB_VERSION=$2

if [ -z "$TEST_VERSION" ] || [ -z "$LIB_VERSION" ]; then
    echo "Usage: $0 <TEST_VERSION> <LIB_VERSION>"
    echo "Example: $0 1-2-0 1-2-0"
    exit 1
fi

MAZE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_DIR="$MAZE_ROOT/testdata/cpp/20260211-mimalloc-${TEST_VERSION}-multithread"
LIB_PATH="$MAZE_ROOT/3rd/mimalloc-${LIB_VERSION}/build/libmimalloc-debug.so"

echo "============================================================"
echo "Generating coredump for mimalloc $TEST_VERSION"
echo "Using library: $LIB_PATH"
echo "Test directory: $TEST_DIR"
echo "============================================================"

# 检查是否已有 coredump
if ls "$TEST_DIR"/coredump-*.tar.gz 1>/dev/null 2>&1; then
    echo "Coredump already exists in $TEST_DIR, skipping..."
    exit 0
fi

# 编译带 mimalloc 链接的测试程序
echo "Compiling test program..."
cd "$TEST_DIR"
g++ -g -O0 -pthread -o mi_alloc_multithread_test_linked mi_alloc_multithread_test.cpp \
    -I"$MAZE_ROOT/3rd/mimalloc-${LIB_VERSION}/include" \
    -L"$MAZE_ROOT/3rd/mimalloc-${LIB_VERSION}/build" \
    -lmimalloc-debug -ldl

# 设置库路径并启动测试程序
export LD_LIBRARY_PATH="$MAZE_ROOT/3rd/mimalloc-${LIB_VERSION}/build:$LD_LIBRARY_PATH"

# 使用临时文件捕获输出
OUTPUT_LOG="$TEST_DIR/.test_output.log"
rm -f "$OUTPUT_LOG"

echo "Starting test program..."
./mi_alloc_multithread_test_linked > "$OUTPUT_LOG" 2>&1 &
PID=$!
echo "Started with PID: $PID"

# 等待程序输出 ">>> READY FOR GCORE <<<"
echo "Waiting for '>>> READY FOR GCORE <<<' signal..."
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if grep -q ">>> READY FOR GCORE <<<" "$OUTPUT_LOG" 2>/dev/null; then
        echo "Signal received! Memory allocation complete."
        cat "$OUTPUT_LOG"
        break
    fi
    
    # 检查进程是否还在运行
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "ERROR: Process has exited unexpectedly"
        cat "$OUTPUT_LOG"
        rm -f "$TEST_DIR/mi_alloc_multithread_test_linked" "$OUTPUT_LOG"
        exit 1
    fi
    
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "ERROR: Timeout waiting for READY signal"
    cat "$OUTPUT_LOG"
    kill $PID 2>/dev/null || true
    rm -f "$TEST_DIR/mi_alloc_multithread_test_linked" "$OUTPUT_LOG"
    exit 1
fi

# 清理输出日志
rm -f "$OUTPUT_LOG"

# 在测试目录生成 coredump
echo "Generating coredump..."
cd "$TEST_DIR"
gcore -o coredump $PID 2>&1

# 停止测试程序
echo "Stopping test process..."
kill $PID 2>/dev/null || true
sleep 1

# 打包 coredump (在测试目录执行)
echo "Packaging coredump..."
cd "$TEST_DIR"
python3 "$MAZE_ROOT/cmd/maze-tar-coredump.py" "coredump.$PID"

# 清理原始 coredump
rm -f "$TEST_DIR/coredump.$PID"

# 清理链接的测试程序
rm -f "$TEST_DIR/mi_alloc_multithread_test_linked"

# 清理打包脚本生成的临时文件
rm -f "$TEST_DIR/$PID.exe" "$TEST_DIR/$PID.md5" "$TEST_DIR/maps"

echo "============================================================"
echo "Done! Coredump for mimalloc $TEST_VERSION generated."
ls -la "$TEST_DIR"/coredump-*.tar.gz
echo "============================================================"

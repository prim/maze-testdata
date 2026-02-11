#!/bin/bash
#
# Create mimalloc test cases for versions 1.1 to 1.9
# Based on the 1.0.0 test case template
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTDATA_CPP="$SCRIPT_DIR"

# mimalloc versions to test
VERSIONS=(
    "1-1-0"
    "1-2-0"
    "1-3-0"
    "1-4-0"
    "1-5-0"
    "1-6-0"
    "1-7-0"
    "1-8-0"
    "1-9-2"
)

# Date prefix for test case directories
DATE_PREFIX="20260211"

# Source template directory
TEMPLATE_DIR="$TESTDATA_CPP/20260211-mimalloc-1-0-0-multithread"

echo "============================================================"
echo "Creating mimalloc test cases"
echo "============================================================"
echo "Root directory: $ROOT_DIR"
echo "Template: $TEMPLATE_DIR"
echo ""

# Check template exists
if [ ! -d "$TEMPLATE_DIR" ]; then
    echo "ERROR: Template directory not found: $TEMPLATE_DIR"
    exit 1
fi

# Check source file exists
if [ ! -f "$TEMPLATE_DIR/mi_alloc_multithread_test.cpp" ]; then
    echo "ERROR: Source file not found: $TEMPLATE_DIR/mi_alloc_multithread_test.cpp"
    exit 1
fi

for VERSION in "${VERSIONS[@]}"; do
    echo ""
    echo "============================================================"
    echo "Processing mimalloc-$VERSION"
    echo "============================================================"
    
    # Convert version format: 1-1-0 -> 1.1.0 for display
    VERSION_DOT=$(echo $VERSION | tr '-' '.')
    
    # Target directory name
    TARGET_DIR="$TESTDATA_CPP/${DATE_PREFIX}-mimalloc-${VERSION}-multithread"
    
    # mimalloc paths
    MIMALLOC_DIR="$ROOT_DIR/3rd/mimalloc-$VERSION"
    MIMALLOC_LIB="$MIMALLOC_DIR/build/libmimalloc.so"
    MIMALLOC_INCLUDE="$MIMALLOC_DIR/include"
    
    # Check mimalloc exists
    if [ ! -d "$MIMALLOC_DIR" ]; then
        echo "WARNING: mimalloc-$VERSION not found at $MIMALLOC_DIR, skipping..."
        continue
    fi
    
    if [ ! -f "$MIMALLOC_LIB" ]; then
        echo "WARNING: libmimalloc.so not found at $MIMALLOC_LIB, skipping..."
        continue
    fi
    
    # Create target directory
    echo "Creating directory: $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
    
    # Copy source file
    echo "Copying source file..."
    cp "$TEMPLATE_DIR/mi_alloc_multithread_test.cpp" "$TARGET_DIR/"
    
    # Copy validate.py
    echo "Copying validate.py..."
    cp "$TEMPLATE_DIR/validate.py" "$TARGET_DIR/"
    
    # Compile the test program
    echo "Compiling test program with mimalloc-$VERSION..."
    TEST_BINARY="$TARGET_DIR/mi_alloc_multithread_test"
    
    g++ -g -O0 -pthread \
        -I"$MIMALLOC_INCLUDE" \
        -L"$MIMALLOC_DIR/build" \
        -Wl,-rpath,"$MIMALLOC_DIR/build" \
        -o "$TEST_BINARY" \
        "$TARGET_DIR/mi_alloc_multithread_test.cpp" \
        -lmimalloc -ldl
    
    if [ ! -f "$TEST_BINARY" ]; then
        echo "ERROR: Compilation failed for mimalloc-$VERSION"
        continue
    fi
    
    echo "Compiled: $TEST_BINARY"
    
    # Run the test program in background
    echo "Running test program..."
    cd "$TARGET_DIR"
    
    # Start the test program
    LD_LIBRARY_PATH="$MIMALLOC_DIR/build:$LD_LIBRARY_PATH" \
        "$TEST_BINARY" > test_output.log 2>&1 &
    TEST_PID=$!
    
    echo "Test PID: $TEST_PID"
    
    # Wait for "READY FOR GCORE" message
    echo "Waiting for allocations to complete..."
    for i in {1..60}; do
        if grep -q "READY FOR GCORE" test_output.log 2>/dev/null; then
            echo "Allocations complete!"
            break
        fi
        sleep 1
    done
    
    if ! grep -q "READY FOR GCORE" test_output.log 2>/dev/null; then
        echo "ERROR: Test program did not complete in time"
        kill $TEST_PID 2>/dev/null || true
        continue
    fi
    
    # Generate coredump
    echo "Generating coredump..."
    gcore -o core $TEST_PID
    
    # Kill the test program
    echo "Stopping test program..."
    kill $TEST_PID 2>/dev/null || true
    wait $TEST_PID 2>/dev/null || true
    
    # Check if coredump was generated
    COREFILE="core.$TEST_PID"
    if [ ! -f "$COREFILE" ]; then
        echo "ERROR: Coredump not found: $COREFILE"
        continue
    fi
    
    # Package the coredump
    TIMESTAMP=$(date +%s)
    TARBALL="coredump-${TEST_PID}-${TIMESTAMP}.tar.gz"
    
    echo "Creating tarball: $TARBALL"
    
    # Create tarball with required files
    # Need: core file, executable, maps, mimalloc library
    tar -czvf "$TARBALL" \
        "$COREFILE" \
        "mi_alloc_multithread_test" \
        -C "$MIMALLOC_DIR/build" $(ls "$MIMALLOC_DIR/build"/*.so* 2>/dev/null | xargs -n1 basename)
    
    # Cleanup
    echo "Cleaning up..."
    rm -f "$COREFILE"
    rm -f test_output.log
    
    echo "Test case created: $TARGET_DIR"
    echo "Tarball: $TARGET_DIR/$TARBALL"
done

echo ""
echo "============================================================"
echo "All test cases created!"
echo "============================================================"
echo ""
echo "To run tests:"
echo "  cd $ROOT_DIR/testdata"
echo "  python3 run_test.py cpp/20260211-mimalloc-*"

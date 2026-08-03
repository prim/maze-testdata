# Go cgo Runtime Core Fixture

This Linux/amd64 fixture verifies that Maze analyzes Go runtime memory and the
native allocator in one cgo process. It retains 128 typed Go nodes, 128 8 KiB
backing arrays, one 8 MiB Go array, 4,096 glibc allocations, one 24 MiB glibc
allocation, and a goroutine permanently blocked inside C.

## Generate

Requirements: Go with cgo, a C compiler, GDB/gcore, glibc, and Git LFS.

```bash
testdata/golang/20260803-cgo-runtime-core/generate.sh
```

The generator works under `./tmp/`, packages the exact executable and shared
libraries, and regenerates the machine-readable manifest. Generation and tests
must remain serial because each capture is memory intensive.

## Run

```bash
python3 testdata/run_test.py golang/20260803-cgo-runtime-core
```

The validator requires Go heap accounting, typed objects, cgo stack metadata,
the blocked goroutine, the 24 MiB ptmalloc mmap chunk, and all 4,096 small
native allocations in the same result.

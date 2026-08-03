# Go PIE Runtime Core Fixture

This durable Linux/amd64 fixture builds the common typed heap workload with
`-buildmode=pie`. The validator requires the same object, root, edge,
dominator, garbage, backing-array, and parked-goroutine semantics as the
default executable matrix. `run_executable_forms.py` additionally proves that
the archived analysis executable is an ET_DYN ELF with DWARF and that Maze
reconstructs its non-zero ASLR load bias.

```bash
testdata/golang/20260803-pie-runtime-core/generate.sh
python3 testdata/run_test.py golang/20260803-pie-runtime-core
```

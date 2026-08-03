# Go Stripped Runtime Core Fixture

This durable Linux/amd64 fixture runs a fully stripped Go executable, captures
its core and exact maps, then binds analysis to the corresponding unstripped
DWARF ELF. The archive retains both `runtime-stripped` and the analysis ELF.
The executable-form verifier requires identical non-empty Go Build IDs, no
`.debug_info` in the runtime ELF, DWARF in the analysis ELF, and full Maze heap
semantics.

```bash
testdata/golang/20260803-stripped-runtime-core/generate.sh
python3 testdata/run_test.py golang/20260803-stripped-runtime-core
```

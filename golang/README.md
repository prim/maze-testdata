# Go Runtime Core Matrix

`runtime_matrix.json` is the authoritative durable Linux/amd64 compatibility
matrix. Each case contains its own source, exact toolchain declaration,
generator, validator, compressed core artifact, and hash manifest. Generation
and replay are intentionally serial because concurrent `gcore` runs create
large transient files and unstable resource pressure.

Verify hashes, archive members, embedded executable identity, and replay every
case with Maze:

```bash
python3 testdata/golang/run_runtime_matrix.py
```

Regenerate all artifacts with exact Go toolchains, then verify and replay:

```bash
python3 testdata/golang/run_runtime_matrix.py --generate
```

Limit a run to one exact version with `--version go1.20.14`. Use
`--verify-only` when only artifact integrity needs to be checked. Dynamic files
stay under `./tmp/`, and repository-root Maze result/log files are restored
after replay.

After building Maze, derive and validate the malformed-input matrix from the
durable Go 1.25.6 artifact:

```bash
./maze --build
python3 testdata/golang/run_corrupt_matrix.py
```

The 15 cases cover a truncated ELF core; a missing runtime page; corrupt
pointer, slice, string, span, linked-list, and goroutine-stack metadata;
missing/corrupt DWARF; a mismatched main Go ELF; and a real Go plugin ELF whose
`.debug_info` byte is changed while its size and PT_LOAD layout remain
identical; the final case corrupts a real Go 1.23 legacy runtime GC program.
The plugin case sends CoreInput v2 with the original file SHA-256 and requires
`GOCORE_INPUT_INVALID/core-input`. Every case must exit nonzero with no trailer
and no raw Go panic stack on stderr. The first 14 loading failures emit exactly
a header and stable fatal diagnostic. GC-program corruption is a valid late
failure: it emits 42 normal prefix records and a final fatal diagnostic as
record 43. Derived sparse files and `results.json` stay in
`./tmp/golang-corrupt-matrix/`.

The Go 1.23 matrix replay automatically runs `run_gcprog_integration.py`. It
extracts the exact durable core/executable and requires `main.GlobalGCProg` to
resolve through a runtime-only `KindGCProg` type with no DWARF mapping, exactly
160,000 bytes and 20,000 pointer fields at pointer-sized offsets.

Verify and replay the durable executable-form corpus serially:

```bash
python3 testdata/golang/run_executable_forms.py
python3 testdata/golang/run_executable_forms.py --generate
```

The PIE case requires an ET_DYN analysis ELF with DWARF and a non-zero runtime
load bias. The stripped case archives both the actual `runtime-stripped` ELF
and its exact unstripped analysis ELF, requires absent/present `.debug_info`
respectively, and binds them with the same non-empty Go Build ID. Both cases
run the full typed heap/root/edge/dominator validator through Maze tar replay.

Run the opt-in live PID to exact core tar equivalence checks serially:

```bash
./maze --build
MAZE_GOCORE_LIVE_TAR_INTEGRATION=1 TMPDIR="$PWD/tmp/go-test" \
  go test ./golang_runtime -run '^TestMazeLiveTarEquivalence$' -count=1 -v
MAZE_GOCORE_CGO_LIVE_TAR_INTEGRATION=1 TMPDIR="$PWD/tmp/go-test" \
  go test ./golang_runtime -run '^TestMazeCgoLiveTarEquivalence$' -count=1 -v
```

`run_live_tar.py --fixture pure|cgo` builds the matching durable fixture source,
analyzes the live PID, packages the exact retained core and maps, replays the
tar, runs both validators, and requires byte-identical text plus JSON equality
after removing only `generated_at`. The cgo comparison keeps native class IDs
strict. Artifacts stay under `./tmp/golang-live-tar/` or
`./tmp/golang-cgo-live-tar/`; existing root result and log files are restored.

Run the qualifying large-graph CPU, RSS, and output-size gate after building
Maze:

```bash
./maze --build
PYTHONDONTWRITEBYTECODE=1 \
  python3 testdata/golang/run_performance_gate.py
```

`performance_fixture.go` creates exactly 200,000 individually allocated,
64-byte `main.benchNode` objects with two object edges and one global-root edge
per node. The runner analyzes the live process with full Maze, retains that
exact core, and analyzes it again with `.maze-go-core`. It samples each command
process tree every 20 ms and gates wall time, child CPU, peak RSS, NDJSON/JSON
bytes, object count, edge count, and complete trailer/hash semantics. A smaller
development run requires `--smoke`; `--keep-large-artifacts` retains the sparse
core and full helper NDJSON. Otherwise only the result, logs, fixture binary,
and Maze output remain under `./tmp/golang-performance-gate/`, and existing
repository-root result/log files are restored.

Run the small live type-evidence demonstration when changing Go type
propagation or documenting unknown-object semantics:

```bash
mkdir -p tmp/go-type-recovery-limits
go build -o tmp/go-type-recovery-limits/go-type-recovery-limits \
  testdata/golang/20260805-type-recovery-limits-live/type_recovery_limits.go
tmp/go-type-recovery-limits/go-type-recovery-limits
```

`20260805-type-recovery-limits-live` prints controlled addresses for same-size
typed, `unsafe.Pointer`, closure-captured, and stack-root objects, plus an
interior-only object and a `reflect.StructOf` value. It also creates 10,000
unrooted `A <-> B` pairs. Query the printed addresses with `/api/go/object` and
`/api/go/reachable`; do not infer fixture counts from all process-wide
`unk<size>` classes. The unrooted pairs must contribute only aggregate garbage
bytes and must not appear as individual `main.GarbageA`/`main.GarbageB`
objects.

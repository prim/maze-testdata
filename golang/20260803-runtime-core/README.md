# Go Runtime Core Fixture

This Go 1.25.6 fixture is one entry in the durable Linux/amd64 matrix for Maze
Go core analysis.
It covers global, map, interface, and parked-goroutine stack roots; linked and
branched objects; variable-sized slice backing arrays; one large backing array;
and allocated but unreachable garbage.

## Generate

Requirements: Go, GDB/gcore, GNU tar-compatible Linux core dumps, and Git LFS.
Run from any directory:

```bash
testdata/golang/20260803-runtime-core/generate.sh
```

The generator uses exactly `GOTOOLCHAIN=go1.25.6`, builds under `./tmp/`, captures a stopped snapshot, packages the
matching executable and mappings, writes `coredump-runtime-core.tar.gz`, and
regenerates `manifest.json` with source, binary, archive, member, and logical
core hashes/sizes. Generation is intentionally serial.

## Run

From the Maze repository root:

```bash
python3 testdata/run_test.py golang/20260803-runtime-core
```

The validator checks the versioned Go schema, runtime identity, heap accounting
invariants, full dominator coverage, exact user object counts, backing arrays,
unreachable garbage, and the parked goroutine.

Run the complete Go 1.20.14-1.26.0 matrix with:

```bash
python3 testdata/golang/run_runtime_matrix.py
```

## Live/Tar Equivalence

Build Maze first, then run the opt-in integration from the repository root:

```bash
./maze --build
MAZE_GOCORE_LIVE_TAR_INTEGRATION=1 \
  go test ./golang_runtime -run '^TestMazeLiveTarEquivalence$' -v
```

The integration builds and launches this fixture, analyzes the live PID, checks
that it survived GDB detach, packages the exact core retained by the live run,
replays that tarball, and requires byte-identical text plus structurally equal
JSON after removing only `generated_at`. It also runs this validator against
both results. All generated files stay under `./tmp/golang-live-tar/`; existing
root `maze-result.txt` and `maze-result.json` files are preserved and restored.

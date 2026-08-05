# Go Type Recovery Limits Live Fixture

This fixture demonstrates the difference between a live Go heap allocation
and an allocation for which Maze has exact source-level type evidence. It
contains the following controlled cases:

| Case | Liveness evidence | Expected Maze type behavior |
|------|-------------------|-----------------------------|
| `KnownPayload` | typed global `*KnownPayload` | exact `main.KnownPayload` |
| `UnsafePayload` | global `unsafe.Pointer` | `unk128`; size does not imply type |
| `InteriorPayload` | only `*byte` into the allocation | `unk2048`; no canonical-start type |
| closure environment/capture | global `func`, runtime pointer bitmap | conservative unknown closure/capture objects |
| `reflect.StructOf` value | interface dynamic `abi.Type` | `reflect.generatedType...` placeholder |
| `StackPayload` | typed live goroutine stack local | exact `main.StackPayload` when DWARF location evidence is usable |
| runtime storage | goroutine, channels, sleep timer | `runtime.*` when typed; otherwise version-dependent `unk<size>` |
| 10,000 `GarbageA <-> GarbageB` pairs | no root after construction | aggregate garbage bytes only; no object/type rows |

`KnownPayload`, `UnsafePayload`, `ClosurePayload`, and `StackPayload` are all
128 bytes on Linux/amd64. Their different results prove that Maze does not use
allocation size as a substitute for type evidence.

## Live run

Build from the Maze repository root and keep generated files under `./tmp/`:

```bash
mkdir -p tmp/go-type-recovery-limits
go build -o tmp/go-type-recovery-limits/go-type-recovery-limits \
  testdata/golang/20260805-type-recovery-limits-live/type_recovery_limits.go
tmp/go-type-recovery-limits/go-type-recovery-limits
```

Wait for `>>> READY FOR MAZE LIVE PROFILE <<<`, then analyze the printed PID:

```bash
./maze --pid <PID> --text --json-output --local-api \
  --output-dir "$PWD/tmp/go-type-recovery-limits/results" \
  --logdir "$PWD/tmp/go-type-recovery-limits/work"
```

The program prints representative addresses for every live controlled case.
Use `/api/go/object?address=0x...` to compare the printed address with Maze's
actual `display_type`, incoming roots, and field-path evidence. Exact counts of
unrelated `unk<size>` runtime objects are Go-version dependent; validate the
controlled addresses instead of assuming every unknown class belongs to this
fixture.

The program disables target GC only so the unrooted cycle bytes remain in
allocated spans until capture. Those cycles are intentionally outside Maze's
live-object stream. They appear in
`all/heap/in use spans/alloc/garbage`, not as `main.GarbageA` or
`main.GarbageB` objects.

## Go 1.25.6 live baseline

One Linux/amd64 run resolved the printed controlled addresses as follows:

```text
typed global              main.KnownPayload
unsafe-only               unk128
interior-only base        unk2048 (root target_offset=25)
closure environment       unk16
closure-captured payload  unk128
reflect-generated value   reflect.generatedType<runtime-address>
typed stack-root payload  main.StackPayload
```

The heap stats were `1,937,408 alloc = 574,952 live + 1,362,456 garbage`.
The 10,000 cycles account for exactly 1,280,000 bytes of the garbage; the
remaining 82,456 bytes primarily come from the temporary pointer-slice backing
and construction/runtime allocations. `main.GarbageA` and `main.GarbageB`
were absent from the live type classes.

Optimizer locations and incidental runtime allocations can change with a Go
minor version. The stable fixture contract is the evidence rule and the
printed controlled addresses, not the total number of every process-wide
unknown class.

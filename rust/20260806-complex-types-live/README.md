# TC-R001: Rust Phase 0 complex-types live fixture

Phase 0 fixture for [Rust support](../../../dev-log/2026-08-06-rust-support-implementation-plan.md).
A dependency-free Rust 1.97 image that parks a live object graph so a core can
be captured while every root and backing allocation is reachable.

## What it exercises

| Root | Type | Status |
|------|------|--------|
| `GLOBAL_CACHE` | `OnceLock<Mutex<HashMap<String, Box<Person>>>>` | live |
| `GLOBAL_SPEAKERS` | `Vec<Box<dyn Speaker>>` (trait objects, Dog/Cat) | live |
| `GLOBAL_VEC` | `Vec<Person>` | live |
| `GLOBAL_ARC_NODE` | `Arc<ArcNode>` (Arc + Mutex + sync::Weak) | live |
| `GLOBAL_SET` / `GLOBAL_DEQUE` | `HashSet<u64>` / `VecDeque<String>` | live |
| `GLOBAL_SLICE_VIEW` | `&'static [u64]` (Box::leak) | live |
| local `a`/`b` | `Rc` + `rc::Weak` cycle on the owner thread | live |
| TLS `TLS_BUFFER` / `TLS_COUNTER` | `RefCell<Option<Box<Vec<u64>>>>` / counter | live |
| stack locals | `Event` enum, `Option<Person>`, `Result<u64,String>`, closure | live on `fixture-owner` |
| `pending_task` | parked async generator, leaked boxed state | live |
| `malloc(4096)` + `mmap(65536)` | deliberate FFI C / anonymous allocations | live |

Every live root writes its address into `rust-fixture-ground-truth.json` before
the `>>> READY FOR GCORE <pid> <<<` signal.

## Capture layout

- `coredump-*.tar.gz` — the maze standard tar: `core.<pid>`, `<pid>.maps`,
  `<pid>.exe`, `<pid>.md5`, md5-named exe/libs, `libthread_db.so`,
  `capture-manifest.json`, and the injected `rust-artifacts.json`.
- `rust-artifacts.json` — locked build identity (`maze.rust-artifacts/v1`):
  rustc version, target triple, LLVM version, Cargo profile, opt/debug level,
  LTO, panic strategy, allocator, Cargo.lock digest, executable SHA-256.
- `src/main.rs` + `Cargo.toml` + `Cargo.lock` — the fixture source (dev profile,
  `debug = 2` full variable debuginfo).

## Reproducing the capture

```bash
# cargo must be on PATH (e.g. source ~/.cargo/env)
testdata/rust/20260806-complex-types-live/generate.sh
```

`generate.sh` rebuilds the fixture, collects `rust-artifacts.json`, captures the
core with the standard `cmd/maze-gen-coredump.py` workflow, injects the manifest
into the tar, and moves it into the case directory.

## Running the regression

```bash
python3 testdata/run_test.py rust/20260806-complex-types-live
```

The Go unit tests in `prepare/lang_rust_test.go` assert the same Phase 0 DoD
(capability states, manifest merge, and all fail-closed cases) without needing
the captured core:

```bash
go test ./prepare/ -run Rust
```

## Fixture expectations

Rust is an **additive capability** over the native C baseline: the image still
runs through the generic native path (`Language = "c"`, allocator = ptmalloc),
and the prepare stage records the multi-evidence capability report in
`S.Rust` (`rust_detected`, `rust_dwarf_available`, `rust_profile`,
`allocator_profile`, `mixed_modules`, `unsupported_reason`) plus the locked
manifest identity. The native analyzer names Rust types (e.g.
`alloc::sync::ArcInner<...>`, `maze_rust_fixture::pending_task::{async_fn_env#0}`)
without any Rust-specific parser.

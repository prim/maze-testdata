# Rust high-cardinality complex types live fixture

This fixture is the Rust counterpart of
`python/20260131-complex-types-3000`. The older
`rust/20260806-complex-types-live` case is kept as a small ABI, identity and
fail-closed conformance fixture. This case is intentionally larger: every
family has many independently allocated instances so allocator top results and
the Rust typed walk both have useful counts.

## Coverage

| Family | Instances |
| --- | ---: |
| `Box<Person>` | 1,000 |
| `Box<GameEntity>` | 300 |
| `Box<TreeNode>` | 600 nodes in 200 trees |
| `Box<Vec<u64>>` | 500 |
| `Box<HashMap<String, u64>>` | 300 |
| `Box<HashSet<u64>>` | 240 |
| `Box<BTreeMap<u64, String>>` | 120 |
| `Box<BTreeSet<String>>` | 120 |
| `Box<VecDeque<String>>` | 300 |
| `Box<LinkedList<Payload>>` | 120 |
| `Box<BinaryHeap<u64>>` | 200 |
| short / medium / long `String` | 1,000 / 500 / 200 |
| byte buffers | 400 |
| `LanguageRecord` (`enum`, `Option`, `Result`, tuple, array) | 500 |
| `Box<dyn Speaker>` | 300 |
| `Arc` / `Weak` graph | 200 nodes |
| `Rc` / `Weak` cycle | 128 nodes |
| pending async futures | 200 |
| TLS records | 512 records on 4 threads |
| raw `malloc(4096)` / anonymous `mmap` | 64 blocks / 4 regions |

The process writes `rust-scale-ground-truth.json` in its working directory.
That file records the exact counts, type sizes, lower-bound requested bytes and
sample addresses for the current process. It is capture-specific and must be
kept with any durable core produced from that process.

## Build and run

Use the locked Rust toolchain already installed for this project. Do not switch
toolchains merely to obtain `rustfmt`; the manifest deliberately binds the
analyzer to the exact compiler and executable identity.

```bash
cd testdata/rust/20260810-complex-types-scale-live
./build.sh dev

mkdir -p ../../../../tmp/rust-complex-scale-live/target
cd ../../../../tmp/rust-complex-scale-live/target
../../../../testdata/rust/20260810-complex-types-scale-live/target/debug/maze-rust-complex-scale
```

Wait for `READY FOR GCORE`, then from the Maze repository root run:

```bash
./maze --pid <PID> --http --fresh-capture --no-cpp \
  --logdir ./tmp/rust-complex-scale-live/maze \
  --output-dir ./tmp/rust-complex-scale-live/result \
  --json-output
```

`build.sh` writes the same `rust-artifacts.json` both at the case root and next
to the executable. Live analysis reads the adjacent manifest, validates it
against the executable snapshot pinned before capture, and reports
`rust_profile=locked`. Offline replay only trusts the manifest inside its
controlled capture input.

## Validation

```bash
python3 testdata/rust/20260810-complex-types-scale-live/validate.py \
  ./tmp/rust-complex-scale-live/result/maze-result.json \
  ./tmp/rust-complex-scale-live/target/rust-scale-ground-truth.json
```

The validator checks the allocator lower bound and at least 10,000 physical
blocks, then verifies the exact batch lengths visible in the typed Rust walk.
It also requires the expected container, ownership, enum, trait-object and
async kinds.

The legacy `top` command aggregates physical ptmalloc chunks by usable size, so
its rows are named `malloc(40)`, `malloc(56)`, and so on. It does not rename
those rows after Rust types. Use `rust-summary` and `rust-allocations` for the
typed view. Rust traversal is bounded, so an outer batch can prove `len=1000`
while only a bounded subset of its child objects is published; TLS is reported
as a separate, currently non-traversable layer.

# Elixir 1.18.4 / OTP 27.3.4.1 fixture

This fixture captures a real Elixir 1.18.4 process running on the reproduced
OTP 27.3.4.1 / ERTS 15.2.7 Linux x86-64 `beam.smp` with GNU Build ID
`f94f08a81260ba544812ca2d62f479a794dc7c77`. Maze must select its embedded v28
layout by Build ID **without** `MAZE_ERLANG_LAYOUT`, publish
`flavor=elixir / version=1.18.4` from authoritative module-literal evidence, and
reach the full v28 contract (every BEAM domain complete, an exact global term
graph, allocator ownership reconciled to the exact archived libc).

Run from the Maze repository root:

```bash
python3 testdata/run_test.py erlang/20260814-elixir-1.18.4-otp27
```

## What the fixture exercises

`maze_elixir_fixture.exs` builds live objects with known values so Maze's
inventory/search/object/ref/root-path/aggregate can be reconciled against ground
truth (the script prints `MAZE_ELIXIR_GROUND_TRUTH=...` before `READY FOR
GCORE`):

- Supervisor / GenServer / Task process identity and state
  (`MazeSupervisor`, `MazeWorker`, a sleeping `Task` child).
- struct / map / list / tuple / bignum / atom (`%MazeFixture{}`, a nested map,
  a list, a tuple, a 30-digit bignum, and sentinel atoms).
- Process dictionary (`:maze_pdict`, `:maze_worker_dict`).
- Mailbox / message fragments: the worker is suspended with `:sys.suspend/1`
  before two known messages (one carries the shared binary) and a long timer
  are queued, so the mailbox is stable at capture time.
- Named ETS table `:maze_ets` with three rows.
- `persistent_term` ground truth `{:maze, :persistent}` holding the struct, the
  big map/list/tuple/bignum, the shared binary, a sub-binary, the captured
  closure and its result.
- Shared large Binary (8000 bytes). OTP 27 `binary_part/3` (erts_bif_binary.c
  → erts_build_sub_bitstring, erl_bits.c) materializes slices ≤
  `ERL_ONHEAP_BITS_LIMIT` (64 bytes) as a HEAP_BITSTRING (a detached heap
  binary), while slices above the limit keep an `ErlSubBits` referencing the
  parent refc Binary. The fixture therefore keeps BOTH forms live with distinct
  process-dictionary keys:
  - `small_slice16` → a 16-byte detached heap bitstring (logical 16, **no**
    chain to the 8000-byte refc);
  - `sub_binary100` → a 100-byte genuine sub-binary (`ErlSubBits` → `BinRef` →
    the same 8000-byte refc Binary).
- Closure / capture (a fun capturing the bignum and struct value).
- Timer / monitor / link.

The `:sys.suspend` + long (600 s) timers guarantee the mailbox and timer state
are stable when `cmd/maze-gen-coredump.py` gcores the process. The fixture also
persists a machine-readable ground truth (`ground-truth.txt` in this directory,
written at capture time under `tmp/elixir-fixture/ground-truth-<run>.txt`) with
the version/OTP/ERTS identity, bignum/struct/closure constants, ETS row count,
process/atom counts, worker/fixture mailbox/link/monitor/timer facts. The
validator binds the runtime evidence to these exact values and fails closed if
the file is missing, empty, or incomplete.

## Capture procedure (regeneration)

The fixture process must run in the same Debian 12 bookworm / glibc 2.36
environment that produced the `beam.smp` (the host is Debian 11 glibc 2.31 and
cannot exec it). The OTP install and the Elixir precompiled build live under
`tmp/otp-27.3.4.1/`; the capture runs the one-shot
`cmd/maze-gen-coredump.py` inside a bookworm container that binds the maze repo
and the OTP tree at the original build path.

```bash
# In a bookworm container with --cap-add SYS_PTRACE --security-opt seccomp=unconfined:
#   -v /home/nguser/hcjn0770/maze8:/home/nguser/hcjn0770/maze8
#   -v /home/nguser/hcjn0770/maze8/tmp/otp-27.3.4.1:/home/hcjn0770/github/maze9/tmp/otp-27.3.4.1
bash /home/hcjn0770/github/maze9/tmp/otp-27.3.4.1/run-elixir-fixture.sh
```

`run-elixir-fixture.sh` first merges the `libc6-dbg` DWARF back into the
container libc with `eu-unstrip` and swaps it in place, so the captured process
maps a full-DWARF libc whose exact member is packaged into the tar. It then runs
`cmd/maze-gen-coredump.py`, which launches the fixture, waits for
`READY FOR GCORE`, gcores the PID, and packages the tar with
`maze-tar-coredump.py` (using the container's gdb via `MAZE_GDB`).

Two independent ASLR captures (the second via a container PID-padding wrapper so
the archived source PIDs differ) are reconciled by the formal
`testdata/erlang/20260814-elixir-1.18.4-otp27/reconcile.py`:
identical Build ID / flavor identity / domain totals (60 processes, 23 ETS
tables, identical runtime atom count), L4 exact graph, allocator ownership
complete, `known_size == allocator_native_covered_bytes`, matching
truth-to-runtime atom deltas inside [0,64], and disjoint ASLR address families.

## Offline replay (this host)

Replay uses the embedded f94 layout and the tar's content-addressed ELF members.
The GDB ctypes extraction must bind to the exact archived libc: the offline
prepare sets an isolated empty `sysroot` (profile-private `gdb-empty-sysroot`)
plus the flat `xy/` solib-search-path, so GDB never falls back to a same-named
host libc with a different Build ID. This is a general tar-replay fix, not an
Elixir special case.

## Local API acceptance (same-core persistent session)

A single resident `--local-api` session over the same formal core verifies the
structured BEAM endpoints and console commands against the real fixture objects.

```bash
./maze --tar testdata/erlang/20260814-elixir-1.18.4-otp27/coredump-<PID>-*.tar.gz \
  --local-api --no-cpp --json-output \
  --output-dir <session>/results --logdir <session>/work &
# discover BASE from the session log (/api/status log_file/workspace_dir)
curl -fsS "$BASE/api/status" | jq '{log_file, ready}'
curl -fsS "$BASE/api/capabilities" | jq '.endpoints'
```

Verified on the formal core:
- `/api/status`, `/api/capabilities`, and all 8 BEAM endpoints (`erlang-runtime`,
  `erlang-search`, `erlang-object`, `erlang-root-path`, `erlang-aggregate`,
  `erlang-roots`, `erlang-reachable`, `erlang-dominator`). Runtime overview
  matches Text/JSON identity: F94 Build ID, OTP 27, ERTS 15.2.7,
  flavor=elixir 1.18.4 verified with the 3 evidence records,
  L4 / global-term-graph / complete / exact.
- Real objects: the exact 8000-byte shared Binary (sub-bits(8000) → BinRef →
  refc Binary chain with worker + literal referrers), the 16-byte detached slice
  (heap binary, logical 16, no chain), root path rooted at the worker, exact
  persistent key `{maze, persistent}` and ETS `maze_ets` (3 rows), bignum
  `123456789012345678901234567890`, sentinel atom, and the persistent map's
  struct/map/list/tuple/local closure with its result.
- `/api/exec`: `text 500`, `p`, `ref`, `ref-dot`, `sizetree`, plus console
  aliases `erlang-search`, `erlang-object`, `erlang-root-path`,
  `erlang-aggregate`, `erlang-runtime`. Retained/dominator results are
  published only because the graph is complete/exact.

Stop the session with SIGTERM and confirm no Maze/GDB process remains.

### Formal same-core acceptance script

`accept_local_api.py` automates the full acceptance in one command. It spawns
one Maze subprocess with `--local-api --json-output --output-dir <session>/results
--logdir <session>/work` (Maze and core as absolute paths, working directory set
to the session so ref/sizetree artifacts land inside it), waits for readiness,
and verifies:

- the v28 contract from the session's own `maze-result.json`:
  `term_unsupported_count==0`, `graph_status==complete`,
  `term_graph_status==complete`, `term_graph_precision==exact`, every
  `*_status` complete with `flavor_status=verified`, and
  `known_size == allocator_native_covered_bytes`;
- identity and the full contract over `/api/erlang-runtime` overview;
- all 8 structured BEAM endpoints;
- the `/api/exec` console commands;
- the DUAL-FORM sub-binary chain located deterministically via
  `/api/erlang-roots source=process-dictionary` (roots.go exposes every ProcDict
  bucket as a root; the binary inventory and the dictionary pages are fully
  paginated to `truncated==false`, and missing/duplicate keys, multiple
  8000-byte refc binaries, truncated pagination, or ambiguous BinRef chains all
  fail closed).

The session directory is removed in the `finally` block after terminate/wait;
the repository root and any user-owned maze-result.json are never touched.

```bash
python3 testdata/erlang/20260814-elixir-1.18.4-otp27/accept_local_api.py \
  --core testdata/erlang/20260814-elixir-1.18.4-otp27/coredump-140-1786728307.tar.gz \
  --ground-truth testdata/erlang/20260814-elixir-1.18.4-otp27/ground-truth.txt
```

Passes on both ASLR runs (Run A PID 140 and Run B PID 142, the second via the
PID-padding wrapper). The summary-level `validate.py`
checks the ground-truth constants and the 8000-byte Binary topology; the graph
dual-form chain is verified by this Local API acceptance script.

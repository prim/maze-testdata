# OTP 27.3.4.1 ordinary-JIT root fixture

This fixture locks Maze's first production Erlang target:

- OTP 27.3.4.1 / ERTS 15.2.7
- Linux x86-64, JIT `beam.smp`
- GNU Build ID `c3db37cbc86ec25b96b6e69b4b52ea22e7c20bc1`
- embedded `maze-erlang-layout-v28`

Eight recursive Erlang workers keep normal schedulers in JIT code while the
core is captured. The validator checks automatic embedded-layout selection,
complete global graph recovery, conservative native roots, reachability and
the major runtime inventories.

Run from the Maze repository root:

```bash
python3 testdata/run_test.py erlang/20260805-otp27-jit-roots
```

To regenerate, point `OTP_ROOT` at the exact supported OTP build, compile the
module, and use the project's one-shot capture tool:

```bash
OTP_ROOT="$PWD/tmp/otp-27.3.4.1/otp_src_27.3.4.1"
"$OTP_ROOT/bin/erlc" -o testdata/erlang/20260805-otp27-jit-roots \
  testdata/erlang/20260805-otp27-jit-roots/maze_scheduler_active_fixture.erl
python3 cmd/maze-gen-coredump.py \
  -o testdata/erlang/20260805-otp27-jit-roots -t 120 \
  "MAZE_ERLANG_GROUND_TRUTH=$PWD/tmp/otp27-jit-fixture.term $OTP_ROOT/bin/erl +S 2:2 +SDcpu 1 +SDio 1 -pa $PWD/testdata/erlang/20260805-otp27-jit-roots -noshell -s maze_scheduler_active_fixture start"
```

The ground-truth file is diagnostic capture evidence and is intentionally kept
under `tmp/`, not in the fixture contract.

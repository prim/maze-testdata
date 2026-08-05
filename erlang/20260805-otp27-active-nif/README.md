# OTP 27.3.4.1 active-NIF root fixture

This is the native-boundary companion to the ordinary-JIT OTP 27 fixture. It
locks the same OTP 27.3.4.1 / ERTS 15.2.7 Linux x86-64 `beam.smp` Build ID and
requires Maze to select its embedded v28 layout without `MAZE_ERLANG_LAYOUT`.

The fixture keeps one normal, one dirty-CPU and one dirty-IO scheduler inside a
NIF. Each active environment owns a 50,000-cell list and binary payload; a
fourth independent environment, NIF resources, a process monitor, a shared
binary and native allocation remain live. This exercises exact published X
roots plus conservative GPR/C-stack roots and the candidate-only reachability
gap.

Run from the Maze repository root:

```bash
python3 testdata/run_test.py erlang/20260805-otp27-active-nif
```

To regenerate with the exact supported OTP build:

```bash
OTP_ROOT="$PWD/tmp/otp-27.3.4.1/otp_src_27.3.4.1"
FIXTURE="$PWD/testdata/erlang/20260805-otp27-active-nif"
cc -O2 -g -fPIC -shared \
  -I"$OTP_ROOT/erts/emulator/beam" \
  -I"$OTP_ROOT/erts/include/x86_64-pc-linux-gnu" \
  -o "$FIXTURE/maze_nif_resource_fixture.so" \
  "$FIXTURE/maze_nif_resource_fixture.c"
"$OTP_ROOT/bin/erlc" -o "$FIXTURE" "$FIXTURE/maze_nif_resource_fixture.erl"
python3 cmd/maze-gen-coredump.py \
  -o "$FIXTURE" -t 120 \
  "MAZE_NIF_LIBRARY=$FIXTURE/maze_nif_resource_fixture MAZE_ERLANG_GROUND_TRUTH=$PWD/tmp/otp27-active-nif-fixture.txt $OTP_ROOT/bin/erl +S 4:4 +SDcpu 2 +SDio 2 +MTatags true -pa $FIXTURE -noshell -s maze_nif_resource_fixture start"
```

The generated truth file is diagnostic evidence under `tmp/`; the committed
validator checks the recovered runtime graph directly.

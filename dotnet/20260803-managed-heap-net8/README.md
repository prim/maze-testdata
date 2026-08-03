# .NET 8 managed heap compatibility fixture

This is the Workstation GC fixture from `20260802-managed-heap-workstation`, compiled for
`net8.0` and captured with the .NET 8.0.29 Linux x64 runtime. It runs the full shared validator,
including strings, fields, containers, roots, dominators, Task/ValueTask, exceptions, threads,
monitors, collectible ALC identity, token reset/reuse mismatch, and the .NET 8 Channel layouts.

The fixture guards a ClrMD/DAC compatibility edge: `ClrType.Fields` must not be queried for the
GC `Free` pseudo-type. .NET 8's DAC can terminate the helper process on that invalid metadata
request even though normal heap walking is valid.

It also guards the thread-static root fallback. Treating every `ClrThreadStaticField` as an object
reference makes .NET 8's DAC crash while reading primitive/value-type fields or an unresolved shared
generic such as `System.Collections.Immutable.AllocFreeConcurrentStack<T1>.t_stack`. The helper must
only call `ReadObject` for `IsObjectReference` fields and must skip field-address enrichment while the
declaring owner still contains unresolved `T1`/`T2` placeholders. Normal object-reference
thread-statics remain roots, and the cached root context still includes their thread/AppDomain/ALC
identity.

Regenerate from the Maze repository root:

```bash
tmp/dotnet-install.sh --runtime dotnet --version 8.0.29 \
  --install-dir tmp/dotnet-runtime-8 --no-path

dotnet build testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release -p:TargetFramework=net8.0 -p:TargetFrameworks=net8.0 \
  --artifacts-path tmp/dotnet-fixture-net8-artifacts

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260803-managed-heap-net8 \
  "DOTNET_ROOT=$PWD/tmp/dotnet-runtime-8 MAZE_EXPECT_SERVER_GC=0 $PWD/tmp/dotnet-runtime-8/dotnet $PWD/tmp/dotnet-fixture-net8-artifacts/bin/MazeDotnetFixture/release_net8.0/MazeDotnetFixture.dll"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260803-managed-heap-net8
```

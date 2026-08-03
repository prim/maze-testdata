# .NET 11 preview managed heap compatibility fixture

This is the Workstation GC fixture from `20260802-managed-heap-workstation`, compiled for
`net11.0` and captured with .NET SDK/runtime 11.0.100-preview.6.26359.118 on Linux x64. It runs
the full shared validator, including strings, fields, containers, roots, dominators,
Task/ValueTask, exceptions, threads, monitors, collectible ALC identity, and token reset/reuse
mismatch. Channel coverage includes bounded/unbounded content, the circular waiter-head layout and
the runtime's rendezvous channel shape.

Preview 6 has one evidence-level limitation: the waiter thread stack contains
`System.Threading.Lock.TryEnterSlow`, `Lock.Enter`, and `Monitor.Enter`, while the matching
SyncBlock reports `WaitingThreadCount=0`. The validator therefore checks the held object,
holder, recursion, and physical waiter stack independently. It does not infer a waiter-to-lock
edge from the fixture's thread name.

Regenerate from the Maze repository root:

```bash
tmp/dotnet-install.sh --channel 11.0 --quality preview \
  --install-dir tmp/dotnet-sdk-11 --no-path

tmp/dotnet-sdk-11/dotnet build \
  testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release -p:TargetFramework=net11.0 -p:TargetFrameworks=net11.0 \
  --artifacts-path tmp/dotnet-fixture-net11-artifacts

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260803-managed-heap-net11 \
  "DOTNET_ROOT=$PWD/tmp/dotnet-sdk-11 MAZE_EXPECT_SERVER_GC=0 $PWD/tmp/dotnet-sdk-11/dotnet $PWD/tmp/dotnet-fixture-net11-artifacts/bin/MazeDotnetFixture/release_net11.0/MazeDotnetFixture.dll"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260803-managed-heap-net11
```

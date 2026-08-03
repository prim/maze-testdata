# .NET 9 managed heap compatibility fixture

This is the Workstation GC fixture from `20260802-managed-heap-workstation`, compiled for
`net9.0` and captured with the .NET 9.0.18 Linux x64 runtime. It runs the full shared validator,
including strings, fields, containers, roots, dominators, Task/ValueTask, exceptions, threads,
monitors, collectible ALC identity, token reset/reuse mismatch, and both bounded/unbounded Channel
content plus the .NET 9 waiter-tail layout.

Regenerate from the Maze repository root:

```bash
tmp/dotnet-install.sh --runtime dotnet --version 9.0.18 \
  --install-dir tmp/dotnet-runtime-9 --no-path

dotnet build testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release -p:TargetFramework=net9.0 -p:TargetFrameworks=net9.0 \
  --artifacts-path tmp/dotnet-fixture-net9-artifacts

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260803-managed-heap-net9 \
  "DOTNET_ROOT=$PWD/tmp/dotnet-runtime-9 MAZE_EXPECT_SERVER_GC=0 $PWD/tmp/dotnet-runtime-9/dotnet $PWD/tmp/dotnet-fixture-net9-artifacts/bin/MazeDotnetFixture/release_net9.0/MazeDotnetFixture.dll"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260803-managed-heap-net9
```

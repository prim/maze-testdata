# .NET 10 managed heap fixture (Server GC)

This uses the same source as the Workstation GC fixture, with four logical processors and
Server GC enabled. The validator requires multiple logical heaps and the same managed/native
semantics as the Workstation capture.
That includes deterministic multiple static-root paths, same-assembly types loaded into default and collectible
ALCs, and named-thread monitor contention.
It also validates the shared pending `ValueTask`/`IValueTaskSource` fixture, its continuation state,
and a reset/reuse fixture whose retained old awaiter token no longer matches the source version.

Regenerate from the Maze repository root after building the source fixture:

```bash
dotnet build testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release --artifacts-path tmp/dotnet-fixture-artifacts

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260802-managed-heap-server \
  "DOTNET_gcServer=1 DOTNET_PROCESSOR_COUNT=4 DOTNET_GCDynamicAdaptationMode=0 DOTNET_GCHeapCount=4 MAZE_EXPECT_SERVER_GC=1 dotnet tmp/dotnet-fixture-artifacts/bin/MazeDotnetFixture/release/MazeDotnetFixture.dll"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260802-managed-heap-server
```

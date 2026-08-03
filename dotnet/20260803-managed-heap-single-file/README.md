# .NET 10 self-contained single-file fixture

This Linux x64 fixture publishes the shared managed-heap workload as a self-contained single-file
application. `DotNetRuntimeInfo` is matched to an external CoreCLR/DAC directory by exact GNU Build
ID. The external `MazeDotnetFixture.Plugin.dll` is used only to create the fixture's collectible
AssemblyLoadContext, matching a real single-file application that loads a plugin from disk.

Regenerate from the Maze repository root:

```bash
dotnet publish testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release -r linux-x64 --self-contained true \
  -p:PublishSingleFile=true -p:PublishReadyToRun=false \
  -o tmp/dotnet-publish-shapes/single-file

cp testdata/dotnet/20260802-managed-heap-workstation/bin/Release/net10.0/linux-x64/MazeDotnetFixture.dll \
  tmp/dotnet-publish-shapes/single-file/MazeDotnetFixture.Plugin.dll

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260803-managed-heap-single-file -t 120 \
  "MAZE_FIXTURE_ASSEMBLY_PATH=$PWD/tmp/dotnet-publish-shapes/single-file/MazeDotnetFixture.Plugin.dll \
  ./tmp/dotnet-publish-shapes/single-file/MazeDotnetFixture"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260803-managed-heap-single-file
```

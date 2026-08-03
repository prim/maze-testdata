# .NET 10 self-contained ReadyToRun fixture

This Linux x64 fixture publishes the shared managed-heap workload as a self-contained
application with `PublishReadyToRun=true`. It uses capture manifest v2 and validates that
all managed object, root, dominator, Task, async, exception, thread, and monitor views remain
available when the application entry assembly contains a ReadyToRun header.

Regenerate from the Maze repository root:

```bash
dotnet publish testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release -r linux-x64 --self-contained true \
  -p:PublishSingleFile=false -p:PublishReadyToRun=true \
  -o tmp/dotnet-publish-shapes/self-contained-r2r

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260803-managed-heap-self-contained-r2r -t 120 \
  "./tmp/dotnet-publish-shapes/self-contained-r2r/MazeDotnetFixture"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260803-managed-heap-self-contained-r2r
```

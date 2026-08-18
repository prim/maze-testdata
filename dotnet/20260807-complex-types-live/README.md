# C#/.NET complex-types live fixture

这个 fixture 对照 `python/20260129-complex-types` 的对象混合，专门用于
Linux x64 / .NET 10 CoreCLR 的 live profile。它不依赖外部包，所有对象由一个
静态 `Root.Storage` 保持可达，便于在 Web UI 中沿类型、字段、容器、root、引用图和
retained/dominator 继续下钻。

覆盖内容：

- `List<T>` 的空、单元素、多元素、混合和嵌套形态（约 2,800 个）；
- `Tuple1`/`Tuple2`/`Tuple3`/`MixedTuple` 自定义 tuple-like class（约 2,500 个）；
- `SimpleClass`、`PersonClass`、`GameEntity`、带 parent/child 环的 `TreeNode`（约 2,400 个）；
- `HashSet<int>`、中等集合和 `ImmutableHashSet<int>`（约 1,200 个）；
- 短/中/长 `byte[]`、独立 mutable buffers 和一个跨多个 owner 共享的 2 MiB `SharedAsset`；
- 简单、嵌套、宽字典，以及 `SortedDictionary`、`ConcurrentDictionary`、计数字典（约 2,400 个）；
- 短/中/长/Unicode `string`（约 2,000 个）；
- 大整数、浮点和 `System.Numerics.Complex` boxed values（约 1,300 个）；
- `Queue<int>`、`Point`、`Rectangle`（约 1,000 个）；
- 一个有 root 的 `CycleNode -> CycleNode` 环、一个只由 `WeakReference` 指向的无 root 对照，
  以及重复引用共享对象，验证 reachability、去重和 free/garbage 边界。

## Build and run

从 Maze 仓库根目录执行：

```bash
mkdir -p tmp/csharp-complex-types-live
dotnet build testdata/dotnet/20260807-complex-types-live/MazeComplexTypesFixture.csproj \
  -c Release -o tmp/csharp-complex-types-live/bin
cd tmp/csharp-complex-types-live
dotnet bin/MazeComplexTypesFixture.dll
```

看到 `READY FOR MAZE` 后，在另一个终端对输出的 PID 做 live Web profile：

```bash
./maze --mode standalone --pid <PID> --http \
  --logdir tmp/csharp-complex-types-live/maze-log \
  --output-dir tmp/csharp-complex-types-live/maze-output
```

打开 Maze 输出的 `/v2/#/<session-id>` URL。先看 `Overview / By Size`，再进入 `Managed`，
按 `MazeCSharpComplexTypes` 过滤；`Payload`、`PersonClass`、`GameEntity`、`TreeNode`、
`Dictionary`、`List` 和 `SharedAsset` 都可以继续查看对象详情、root/referrer、引用图和 retained。

fixture 的输入命令：

```text
gc      # Full GC 后重新打印计数
summary # 打印对象分类计数
exit    # 结束 fixture
```

这是 live-only fixture；生成可归档 core 时使用项目现有的 `createdump --full`/tar 流程，
不要把 core、Maze workspace 或 `maze-result.json` 写入这个 testdata 目录。

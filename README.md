# maze-testdata

Core dumps and expected outputs for maze regression testing.

## 目录结构

每个测试用例是一个目录，包含：

- `*.tar.gz` — coredump 打包文件（由 `maze-tar-coredump.py` 生成）
- `validate.py` — 验证脚本，定义 `validate(data)` 函数
- `*.cpp` / 源码 — 测试程序源码（仅供参考，不参与测试流程）

## 运行测试

```bash
# 单个测试
python3 testdata/run_test.py cpp/20260211-jemalloc-5-3-0-multithread

# 多个测试
python3 testdata/run_test.py cpp/20260210-jemalloc-5-0-0 cpp/20260210-jemalloc-5-3-0

# 带 --py-merge 模式
python3 testdata/run_test.py --py-merge python/20260201-class-merge
```

### Go runtime core

```bash
# Go 1.20.14-1.26.0 durable pure-Go matrix；hash 校验后串行回放
python3 testdata/golang/run_runtime_matrix.py

# 使用精确 toolchain 串行重抓全部版本
python3 testdata/golang/run_runtime_matrix.py --generate

# 固定 pure-Go runtime/object/root/garbage/dominator 回归
python3 testdata/run_test.py golang/20260803-runtime-core

# 同一进程中的 Go runtime + cgo/glibc ptmalloc 回归
python3 testdata/run_test.py golang/20260803-cgo-runtime-core

# Go plugin、多 moduledata、external ELF DWARF 和 plugin global roots 回归
python3 testdata/run_test.py golang/20260803-plugin-runtime-core

# durable PIE 与 stripped runtime + exact DWARF ELF，含 ELF/Build ID 校验
python3 testdata/golang/run_executable_forms.py

# durable artifact 派生的 15 项缺页、损坏 runtime/DWARF/GC program 和错误 ELF
./maze --build
python3 testdata/golang/run_corrupt_matrix.py

# 可选的 pure-Go live PID -> exact core tar -> replay 全输出等价性回归
./maze --build
MAZE_GOCORE_LIVE_TAR_INTEGRATION=1 \
  go test ./golang_runtime -run '^TestMazeLiveTarEquivalence$' -count=1 -v

# 可选的 cgo + ptmalloc live/tar 全输出等价性回归
MAZE_GOCORE_CGO_LIVE_TAR_INTEGRATION=1 \
  go test ./golang_runtime -run '^TestMazeCgoLiveTarEquivalence$' -count=1 -v

# 真实 200,000-object live/core CPU、RSS、输出规模门槛
PYTHONDONTWRITEBYTECODE=1 \
  python3 testdata/golang/run_performance_gate.py
```

七版本 pure-Go matrix、cgo/plugin 和两个 executable-form fixture 都包含 source、
generator、validator、machine-readable manifest 和压缩 core artifact。runner
还验证 tar 中确实包含 binary SHA-256 匹配的 executable。PIE case 固定 ET_DYN
和 ASLR；stripped case 同时固定无 DWARF runtime ELF、匹配的 DWARF ELF 和相同
Go Build ID。plugin case 要求恢复 192 个插件定义节点、
192 个 4 KiB backing array、一个 plugin-only 5 MiB array 和插件栈帧，并保留
真实 `r--p/r-xp/rw-p` maps。Go 1.23 matrix replay 会额外验证没有 DWARF type
mapping 的 reflect-generated 20,000-pointer GC program。corrupt matrix 还要求
CoreInput v2 拒绝内容 SHA-256 不匹配但 PT_LOAD 布局相同的 substitute plugin；
前 14 个早期失败只有 header + diagnostic，第 15 个 GC-program 晚期失败以第
43 条 fatal diagnostic 结束，所有失败都不得有 trailer 或原始 panic stack。
pure-Go/cgo live/tar 集成检查目标进程在 GDB detach 后仍存活、text 字节一致，并要求 JSON 除
`generated_at` 外结构完全一致；cgo 的 native class ID 不做归一化。动态产物
分别位于 `./tmp/golang-live-tar/` 和 `./tmp/golang-cgo-live-tar/`，测试串行执行，
并恢复仓库根既有 result/log 文件。

性能 runner 使用 Go 1.25.6 构造精确 200,000 个独立 64-byte
`main.benchNode`，每 20 ms 采样完整 Maze/helper 进程树；它校验 typed object
数量、完整 NDJSON trailer/count/hash、Maze class 汇总，并对 wall、child CPU、
peak RSS、NDJSON/JSON bytes 和 graph 数量执行数值门槛。结果位于
`./tmp/golang-performance-gate/results.json`。低于 200,000 对象必须显式加
`--smoke`，不计入发布验收；加 `--keep-large-artifacts` 才保留 sparse core 和
完整 helper NDJSON。

## 生成测试用的 coredump tar.gz

### 流程

1. 编译测试程序
2. 运行程序（如需 jemalloc，用 `LD_PRELOAD` 加载）
3. 等待程序输出 `READY FOR GCORE`
4. 用 `gcore <pid>` 抓取 coredump
5. **回到项目根目录**，用 `maze-tar-coredump.py` 打包
6. 将生成的 tar.gz 移到测试目录

### 示例（jemalloc 多线程测试）

```bash
# 1. 编译
g++ -g -O0 -pthread -ldl -o testdata/cpp/20260211-jemalloc-5-3-0-multithread/jemalloc_multithread_test \
    testdata/cpp/20260211-jemalloc-5-3-0-multithread/jemalloc_multithread_test.cpp

# 2. 运行（后台）
LD_PRELOAD=3rd/jemalloc-5-3-0/lib/libjemalloc.so.2 \
    testdata/cpp/20260211-jemalloc-5-3-0-multithread/jemalloc_multithread_test &

# 3. 等 READY FOR GCORE 后抓 coredump
gcore -o testdata/cpp/20260211-jemalloc-5-3-0-multithread/core <pid>

# 4. 回到项目根目录打包（重要！）
python3 cmd/maze-tar-coredump.py testdata/cpp/20260211-jemalloc-5-3-0-multithread/core.<pid>

# 5. 移动 tar.gz 到测试目录
mv coredump-<pid>-*.tar.gz testdata/cpp/20260211-jemalloc-5-3-0-multithread/

# 6. 清理
rm testdata/cpp/20260211-jemalloc-5-3-0-multithread/core.<pid>
kill <pid>
```

如果抓 core 时同时保存了准确的 `/proc/<pid>/maps`，应显式传入，避免仅由
core/GDB 重建时丢失线程栈和内核辅助映射：

```bash
python3 cmd/maze-tar-coredump.py \
  --maps testdata/cpp/<case>/maps.snapshot \
  testdata/cpp/<case>/core.<pid>
```

未提供 `--maps` 时仍保留原有 GDB fallback，适用于目标进程已经退出、只有
core 的场景。

### 踩坑点

1. **`maze-tar-coredump.py` 必须在项目根目录执行**
   coredump 中记录的 exe 路径是相对路径（如 `testdata/cpp/.../jemalloc_multithread_test`），
   如果在测试子目录执行打包脚本，GDB 会找不到 exe 文件，导致 `create_fake_maps` 失败。

2. **打包后的 tar.gz 生成在当前目录（项目根），需要手动移到测试目录**
   `maze-tar-coredump.py` 会在 cwd 生成 `coredump-<pid>-<timestamp>.tar.gz`，
   以及临时文件 `<pid>.exe`、`<pid>.md5`、`maps`（脚本会自动清理临时文件）。

3. **编译后的二进制不要删除或移动**
   打包脚本需要通过 coredump 中的路径找到原始 exe 文件，
   如果编译产物被移走，`get_program_path` 虽然能解析出路径，但后续 GDB 加载会失败。

4. **jemalloc 版本的 so 文件路径**
   项目 `3rd/` 目录下有预编译的各版本 jemalloc：
   `3rd/jemalloc-5-3-0/lib/libjemalloc.so.2` 等，用 `LD_PRELOAD` 加载即可。

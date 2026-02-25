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

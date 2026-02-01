# C++ Basic Malloc Test

基础 C++ 内存分配测试案例，验证 Maze 对 C++ 类实例和 malloc 分配的识别能力。

## 测试目标

1. **C++ 类实例识别** - 通过 vtable 指针识别 `class A` 实例
2. **malloc 块分类** - 区分不同大小的 malloc 分配

## 测试数据

| 类型 | 请求大小 | 实际 Chunk 大小 | 数量 |
|------|----------|-----------------|------|
| class A (new) | 8 bytes | 24 bytes | 80,000 |
| malloc(16) | 16 bytes | 24 bytes | 80,000 |
| malloc(32) | 32 bytes | 40 bytes | 80,000 |
| malloc(64) | 64 bytes | 72 bytes | 80,000 |

> **注意**: ptmalloc 的最小 chunk 对齐导致实际大小与请求大小不同

## 验证结果 (2026-02-01)

运行 Maze 分析后的结果：

```
Order     Amount    TotalSize    AvgSize  Type
    1      80000         5.5M         72  (weak) malloc(72)
    2      80000         3.1M         40  (weak) malloc(40)
    3      80000         1.8M         24  (weak) malloc(24)
    4      80000         1.8M         24  (<32) C++ A
```

✅ **所有 80,000 个 class A 实例被正确识别**
✅ **三种 malloc 大小分别被正确分类和计数**

## 文件说明

- `basic_malloc_test.cpp` - 测试源代码
- `basic_malloc_test` - 编译后的可执行文件
- `coredump-*.tar.gz` - 打包的 coredump 文件
- `validate.py` - 验证脚本
- `maze-result.json` - Maze 分析结果
- `maze_output.txt` - Maze 运行日志

## 使用方法

### 重新生成 coredump

```bash
# 编译
g++ -O0 -g basic_malloc_test.cpp -o basic_malloc_test

# 运行并捕获 coredump
./basic_malloc_test &
# 等待 "READY FOR GCORE" 输出
sudo gcore $(pgrep basic_malloc_test)

# 打包
python3 /path/to/maze/cmd/maze-tar-coredump.py core.<pid>
```

### 运行 Maze 分析

```bash
cd /path/to/maze
./maze --tar testdata/cpp/20260201-basic-malloc/coredump-*.tar.gz --text --json-output --cpp
```

### 验证结果

```bash
python3 validate.py maze-result.json
```

## 预期输出

验证脚本应该输出：
- `[Check 1] class A instances... ✓`
- `[Check 2] malloc blocks... ✓`
- `[Check 3] Small chunk distribution... ✓`
- `All validations passed!`
# PyMerge 模式测试用例

**日期**: 2026-02-01  
**目的**: 测试 `--py-merge` 选项的内存合并功能

## 背景

`--py-merge` 选项用于将 `refcnt=1` 的子对象内存合并到父对象统计。这个测试用例验证该功能是否正确工作。

## 测试原理

### 独占 vs 共享对象

| 类型 | refcnt | 合并行为 |
|------|--------|----------|
| 独占对象 (exclusive) | = 1 | 应该被合并到父对象 |
| 共享对象 (shared) | > 1 | 不应该被合并 |

### 测试对象

| 组 | 对象类型 | 数量 | 预期行为 |
|----|---------|----|----------|
| exclusive_dicts | dict + 独占 str | 100 | 每个 dict 合并 10 个 str |
| shared_dicts | dict + 共享 str | 100 | str 不被合并 |
| mixed_dicts | dict + 混合 | 100 | 只合并独占部分 |
| nested_dicts | dict 嵌套 dict | 50 | 多层合并 |
| exclusive_lists | list + 独占 str | 100 | list 元素被合并 |
| number_dicts | dict + int/float | 100 | 数值被合并 |

## 验证方法

### 方法 1: 基本验证（单次运行）

```bash
# 生成测试数据后
python testdata/run_test.py python/20260201-py-merge
```

### 方法 2: 对比验证（推荐）

```bash
# 不启用 merge
./maze --tar testdata/python/20260201-py-merge/coredump-*.tar.gz --text --json-output
mv maze-result.json result-no-merge.json

# 启用 merge
./maze --tar testdata/python/20260201-py-merge/coredump-*.tar.gz --text --json-output --py-merge --skip-prelude
mv maze-result.json result-with-merge.json

# 对比验证
python testdata/python/20260201-py-merge/validate.py result-no-merge.json result-with-merge.json
```

## 预期结果差异

### exclusive_dicts 的 avg_size

| 模式 | avg_size | 说明 |
|------|----------|------|
| 无 --py-merge | ~192 bytes | 只有 dict 本身 |
| 有 --py-merge | ~700+ bytes | dict + 10 个 str |

### str 对象数量

| 模式 | str 数量 | 说明 |
|------|----------|------|
| 无 --py-merge | ~3000+ | 所有 str 独立统计 |
| 有 --py-merge | ~200 | 只有 refcnt>1 的 str |

## 如何生成测试数据

```bash
# 1. 运行测试程序
python testdata/python/20260201-py-merge/py_merge_test.py &
PID=$!
sleep 2

# 2. 生成 coredump
gcore $PID

# 3. 打包
cd cmd && python maze-tar-coredump.py ../core.$PID && cd ..

# 4. 移动文件
mv cmd/coredump-$PID-*.tar.gz testdata/python/20260201-py-merge/

# 5. 清理
rm -f core.$PID cmd/$PID.exe cmd/$PID.md5 cmd/maps
kill $PID
```

## 文件结构

```
testdata/python/20260201-py-merge/
├── README.md              # 本文件
├── py_merge_test.py       # 测试程序
├── validate.py            # 验证脚本
└── coredump-*.tar.gz      # 测试数据 (需要生成)
```

## 已知问题

参见 `dev-log/2026-02-01-py-merge-analysis.md` 中关于 PyMerge 模式潜在 bug 的分析。

# 02-collections: 集合类型测试

验证 Maze 对 JS 集合类型的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Map(5) | 1,000 | 每个含 5 个键值对 |
| Set(5) | 1,000 | 每个含 5 个元素 |
| WeakMap(1) | 1,000 | 每个含 1 个键值对 |
| WeakSet(1) | 1,000 | 每个含 1 个元素 |
| Array (dense) | 1,000 | 密集数组 |
| Array (sparse) | 1,000 | 稀疏数组 |
| Array (objects) | 1,000 | 对象数组，每个 10 个元素 |
| ArrayBuffer | 1,000 | 64-128 字节 |
| DataView | 1,000 | 32 字节 |
| TypedArray (11种) | 各100-400 | Int8~BigUint64，数量各不同 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-02-collections
```

# 03-binary-types: 二进制数据类型测试

验证 Maze 对二进制数据类型的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Buffer | 1,000 | 64-128 字节 |
| ArrayBuffer | 1,000 | 128 字节 |
| SharedArrayBuffer | 1,000 | 64 字节 |
| DataView | 1,000 | 32 字节 |
| Int8Array | 1,000 | 16 元素 |
| Uint8Array | 1,000 | 16 元素 |
| Uint8ClampedArray | 1,000 | 16 元素 |
| Int16Array | 1,000 | 16 元素 |
| Uint16Array | 1,000 | 16 元素 |
| Int32Array | 1,000 | 16 元素 |
| Uint32Array | 1,000 | 16 元素 |
| Float32Array | 1,000 | 16 元素 |
| Float64Array | 1,000 | 16 元素 |
| BigInt64Array | 1,000 | 16 元素 |
| BigUint64Array | 1,000 | 16 元素 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-03-binary-types
```

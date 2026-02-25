# 06-builtin-objects: 内置对象类型测试

验证 Maze 对 JavaScript 内置对象类型的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Date | 1,000 | 不同时间戳 |
| RegExp | 1,000 | 带 gim 标志 |
| Error | 1,000 | 带 code 属性 |
| TypeError | 1,000 | 类型错误 |
| RangeError | 1,000 | 范围错误 |
| Promise (pending) | 1,000 | 未决 Promise |
| Promise (resolved) | 1,000 | 已解决 Promise |
| Promise (rejected) | 1,000 | 已拒绝 Promise |
| Proxy | 1,000 | 带 get/set handler |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-06-builtin-objects
```

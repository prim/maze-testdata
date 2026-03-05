# stringify-test: V8 对象 Stringify 基础测试

验证 Maze 对常见 V8 堆对象类型的 stringify 输出格式。

## 测试数据

每种类型 N=100 个实例，覆盖 11 类对象：

| 类别 | 对象类型 | 预期 stringify 格式 |
|------|----------|-------------------|
| 1 | Oddball holder | `{Object: u, n, t, f}` |
| 2 | Array (dense/sparse/empty/mixed) | `<Array(N)>` |
| 3 | Promise (pending/fulfilled/rejected) | `<Promise(status)>` |
| 4 | RegExp | `(RegExp)` |
| 5 | Date (normal/invalid/epoch) | `(Date)` |
| 6 | ArrayBuffer | `<ArrayBuffer(N)>` |
| 7 | TypedArray (11种) | `<Uint8Array(N)>`, `<Int32Array(N)>`, ... |
| 8 | DataView | `(DataView)` |
| 9 | Generator/AsyncGenerator | `(AsyncGenerator)` |
| 10 | WeakMap/WeakSet | `<WeakMap(N)>`, `<WeakSet(N)>` |
| 11 | Error/TypeError/RangeError | `Error`, `TypeError`, `RangeError` |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — Node.js v20.20.0 的 coredump

## 运行测试

```bash
# 自动化测试
python3 testdata/run_test.py nodejs/20260213-stringify-test

# 手动测试
./maze --tar testdata/nodejs/20260213-stringify-test/coredump-*.tar.gz \
    --text --json-output --limit 200
python3 testdata/nodejs/20260213-stringify-test/validate.py maze-result.json
```

## 重新生成 coredump

```bash
NODE=/home/hcjn0770/.nvm/versions/node/v20.20.0/bin/node
$NODE --expose-gc testdata/nodejs/20260213-stringify-test/test.js &
# 等待 "Waiting for gcore..."
gcore -o /tmp/coredump $!
python3 cmd/maze-tar-coredump.py /tmp/coredump.$!
mv coredump-*.tar.gz testdata/nodejs/20260213-stringify-test/
```

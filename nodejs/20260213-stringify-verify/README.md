# stringify-verify: V8 对象 Stringify 格式验证

验证 Maze 对各种 V8 堆对象类型的 stringify 输出格式是否正确。

## 测试数据

每种类型 N=200 个实例，覆盖 23 类对象：

| 类别 | 对象类型 | 预期 stringify 格式 |
|------|----------|-------------------|
| 1 | HeapNumber | 通过 `{Object: val}` 间接验证 |
| 2 | String | `(String) [0-64]`, `[65-256]`, `[257-1K]`, `[1K-4K]`, `[>4K]` |
| 3 | Oddball holder | `{Object: u, n, t, f}` |
| 4 | JSArray | `<Array(N)>` |
| 5 | JSObject | `{Object: field1, field2, ...}` |
| 6 | Function | `(Function: name @source)` |
| 7 | Promise | `<Promise(pending\|fulfilled\|rejected)>` |
| 8 | RegExp | `(RegExp)` |
| 9 | Date | `(Date)` |
| 10 | ArrayBuffer | `<ArrayBuffer(N)>` |
| 11 | TypedArray (11种) | `<Uint8Array(N)>`, `<Int32Array(N)>`, ... |
| 12 | DataView | `(DataView)` |
| 13 | Generator/AsyncGenerator | `(AsyncGenerator)` |
| 14 | Set/Map | `<Set(N)>`, `<Map(N)>` |
| 15 | WeakMap/WeakSet | `<WeakMap(N)>`, `<WeakSet(N)>` |
| 16 | Error 子类型 (7种) | `Error`, `TypeError`, `RangeError`, ... |
| 17 | Symbol | 通过 holder 对象间接验证 |
| 18 | 引用链 | `{Object: name, arr, map, set, +7 more}` |
| 19 | BigInt | 通过 `{Object: v}` 间接验证 |
| 20 | Iterator | `<ArrayIterator>`, `<StringIterator>` |
| 21 | BoundFunction | `(BoundFunction: name @source)` |
| 22 | SharedArrayBuffer | `<ArrayBuffer(N)>` |
| 23 | Proxy | 通过 target 对象间接验证 |

## 文件说明

- `test.js` — 测试源代码，创建各类型对象并挂在 globalThis 上防止 GC
- `validate.py` — 验证脚本，检查 stringify 格式和对象数量
- `coredump-*.tar.gz` — Node.js v20.20.0 的 coredump

## 运行测试

```bash
# 自动化测试
python3 testdata/run_test.py nodejs/20260213-stringify-verify

# 手动测试
./maze --tar testdata/nodejs/20260213-stringify-verify/coredump-*.tar.gz \
    --text --json-output --limit 300
python3 testdata/nodejs/20260213-stringify-verify/validate.py maze-result.json
```

## 重新生成 coredump

```bash
NODE=/home/hcjn0770/.nvm/versions/node/v20.20.0/bin/node
$NODE --expose-gc testdata/nodejs/20260213-stringify-verify/test.js &
# 等待 "Waiting for gcore..."
gcore -o /tmp/coredump $!
python3 cmd/maze-tar-coredump.py /tmp/coredump.$!
mv coredump-*.tar.gz testdata/nodejs/20260213-stringify-verify/
```

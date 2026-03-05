# refgraph-verify: V8 对象引用图验证测试

验证 Maze 的 `--random-dot` 引用图输出是否正确反映对象间的引用关系。

## 测试数据

每个场景 N=200 个实例，覆盖 20 种引用图模式：

| 场景 | 引用模式 | 预期引用链 |
|------|----------|-----------|
| S1 | 线性引用链 | Object → Object → Object |
| S2 | Map 中间节点 | Object → Map → Object |
| S3 | Set 中间节点 | Object → Set → Object |
| S4 | Array 中间节点 | Object → Array → Object×3 |
| S5 | Promise 引用 | Object → Promise(fulfilled) → Object |
| S6 | 闭包引用 | Object → Function → Context → Object |
| S7 | 多类型混合链 | Object → Map → Array → Set → Object |
| S8 | 树形扇出 | Object → {Map, Set, Array, Date, RegExp, Promise} |
| S9 | 循环引用 | A ↔ B |
| S10 | 三角循环 | A → B → C → A |
| S11 | Map 对象 key | Map → {keyObj, valueObj} |
| S12 | WeakMap 引用 | Object → WeakMap → key/value |
| S13 | Error 引用链 | Object → TypeError |
| S14 | Generator 引用 | Object → Generator → Function |
| S15 | TypedArray→ArrayBuffer | Object → Float64Array → ArrayBuffer |
| S16 | 深层嵌套 (5层) | L0 → L1 → L2 → L3 → L4 |
| S17 | 共享引用 | P1 → shared ← P2 |
| S18 | 嵌套 Map | Map → Map → Object |
| S19 | 嵌套容器 | Set → Map → Array → Object |
| S20 | 综合场景 | session → {user, permissions, cache, handlers} |

## 文件说明

- `test.js` — 测试源代码（20 个引用图场景）
- `validate.py` — 验证脚本（检查一级表格中的类型和数量）
- `coredump-*.tar.gz` — Node.js v20.20.0 的 coredump

## 运行测试

```bash
# 自动化测试
python3 testdata/run_test.py nodejs/20260213-refgraph-verify

# 手动测试
./maze --tar testdata/nodejs/20260213-refgraph-verify/coredump-*.tar.gz \
    --text --json-output --limit 200
python3 testdata/nodejs/20260213-refgraph-verify/validate.py maze-result.json
```

## 手动验证引用图

validate.py 只验证一级表格的类型和数量。引用图的 DOT 输出需要手动验证：

```bash
# 查看某一行的引用图 (DOT 格式)
./.maze --mode postmanprofile --project coredump --user default \
    --profileId <PID> --pid <PID> --random-dot <ROW>

# 例如查看 {Object: type, child} 的引用图
./.maze ... --random-dot 6
```

DOT 输出在 `<<<DOT_BEGIN>>>` 和 `<<<DOT_END>>>` 之间，可用 Graphviz 渲染：

```bash
# 提取 DOT 并渲染为 PNG
... | sed -n '/<<<DOT_BEGIN>>>/,/<<<DOT_END>>>/p' | \
    sed '1d;$d' | dot -Tpng -o graph.png
```

## 重新生成 coredump

```bash
NODE=/home/hcjn0770/.nvm/versions/node/v20.20.0/bin/node
$NODE --expose-gc testdata/nodejs/20260213-refgraph-verify/test.js &
# 等待 "Waiting for gcore..."
gcore -o /tmp/coredump $!
python3 cmd/maze-tar-coredump.py /tmp/coredump.$!
mv coredump-*.tar.gz testdata/nodejs/20260213-refgraph-verify/
```

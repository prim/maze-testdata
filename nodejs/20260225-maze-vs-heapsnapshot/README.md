# 20260225-maze-vs-heapsnapshot

Maze vs chrome-heapsnapshot-parser 对比测试。

## 目的

对比 Maze（分析 coredump）和 chrome-heapsnapshot-parser（分析 .heapsnapshot）对同一 Node.js 进程的分析结果。

## 文件

| 文件 | 说明 |
|------|------|
| test.js | 综合测试用例，生成 heapsnapshot 后等待 gcore |
| compare.py | 对比脚本，读取两个工具的输出并生成差异报告 |

## 覆盖类型

每种 500 个对象：Object, Array, String/Number/Boolean 包装, Map, Set, WeakMap, WeakSet, Uint8Array, Int32Array, Float64Array, Date, RegExp, Error, TypeError, Promise, Function, ArrowFunction, AsyncFunction, SimpleClass, Dog, EventEmitter, Buffer, URL

## 使用方法

```bash
NODE=/home/hcjn0770/.nvm/versions/node/v20.20.0/bin/node

# 1. 运行测试
$NODE --expose-gc test.js &
# 等待 "READY FOR GCORE"

# 2. gcore
gcore -o /home/hcjn0770/coredump $PID

# 3. 打包
cd /home/hcjn0770/github/codemaker-maze
python3 cmd/maze-tar-coredump.py /home/hcjn0770/coredump.$PID
mv coredump-*.tar.gz testdata/nodejs/20260225-maze-vs-heapsnapshot/

# 4. Maze 分析
./maze --tar testdata/nodejs/20260225-maze-vs-heapsnapshot/coredump-*.tar.gz --text --json-output
cp maze-result.json /tmp/maze-result-comparison.json

# 5. 对比
cd testdata/nodejs/20260225-maze-vs-heapsnapshot
python3 compare.py /tmp/maze-result-comparison.json *.heapsnapshot
```

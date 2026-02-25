# Node.js Basic Objects Test

Node.js/V8 对象内存分析测试案例，验证 Maze 对各种 JavaScript 对象类型的识别能力。

## 环境要求

| 项目 | 版本 |
|------|------|
| Node.js | **v18.20.8** |
| npm | 10.x |
| OS | Linux x64 |

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Object | 10,000 | 普通 JS 对象 |
| Array | 1,000 | 数组（每个10个元素）|
| Buffer | 1,000 | Node.js Buffer |
| Date | 1,000 | 日期对象 |
| RegExp | 1,000 | 正则表达式 |
| Error | 1,000 | 错误对象 |
| Promise | 1,000 | Promise 对象 |
| Set | 1,000 | Set 集合 |
| Map | 1,000 | Map 映射 |
| EventEmitter | 1,000 | 事件发射器 |
| Function | 1,000 | 函数对象 |
| ArrayBuffer | 1,000 | ArrayBuffer |
| Uint8Array | 1,000 | 类型化数组 |
| MyClass | 1,000 | 自定义类实例 |
| **总计** | **24,000** | |

## 文件说明

- `test.js` - 测试源代码
- `coredump-*.tar.gz` - 打包的 coredump 文件
- `validate.py` - 验证脚本
- `maze-result.json` - Maze 分析结果
- `maze_output.txt` - Maze 运行日志

## 使用方法

### 1. 运行测试程序

```bash
cd testdata/nodejs/20260201-basic-objects
node test.js
```

等待输出 `READY FOR GCORE`。

### 2. 捕获 coredump

```bash
# 另开终端
sudo gcore $(pgrep -f "node test.js")
```

### 3. 打包 coredump

```bash
python3 /path/to/maze/cmd/maze-tar-coredump.py core.<pid>
```

### 4. 运行 Maze 分析

```bash
cd /path/to/maze
./maze --tar testdata/nodejs/20260201-basic-objects/coredump-*.tar.gz --text --json-output
```

### 5. 验证结果

```bash
python3 validate.py maze-result.json
```

## 验证结果

待补充...

## 注意事项

1. Node.js 版本会影响 V8 内部对象布局
2. 建议使用与测试时相同的 Node.js 版本
3. coredump 可能较大（约 50-100 MB）

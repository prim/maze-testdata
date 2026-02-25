# 01-basic-types: 基础 JavaScript 类型测试

验证 Maze 对基础 JS 类型的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Object {id,name,value,nested} | 1,000 | 普通对象 |
| Object {x,y,z} | 1,000 | 嵌套对象 |
| Object {deep} | 1,000 | 深层嵌套 |
| Array (dense) | 1,000 | 密集数组 |
| Array (sparse) | 1,000 | 稀疏数组 |
| Array (mixed) | 1,000 | 混合类型数组 |
| String object | 1,000 | 字符串包装对象 |
| Number object | 1,000 | 数字包装对象 |
| Boolean object | 1,000 | 布尔包装对象 |
| Symbol holder | 1,000 | 持有 Symbol 的对象 |
| BigInt holder | 1,000 | 持有 BigInt 的对象 |
| Closure holder | 1,000 | 闭包捕获的对象 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-01-basic-types
```

# 04-function-types: 函数类型测试

验证 Maze 对各种 JavaScript 函数类型的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Function (namedFunc) | 1,000 | 普通命名函数，带 customProp |
| ArrowFunction | 1,100 | 箭头函数 |
| AsyncFunction (asyncFn) | 1,200 | 异步函数 |
| GeneratorFunction (genFn) | 1,300 | 生成器函数 |
| AsyncGeneratorFunction (asyncGenFn) | 1,400 | 异步生成器函数 |
| Function.dynamic | 1,500 | new Function() 动态创建 |
| BoundFunction (boundTarget) | 1,600 | fn.bind(obj) 绑定函数 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-04-function-types
```

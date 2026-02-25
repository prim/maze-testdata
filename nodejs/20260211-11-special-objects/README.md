# 11-special-objects: 特殊对象和边界情况测试

验证 Maze 对特殊对象和边界情况的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Object (null proto) | 1,000 | Object.create(null) |
| Object (frozen) | 1,000 | Object.freeze() |
| Object (sealed) | 1,000 | Object.seal() |
| Object (circular) | 1,000 | 循环引用 obj.self = obj |
| Object (deep nested) | 1,000 | 5 层嵌套子对象 |
| Object (many props) | 1,000 | 每个 50 个属性 |
| Arguments | 1,000 | arguments 对象 |
| Object (symbol keys) | 1,000 | 带 Symbol 键 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-11-special-objects
```

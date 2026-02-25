# 07-es6-plus: ES6+ 新特性对象测试

验证 Maze 对 ES6+ 新特性对象的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| WeakRef | 1,000 | 弱引用，target 为 {id, data} |
| FinalizationRegistry | 1,000 | 终结器注册表 |
| PrivateFieldsClass | 1,000 | 带私有字段 #privateField |
| DerivedClass | 1,000 | 继承自 BaseClass |
| Object (accessors) | 1,000 | 带 getter/setter |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-07-es6-plus
```

# 12-custom-classes: 自定义类测试

验证 Maze 对自定义类实例的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| SimpleClass | 1,000 | 简单类 {id, timestamp} |
| Dog | 1,000 | 多层继承 Animal→Mammal→Dog |
| FactoryObject | 1,000 | 工厂模式创建 {type, id, created} |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-12-custom-classes
```

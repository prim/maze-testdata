# 05-iterators: 迭代器和生成器对象测试

验证 Maze 对迭代器和生成器对象的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Generator (gen) | 1,000 | 生成器对象，已调用一次 next() |
| AsyncGenerator (asyncGen) | 1,000 | 异步生成器对象 |
| ArrayIterator | 1,000 | 数组迭代器 |
| MapIterator | 1,000 | Map entries 迭代器 |
| SetIterator | 1,000 | Set values 迭代器 |
| StringIterator | 1,000 | 字符串迭代器 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-05-iterators
```

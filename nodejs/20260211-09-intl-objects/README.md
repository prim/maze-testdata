# 09-intl-objects: 国际化对象 (Intl) 测试

验证 Maze 对国际化对象的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| Intl.DateTimeFormat | 1,000 | 5 种 locale 轮换 |
| Intl.NumberFormat | 1,000 | 货币格式 |
| Intl.Collator | 1,000 | 排序比较器 |
| Intl.PluralRules | 1,000 | 复数规则 |
| Intl.RelativeTimeFormat | 1,000 | 相对时间格式 |
| Intl.ListFormat | 1,000 | 列表格式 |
| Intl.Segmenter | 1,000 | 文本分段器 |

注意: Intl 对象是 C++ 后端实现，Maze 可能无法将其识别为独立的 V8 堆对象类型。

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-09-intl-objects
```

# C++ 1拆N Split Threshold Bug Test

**日期**: 2026-02-25
**测试目的**: 针对 ResultClassify 1拆N 阈值 n>5 (cpp.go:970) 设计触发场景。

## Bug 针对

**ResultClassify 1拆N 阈值 n>5** (cpp.go:970)
- malloc 块大小是类型大小的 2-5 倍时不会被拆分
- 导致整块内存只计为 1 个对象

## 测试数据

| 类型 | 数量 | malloc 大小 | 说明 |
|------|------|-------------|------|
| Widget (split2) | 3000 | sizeof(Widget)*2 | n=2, 不满足 n>5 |
| Widget (split3) | 3000 | sizeof(Widget)*3 | n=3, 不满足 n>5 |
| Widget (split5) | 2000 | sizeof(Widget)*5 | n=5, 不满足 n>5 |
| Widget (split8) | 1000 | sizeof(Widget)*8 | n=8, 满足 n>5 (对照组) |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o split_n_threshold_test ../split_n_threshold_test.cpp
./split_n_threshold_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

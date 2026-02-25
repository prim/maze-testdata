# C++ Vtable Types Test

**日期**: 2026-02-25
**测试目的**: 验证 Maze 能正确识别多种 C++ 类的 vtable，区分不同继承类型，并检测同类对象数组。

## 测试数据

| 类型 | 数量 | 说明 |
|------|------|------|
| Dog | 10000 + 200(数组) | 继承 Animal，有 vtable |
| Cat | 5000 | 继承 Animal，有 vtable |
| GoldFish | 3000 | 继承 Animal，有 vtable |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o vtable_types_test ../vtable_types_test.cpp
./vtable_types_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

# C++ Globals & Weak Classification Test

**日期**: 2026-02-25
**测试目的**: 验证 Maze 能正确收集全局/静态变量（CollectGlobal），以及对无 vtable 的 malloc 块进行弱分类。

## 测试数据

| 类型 | 数量 | 说明 |
|------|------|------|
| Config (全局) | 1 | 有 vtable，含 vector\<string\> |
| g_id_pool (全局) | 1 | vector\<int\>，10000 个元素 |
| g_registry (全局) | 1 | unordered_map\<int, Record*\>，5000 个 kv |
| Record | 5000 | 有 vtable |
| Point3D | 5000 | 无 vtable，纯 POD |
| Node 链表 | 1000 | 无 vtable，有 next 指针链 |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o globals_weak_test ../globals_weak_test.cpp
./globals_weak_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

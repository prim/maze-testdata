# C++ STL Containers Test

**日期**: 2026-02-25
**测试目的**: 验证 Maze 能正确展开 STL 容器（vector, deque, unordered_map, list），将容器内部分配的内存归属到拥有容器的 C++ 对象。

## 测试数据

| 类型 | 数量 | 容器 |
|------|------|------|
| Widget | 5000 | vector\<int*\>(10个) + string |
| Session | 2000 | unordered_map\<int,string\>(20个kv) |
| TaskQueue | 1000 | deque\<int*\>(15个) + list\<int*\>(10个) |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o containers_test ../containers_test.cpp
./containers_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

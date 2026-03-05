# C++ Deep Nested Containers Test

**日期**: 2026-02-25
**测试目的**: 验证多层嵌套容器（vector of vector-holding objects, map of vectors）的 DFS 展开正确性。

## Bug 针对

1. **DFS 递归深度压力**: Warehouse->Inventory->vector<Item\*> 形成 3+ 层 DFS
2. **混合容器交互**: OrderBook 同时含 std::list 和 std::map<int, vector<Item\*>>

## 测试数据

| 类型 | 数量 | 说明 |
|------|------|------|
| Item | ~47500 | 有 vtable，分布在多层容器中 |
| Inventory | 2000 | 含 vector\<Item\*\> |
| Warehouse | 100 | 含 vector\<Inventory\*\>（二层嵌套） |
| OrderBook | 500 | 含 list\<Item\*\> + map\<int, vector\<Item\*\>\> |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o deep_nested_test ../deep_nested_test.cpp
./deep_nested_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

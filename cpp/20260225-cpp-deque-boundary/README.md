# C++ Deque Boundary Bug Test

**日期**: 2026-02-25
**测试目的**: 针对 DequeClassifyInfo 边界检查失效 (custom.go:139/156) 设计触发场景。

## Bug 针对

**DequeClassifyInfo curNode 边界检查失效** (custom.go:139/156)
- curNode 在 line 139 自增后，line 156 的 `curNode == startNode` 和 `curNode == finishNode` 永远为 false
- 导致 deque 首尾 buffer 中已 pop 的无效元素也被遍历

## 测试数据

| 操作 | 数量 | 说明 |
|------|------|------|
| deque 数量 | 200 | 每个 deque 独立 |
| push_back | 100/deque | 总共 20000 个 Task |
| pop_front | 30/deque | 使首 buffer 有空洞 |
| alive in deque | 70/deque | 14000 个存活 Task |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o deque_boundary_test ../deque_boundary_test.cpp
./deque_boundary_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

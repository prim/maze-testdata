# C++ Long List & Pointer Array Test

**日期**: 2026-02-25
**测试目的**: 压测 ListClassifyInfo 的超长链表处理，以及 ArrayClassifyInfo 对指针数组的处理。

## Bug 针对

1. **ListClassifyInfo 循环上限不匹配**: 循环上限 1M (line 347)，但错误日志阈值 10M (line 360)，永远不触发
2. **ArrayClassifyInfo 指针数组 skip 被注释**: `return true, nil` 被注释掉 (base.go line 187)，指针数组不被跳过

## 测试数据

| 类型 | 数量 | 说明 |
|------|------|------|
| Task | 500000 | std::list 中的元素，有 vtable |
| EventDispatcher | 3000 | 含 Listener\*[8] 指针数组 |
| Listener | ~13500 | 通过指针数组持有 |
| Particle | 5000 | 含 Vec3[4] 结构体数组 |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o long_list_ptr_array_test ../long_list_ptr_array_test.cpp
./long_list_ptr_array_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

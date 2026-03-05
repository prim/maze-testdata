# C++ Edge Case Bug Test

**日期**: 2026-02-25
**测试目的**: 针对 cpp package 中发现的真实 bug 设计触发场景。

## Bug 针对

1. **checkStructLastMemberIsArrayOne off-by-one** (cpp.go:1051)
   - 循环条件 `cur < end` 应为 `cur <= end`
   - 柔性数组 `Slot[1]` 最后一个元素恰好填满时被漏掉

2. **ArrayClassifyInfo 指针数组遇 NULL 放弃** (base.go:203)
   - `IsPointer(newptr)` 对 NULL 返回 false，整个数组被放弃
   - Pipeline 含 `Handler*[4]`，后 2 个为 nullptr

## 测试数据

| 类型 | 数量 | 说明 |
|------|------|------|
| SlotTable | 2000 | 含 Slot[1] 柔性数组，精确分配 10 个 Slot |
| Pipeline | 3000 | Handler\*[4] 中 2 个有效 + 2 个 NULL |
| FullPipeline | 3000 | Handler\*[4] 全部填满（对照组） |
| Handler | 18000 | 6000(Pipeline) + 12000(FullPipeline) |

## 编译与运行

```bash
g++ -g -O0 -std=c++11 -o edge_case_test ../edge_case_test.cpp
./edge_case_test
# 等待 ">>> READY FOR GCORE <<<" 后执行 gcore
```

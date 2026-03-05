# TC-001: Stack Locals Basic Test

## 测试目的
验证 maze 能否正确收集函数栈帧中的局部变量，识别仅通过栈变量持有的非多态对象。

## 测试场景
创建以下非多态类（无虚函数），通过函数局部变量持有：
- `Point` (x, y): 3 个实例
- `DataBlock` (buffer[64], id): 2 个实例
- `SimpleNode` (value, next): 3 个实例（链表结构）

这些对象只能通过栈局部变量访问，没有全局引用，用于验证栈变量收集功能。

## 文件说明
- `stack_locals_basic_test.cpp`: 测试程序源码
- `stack_locals_basic_test`: 编译后的测试程序
- `coredump-*.tar.gz`: 打包的 coredump 文件
- `validate.py`: 验证脚本

## 运行测试

```bash
# 使用测试运行器
python3 testdata/run_test.py cpp/20260304-stack-locals-basic

# 手动验证
./maze --tar testdata/cpp/20260304-stack-locals-basic/coredump-*.tar.gz --text --json-output
python3 testdata/cpp/20260304-stack-locals-basic/validate.py maze-result.json
```

## 预期结果
- maze 能识别出 Point、DataBlock、SimpleNode 类型
- `.cpp.json` 中包含 `stack_locals` 字段，且有非空数据
- 各类型数量与测试程序创建的一致（±10%）

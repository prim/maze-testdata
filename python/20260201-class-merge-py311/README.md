# Class Merge 测试用例

## 测试目标

验证 `--py-merge` 选项能正确地将类实例中的 `refcnt=1` 属性合并到实例。

## 测试场景

```python
class A(object):
    def __init__(self):
        self.items = {"a": 1, "b": {i: i for i in range(256)}}

l0 = [A() for _ in range(10000)]
```

- 创建 10000 个类 A 实例
- 每个实例包含一个外层 dict `self.items`
- 外层 dict 的 `"b"` 键指向一个 256 条目的大字典 (refcnt=1)

## 预期结果

### 不启用 `--py-merge`

内层大字典单独统计：
- `<class A> instance`: 10000 个，avg_size ≈ 56 bytes
- `{long => long}<256`: 10000 个，avg_size ≈ 4696 bytes

### 启用 `--py-merge`

内层大字典合并到 A 实例：
- `<class A> instance`: 10000 个，avg_size ≈ 5000+ bytes (包含合并的内层字典)
- `{long => long}<256`: 不单独出现在 Top N (已合并)

## 生成 coredump

```bash
python class_merge_test.py &
gcore $!
```

## 运行测试

```bash
# 普通模式
./maze --tar <tarball> --text --limit 500

# 合并模式
./maze --tar <tarball> --text --limit 500 --py-merge
```

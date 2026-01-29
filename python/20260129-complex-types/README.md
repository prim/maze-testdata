# 20260129-complex-types

复杂类型测试用例 - 测试 Maze 对各种 Python 类型的内存分析能力。

## 测试目标

验证 Maze 能够正确识别和统计以下 Python 类型：

| 类型 | 数量 | 说明 |
|------|------|------|
| list | 2800 | 空列表、单元素、多元素、嵌套列表 |
| tuple | 2500 | 单元素、多元素、混合类型元组 |
| class 实例 | 2400 | SimpleClass, PersonClass, GameEntity, TreeNode |
| set/frozenset | 1200 | 小集合、中等集合、不可变集合 |
| bytes/bytearray | 1400 | 短字节串、中等、长字节串、可变字节数组 |
| dict | 2400 | 简单字典、嵌套字典、defaultdict、OrderedDict、Counter |
| str | 2000 | 短字符串、中等、长字符串、Unicode |
| numeric | 1300 | 大整数、浮点数、复数 |
| collections | 1000 | deque、namedtuple (Point, Rectangle) |

**总计**: 约 17,000 个测试对象

## 自定义类

测试程序定义了以下类：

```python
class SimpleClass:
    """简单的类 - 没有属性"""
    pass

class PersonClass:
    """带属性的类"""
    def __init__(self, name, age, email):
        self.name = name
        self.age = age
        self.email = email

class GameEntity:
    """游戏实体类 - 更复杂的属性"""
    def __init__(self, entity_id, x, y, hp, inventory):
        self.entity_id = entity_id
        self.x = x
        self.y = y
        self.hp = hp
        self.inventory = inventory  # 列表
        self.status = {"alive": True, "level": 1}

class TreeNode:
    """树节点 - 带有引用关系"""
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

Point = namedtuple('Point', ['x', 'y'])
Rectangle = namedtuple('Rectangle', ['x', 'y', 'width', 'height'])
```

## 使用方法

### 生成 coredump

```bash
# 1. 运行测试程序
python testdata/python/20260129-complex-types/complex_types.py

# 2. 在另一个终端生成 coredump
gcore <pid>

# 或使用 maze-tar-coredump.py 一键打包
python cmd/maze-tar-coredump.py <pid> complex-types
```

### 运行测试

```bash
# 使用 run_test.py
python testdata/run_test.py python/20260129-complex-types
```

## 验证规则

验证脚本 `validate.py` 检查：

1. **summary 结构** - 确保有 `items` 和 `summary` 字段
2. **pymempool_objects** - 应该 > 10000
3. **类型识别** - 验证 PersonClass、GameEntity、TreeNode、SimpleClass 等类型被识别
4. **字典类型** - 检查是否识别到字典类型
5. **items 结构** - 确保每个 item 有 order、amount、total_size 等字段
6. **总对象数** - 应该 > 15000

## 文件结构

```
20260129-complex-types/
├── README.md              # 本文档
├── complex_types.py       # 测试程序源码
├── validate.py            # 验证脚本
└── coredump-*.tar.gz      # 测试数据 (待生成)
```

## 相关文件

- `testdata/run_test.py` - 测试运行器
- `dev-log/2026-01-28-test-framework-plan.md` - 测试框架设计文档

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Python Memory Test Script

此脚本创建覆盖 Maze Python 内存分析模块所有主要功能的测试数据结构，
用于验证以下分类和分析功能：

1. 基础类型: int, float, str, unicode/bytes, bool, None
2. 容器类型: list, dict, tuple, set, frozenset
3. 可调用类型: function, lambda, method, classmethod, staticmethod
4. 类与实例: 自定义类实例, 带 __dict__ 的对象, 旧式类(Python 2)
5. 嵌套结构: 嵌套 dict, 嵌套 list, dict 中的 list
6. 引用计数场景: refcnt=1 的子对象 (用于 --py-merge 测试)
7. 特殊场景: 空容器, 大容器, 混合类型容器
8. 模块级变量和闭包: cell 对象

使用方法:
    python comprehensive_test.py

生成 core dump:
    gcore <pid>
    # 或
    kill -ABRT <pid>

测试验证:
    ./maze --tar path/to/coredump.tar.gz --text --json-output
    ./maze --tar path/to/coredump.tar.gz --text --json-output --py-merge
"""

from __future__ import print_function
import os
import sys
import time
import functools
import weakref

# Python 2/3 兼容性
PY2 = sys.version_info[0] == 2


# =============================================================================
# 1. 测试类定义
# =============================================================================

class SimpleClass(object):
    """简单类 - 只有几个基本属性"""
    def __init__(self, id_val):
        self.id = id_val
        self.name = "simple_" + str(id_val)
        self.value = id_val * 1.5


class NestedDictClass(object):
    """嵌套字典类 - 测试 __dict__ 处理和子对象合并"""
    def __init__(self, id_val):
        self.id = id_val
        # 嵌套字典，子对象 refcnt=1，用于 --py-merge 测试
        self.data = {
            "nested": {
                "level1": {
                    "level2": {
                        "value": id_val,
                        "items": [i for i in range(10)]
                    }
                }
            },
            "list_val": [x * 2 for x in range(20)],
            "str_val": "string_value_" + str(id_val),
        }


class NestedListClass(object):
    """嵌套列表类 - 测试 list 分类和子对象遍历"""
    def __init__(self, id_val):
        self.id = id_val
        self.items = [
            [i, i * 2, "item_" + str(i)] for i in range(15)
        ]
        self.matrix = [
            [j * i for j in range(5)] for i in range(5)
        ]


class MixedTypeContainerClass(object):
    """混合类型容器类 - 测试容器元素类型分类"""
    def __init__(self, id_val):
        self.id = id_val
        # 混合类型 list
        self.mixed_list = [
            1,                      # int
            2.5,                    # float
            "string",               # str
            None,                   # NoneType
            True,                   # bool
            [1, 2, 3],              # list
            {"a": 1},               # dict
            (1, 2),                 # tuple
        ]
        # 混合类型 dict (非字符串键)
        self.mixed_dict = {
            1: "int_key",
            "str": "str_key",
            (1, 2): "tuple_key",
        }
        # 字符串键 dict (SimpleMapType)
        self.simple_dict = {
            "name": "test",
            "value": 123,
            "active": True,
        }


class LargeContainerClass(object):
    """大容器类 - 测试大对象处理"""
    def __init__(self, id_val, size=1000):
        self.id = id_val
        # 大列表
        self.large_list = [i * 2 for i in range(size)]
        # 大字典
        self.large_dict = {i: "value_" + str(i) for i in range(size)}
        # 大集合
        self.large_set = set(range(size))


class EmptyContainerClass(object):
    """空容器类 - 测试空容器处理"""
    def __init__(self, id_val):
        self.id = id_val
        self.empty_list = []
        self.empty_dict = {}
        self.empty_tuple = ()
        self.empty_set = set()
        self.empty_frozenset = frozenset()


class MethodHolderClass(object):
    """方法持有类 - 测试 method/function 分类"""
    def __init__(self, id_val):
        self.id = id_val
        # lambda 函数
        self.lambda_func = lambda x: x * 2
        # 绑定方法引用
        self.bound_method = self.instance_method
        # functools.partial
        self.partial_func = functools.partial(self.instance_method_with_arg, arg=42)
    
    def instance_method(self):
        return self.id
    
    def instance_method_with_arg(self, arg=0):
        return self.id + arg
    
    @classmethod
    def class_method(cls):
        return "class_method"
    
    @staticmethod
    def static_method():
        return "static_method"


class ClosureHolderClass(object):
    """闭包持有类 - 测试 cell 对象"""
    def __init__(self, id_val):
        self.id = id_val
        captured_val = id_val * 10
        
        def closure_func():
            return captured_val + self.id
        
        self.closure = closure_func


class WeakRefHolderClass(object):
    """弱引用持有类 - 测试 weakref 处理"""
    def __init__(self, id_val, target):
        self.id = id_val
        self.weak_target = weakref.ref(target)


class InheritedClass(SimpleClass):
    """继承类 - 测试类继承情况下的内存分析"""
    def __init__(self, id_val):
        super(InheritedClass, self).__init__(id_val)
        self.extra_attr = "inherited_" + str(id_val)
        self.extra_data = {"parent_id": id_val, "child_id": id_val * 2}


class SlottedClass(object):
    """使用 __slots__ 的类 - 测试无 __dict__ 的对象"""
    __slots__ = ['id', 'name', 'value']
    
    def __init__(self, id_val):
        self.id = id_val
        self.name = "slotted_" + str(id_val)
        self.value = id_val * 3.14


class SetFrozenSetClass(object):
    """集合类 - 测试 set 和 frozenset 分类"""
    def __init__(self, id_val):
        self.id = id_val
        self.int_set = {i for i in range(20)}
        self.str_set = {"a", "b", "c", "d", "e"}
        self.mixed_set = {1, "two", 3.0, (4, 5)}
        self.frozen_int = frozenset(range(10))
        self.frozen_str = frozenset(["x", "y", "z"])


class TupleClass(object):
    """元组类 - 测试 tuple 分类"""
    def __init__(self, id_val):
        self.id = id_val
        self.int_tuple = tuple(range(10))
        self.str_tuple = ("a", "b", "c", "d")
        self.mixed_tuple = (1, "two", 3.0, None, True)
        self.nested_tuple = ((1, 2), (3, 4), (5, 6))


class BytesUnicodeClass(object):
    """字节和 Unicode 类 - 测试字符串类型分类"""
    def __init__(self, id_val):
        self.id = id_val
        self.ascii_str = "hello_world_" + str(id_val)
        self.unicode_str = u"你好世界_" + str(id_val)
        if not PY2:
            self.bytes_val = b"binary_data_" + str(id_val).encode()
        else:
            self.bytes_val = b"binary_data_" + str(id_val)
        self.long_str = "x" * 1000


class NumberClass(object):
    """数值类 - 测试 int/long/float 分类"""
    def __init__(self, id_val):
        self.id = id_val
        self.small_int = 42
        self.large_int = 10 ** 20
        self.negative_int = -12345
        self.float_val = 3.14159265358979
        self.small_float = 0.001
        self.large_float = 1e100


# Python 2 旧式类 (仅在 Python 2 中有效)
if PY2:
    class OldStyleClass:
        """Python 2 旧式类 - 测试 PyInstanceObject"""
        def __init__(self, id_val):
            self.id = id_val
            self.name = "old_style_" + str(id_val)


class DictSubclass(dict):
    """dict 子类 - 测试 IsPyDictSubType"""
    def __init__(self, id_val):
        super(DictSubclass, self).__init__()
        self["id"] = id_val
        self["data"] = list(range(10))
        self.custom_attr = "dict_subclass_" + str(id_val)


class ListSubclass(list):
    """list 子类"""
    def __init__(self, id_val):
        super(ListSubclass, self).__init__()
        self.extend(range(20))
        self.custom_attr = "list_subclass_" + str(id_val)


class DequeClass(object):
    """deque 类 - 测试 collections.deque"""
    def __init__(self, id_val):
        from collections import deque
        self.id = id_val
        self.deque_obj = deque([i for i in range(50)])
        self.maxlen_deque = deque(range(20), maxlen=10)


class OrderedDictClass(object):
    """OrderedDict 类 - 测试 collections.OrderedDict"""
    def __init__(self, id_val):
        from collections import OrderedDict
        self.id = id_val
        self.ordered = OrderedDict()
        for i in range(20):
            self.ordered["key_%d" % i] = "value_%d" % i


class DefaultDictClass(object):
    """defaultdict 类 - 测试 collections.defaultdict"""
    def __init__(self, id_val):
        from collections import defaultdict
        self.id = id_val
        self.int_default = defaultdict(int)
        self.list_default = defaultdict(list)
        for i in range(20):
            self.int_default["key_%d" % i] = i
            self.list_default["list_%d" % i].append(i)


class CounterClass(object):
    """Counter 类 - 测试 collections.Counter"""
    def __init__(self, id_val):
        from collections import Counter
        self.id = id_val
        self.counter = Counter("abracadabra" * 100 + str(id_val))


class NamedTupleClass(object):
    """namedtuple 类 - 测试 collections.namedtuple"""
    def __init__(self, id_val):
        from collections import namedtuple
        Point = namedtuple('Point', ['x', 'y', 'z'])
        self.id = id_val
        self.points = [Point(i, i*2, i*3) for i in range(20)]


class CircularRefClass(object):
    """循环引用类 - 测试 GC 循环引用"""
    def __init__(self, id_val):
        self.id = id_val
        self.ref = None
    
    def set_circular(self, other):
        self.ref = other


class DescriptorClass(object):
    """描述符类 - 测试描述符对象"""
    class MyDescriptor(object):
        def __get__(self, obj, objtype=None):
            return "descriptor_value"
        def __set__(self, obj, value):
            pass
    
    my_prop = MyDescriptor()
    
    def __init__(self, id_val):
        self.id = id_val


class PropertyClass(object):
    """property 类 - 测试 @property 装饰器"""
    def __init__(self, id_val):
        self._id = id_val
        self._value = id_val * 2
    
    @property
    def id(self):
        return self._id
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self._value = v


class GeneratorHolderClass(object):
    """生成器持有类 - 测试生成器对象"""
    def __init__(self, id_val):
        self.id = id_val
        # 创建生成器对象（不消费）
        self.gen = self._make_generator(id_val)
        self.gen_expr = (x * 2 for x in range(100))
    
    def _make_generator(self, n):
        for i in range(n):
            yield i * 2


class ComplexNumberClass(object):
    """复数类 - 测试 complex 类型"""
    def __init__(self, id_val):
        self.id = id_val
        self.complex_val = complex(id_val, id_val * 2)
        self.complex_list = [complex(i, i+1) for i in range(10)]


class RangeClass(object):
    """range 类 - 测试 range 对象"""
    def __init__(self, id_val):
        self.id = id_val
        if not PY2:
            self.range_obj = range(id_val * 1000)
            self.range_list = [range(i) for i in range(20)]


class HighRefCountClass(object):
    """高引用计数类 - 测试高 refcnt 场景"""
    # 类级别共享对象，refcnt 会很高
    SHARED_DICT = {"shared": True, "data": list(range(100))}
    SHARED_LIST = [1, 2, 3, 4, 5] * 20
    
    def __init__(self, id_val):
        self.id = id_val
        # 引用共享对象
        self.shared_dict_ref = HighRefCountClass.SHARED_DICT
        self.shared_list_ref = HighRefCountClass.SHARED_LIST


class MultiInheritClass(object):
    """多重继承类 - 测试复杂继承"""
    pass


class MixinA(object):
    def __init__(self):
        self.mixin_a_attr = "mixin_a"


class MixinB(object):
    def __init__(self):
        self.mixin_b_attr = "mixin_b"


class MultipleInheritance(MixinA, MixinB):
    """多重继承类"""
    def __init__(self, id_val):
        MixinA.__init__(self)
        MixinB.__init__(self)
        self.id = id_val


class ExceptionClass(object):
    """异常类 - 测试异常对象"""
    def __init__(self, id_val):
        self.id = id_val
        self.exception = Exception("test_exception_%d" % id_val)
        self.value_error = ValueError("value_error_%d" % id_val)
        try:
            raise RuntimeError("runtime_error")
        except RuntimeError as e:
            self.caught_exception = e


class MetaclassTestClass(object):
    """元类测试类"""
    pass


class MyMeta(type):
    """自定义元类"""
    def __new__(mcs, name, bases, namespace):
        namespace['meta_attr'] = 'from_metaclass'
        return super(MyMeta, mcs).__new__(mcs, name, bases, namespace)


# Python 2/3 兼容的元类定义
MetaclassInstance = MyMeta('MetaclassInstance', (object,), {
    '__init__': lambda self, id_val: setattr(self, 'id', id_val)
})


class FrameHolderClass(object):
    """栈帧持有类 - 测试 PyFrameObject"""
    def __init__(self, id_val, depth=10):
        self.id = id_val
        self.frame = None
        self._capture_frame(depth)
    
    def _capture_frame(self, depth):
        if depth > 0:
            self._capture_frame(depth - 1)
        else:
            # 捕获当前栈帧
            import sys
            self.frame = sys._getframe()


class CodeObjectClass(object):
    """代码对象类 - 测试 PyCodeObject"""
    def __init__(self, id_val):
        self.id = id_val
        # 获取函数的代码对象
        self.code_obj = self._sample_func.__code__ if hasattr(self._sample_func, '__code__') else self._sample_func.func_code
        self.lambda_code = (lambda x: x * 2).__code__ if hasattr(lambda: None, '__code__') else (lambda x: x * 2).func_code
    
    def _sample_func(self, a, b, c=10):
        """示例函数，用于获取代码对象"""
        return a + b + c


class BuiltinFunctionClass(object):
    """内置函数类 - 测试 PyCFunction (builtin_function_or_method)"""
    def __init__(self, id_val):
        self.id = id_val
        # 保存对内置函数的引用
        self.builtin_len = len
        self.builtin_print = print
        self.builtin_abs = abs
        self.builtin_max = max
        self.builtin_min = min
        self.list_append = [].append
        self.dict_get = {}.get
        self.str_upper = "".upper


class ModuleClass(object):
    """模块类 - 测试 PyModuleObject"""
    def __init__(self, id_val):
        import sys
        import os
        import collections
        self.id = id_val
        self.sys_module = sys
        self.os_module = os
        self.collections_module = collections


class MemberDescrClass(object):
    """MemberDescr 测试类 - 测试 PyMemberDescr_Type"""
    __slots__ = ['id', 'x', 'y', 'z']
    
    # __slots__ 会自动创建 member_descriptor 对象
    
    def __init__(self, id_val):
        self.id = id_val
        self.x = 1.0
        self.y = 2.0
        self.z = 3.0


class GetSetDescrClass(object):
    """GetSetDescr 测试类 - 测试 PyGetSetDescr_Type"""
    def __init__(self, id_val):
        self.id = id_val
        self._real = id_val
        self._imag = id_val * 2
        # complex 类型的 real/imag 是 getset_descriptor
        c = complex(1, 2)
        self.complex_real_descr = type(c).real
        self.complex_imag_descr = type(c).imag


class MethodDescrClass(object):
    """MethodDescr 测试类 - 测试 PyMethodDescr_Type"""
    def __init__(self, id_val):
        self.id = id_val
        # 获取内置类型的方法描述符
        self.list_append_descr = list.append
        self.dict_get_descr = dict.get
        self.str_upper_descr = str.upper
        self.set_add_descr = set.add


class WrapperDescrClass(object):
    """WrapperDescr 测试类 - 测试 PyWrapperDescr_Type"""
    def __init__(self, id_val):
        self.id = id_val
        # __init__, __new__, __repr__ 等是 wrapper_descriptor
        self.object_init = object.__init__
        self.object_new = object.__new__
        self.object_repr = object.__repr__
        self.list_getitem = list.__getitem__
        self.dict_setitem = dict.__setitem__


class ClassMethodDescrClass(object):
    """ClassMethodDescr 测试类"""
    def __init__(self, id_val):
        self.id = id_val
        # dict.fromkeys 是 classmethod_descriptor
        self.dict_fromkeys = dict.fromkeys
        # float.fromhex 也是
        if hasattr(float, 'fromhex'):
            self.float_fromhex = float.fromhex


class BoundMethodClass(object):
    """绑定方法类 - 测试各种方法绑定"""
    def __init__(self, id_val):
        self.id = id_val
        self.data = [1, 2, 3]
        # 绑定方法
        self.bound_instance = self.instance_method
        self.bound_data_append = self.data.append
    
    def instance_method(self):
        return self.id
    
    @classmethod
    def class_method(cls):
        return "class"
    
    @staticmethod
    def static_method():
        return "static"


class AsyncGenClass(object):
    """异步生成器类 (Python 3.6+)"""
    def __init__(self, id_val):
        self.id = id_val
        self.async_gen = None
        # 只在 Python 3.6+ 创建异步生成器
        if sys.version_info >= (3, 6):
            exec("""
async def async_generator(n):
    for i in range(n):
        yield i
self.async_gen = async_generator(10)
""", {'self': self})


class CoroutineClass(object):
    """协程类 (Python 3.5+)"""
    def __init__(self, id_val):
        self.id = id_val
        self.coro = None
        # 只在 Python 3.5+ 创建协程
        if sys.version_info >= (3, 5):
            exec("""
async def sample_coro():
    return 42
self.coro = sample_coro()
""", {'self': self})


# Python 3.7+ dataclass
DataClassInstance = None
if sys.version_info >= (3, 7):
    exec("""
from dataclasses import dataclass, field
from typing import List

@dataclass
class DataClassExample:
    id: int
    name: str = "default"
    items: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        self.items = list(range(10))

DataClassInstance = DataClassExample
""")


# Python 3.10+ match/case pattern objects
PatternMatchClass = None
if sys.version_info >= (3, 10):
    exec("""
class PatternMatchClass:
    def __init__(self, id_val):
        self.id = id_val
        self.results = []
        for val in [1, "hello", [1,2,3], {"a": 1}]:
            match val:
                case int():
                    self.results.append("int")
                case str():
                    self.results.append("str")
                case list():
                    self.results.append("list")
                case dict():
                    self.results.append("dict")
""")


class TypeHintClass(object):
    """类型提示类 - 测试 typing 模块对象"""
    def __init__(self, id_val):
        self.id = id_val
        try:
            from typing import List, Dict, Optional, Union, Callable, Any, Tuple
            self.list_int = List[int]
            self.dict_str_int = Dict[str, int]
            self.optional_str = Optional[str]
            self.union_type = Union[int, str, float]
            self.callable_type = Callable[[int, str], bool]
            self.any_type = Any
            self.tuple_type = Tuple[int, str, float]
        except ImportError:
            pass


class RecursiveStructClass(object):
    """递归结构类 - 测试深层递归对象"""
    def __init__(self, id_val, depth=50):
        self.id = id_val
        self.child = None
        if depth > 0:
            self.child = RecursiveStructClass(id_val, depth - 1)


class LargeStringClass(object):
    """大字符串类 - 测试大字符串内存"""
    def __init__(self, id_val, size=10000):
        self.id = id_val
        self.large_ascii = "A" * size
        self.large_unicode = u"中" * (size // 3)
        if not PY2:
            self.large_bytes = b"B" * size


class MemoryViewClass(object):
    """memoryview 类 - 测试 memoryview 对象"""
    def __init__(self, id_val):
        self.id = id_val
        if not PY2:
            self.data = bytearray(1000)
            self.view = memoryview(self.data)
            self.view_slice = self.view[100:200]


class ByteArrayClass(object):
    """bytearray 类 - 测试 bytearray 对象"""
    def __init__(self, id_val):
        self.id = id_val
        self.ba = bytearray(b"hello world " * 100)
        self.ba_large = bytearray(range(256)) * 10


# =============================================================================
# 2. 模块级变量和全局对象
# =============================================================================

# 模块级字典
MODULE_DICT = {
    "config_a": 100,
    "config_b": "value",
    "config_c": [1, 2, 3],
}

# 模块级列表
MODULE_LIST = [
    {"id": i, "name": "module_item_" + str(i)}
    for i in range(100)
]


# =============================================================================
# 3. 主函数
# =============================================================================

def create_test_objects(count=1000):
    """
    创建测试对象
    
    Args:
        count: 每种类型创建的对象数量
    
    Returns:
        dict: 包含所有测试对象的字典
    """
    objects = {}
    
    print("\n[1/12] Creating SimpleClass instances...")
    objects["simple"] = [SimpleClass(i) for i in range(count)]
    
    print("[2/12] Creating NestedDictClass instances...")
    objects["nested_dict"] = [NestedDictClass(i) for i in range(count)]
    
    print("[3/12] Creating NestedListClass instances...")
    objects["nested_list"] = [NestedListClass(i) for i in range(count)]
    
    print("[4/12] Creating MixedTypeContainerClass instances...")
    objects["mixed_type"] = [MixedTypeContainerClass(i) for i in range(count)]
    
    print("[5/12] Creating LargeContainerClass instances...")
    # 大容器对象创建较少以控制内存
    objects["large_container"] = [LargeContainerClass(i, size=500) for i in range(count // 10)]
    
    print("[6/12] Creating EmptyContainerClass instances...")
    objects["empty_container"] = [EmptyContainerClass(i) for i in range(count)]
    
    print("[7/12] Creating MethodHolderClass instances...")
    objects["method_holder"] = [MethodHolderClass(i) for i in range(count)]
    
    print("[8/12] Creating ClosureHolderClass instances...")
    objects["closure_holder"] = [ClosureHolderClass(i) for i in range(count)]
    
    print("[9/12] Creating InheritedClass instances...")
    objects["inherited"] = [InheritedClass(i) for i in range(count)]
    
    print("[10/12] Creating SlottedClass instances...")
    objects["slotted"] = [SlottedClass(i) for i in range(count)]
    
    print("[11/12] Creating collection classes (Set, Tuple, Bytes)...")
    objects["set_frozenset"] = [SetFrozenSetClass(i) for i in range(count)]
    objects["tuple"] = [TupleClass(i) for i in range(count)]
    objects["bytes_unicode"] = [BytesUnicodeClass(i) for i in range(count)]
    objects["number"] = [NumberClass(i) for i in range(count)]
    
    print("[12/12] Creating WeakRefHolderClass instances...")
    # 弱引用需要目标对象
    targets = [SimpleClass(i) for i in range(count)]
    objects["weakref_targets"] = targets
    objects["weakref_holder"] = [WeakRefHolderClass(i, targets[i]) for i in range(count)]
    
    # Python 2 旧式类
    if PY2:
        print("[Extra] Creating OldStyleClass instances (Python 2 only)...")
        objects["old_style"] = [OldStyleClass(i) for i in range(count)]
    
    # === 新增类型 ===
    print("\n[Extra] Creating additional test types...")
    
    print("  - DictSubclass (dict subtype)...")
    objects["dict_subclass"] = [DictSubclass(i) for i in range(count)]
    
    print("  - ListSubclass (list subtype)...")
    objects["list_subclass"] = [ListSubclass(i) for i in range(count)]
    
    print("  - DequeClass (collections.deque)...")
    objects["deque"] = [DequeClass(i) for i in range(count)]
    
    print("  - OrderedDictClass (collections.OrderedDict)...")
    objects["ordered_dict"] = [OrderedDictClass(i) for i in range(count)]
    
    print("  - DefaultDictClass (collections.defaultdict)...")
    objects["default_dict"] = [DefaultDictClass(i) for i in range(count)]
    
    print("  - CounterClass (collections.Counter)...")
    objects["counter"] = [CounterClass(i) for i in range(count)]
    
    print("  - NamedTupleClass (collections.namedtuple)...")
    objects["namedtuple"] = [NamedTupleClass(i) for i in range(count)]
    
    print("  - CircularRefClass (circular references)...")
    circular_objs = [CircularRefClass(i) for i in range(count)]
    # 创建循环引用
    for i in range(len(circular_objs) - 1):
        circular_objs[i].set_circular(circular_objs[i + 1])
    circular_objs[-1].set_circular(circular_objs[0])  # 闭环
    objects["circular_ref"] = circular_objs
    
    print("  - DescriptorClass (custom descriptors)...")
    objects["descriptor"] = [DescriptorClass(i) for i in range(count)]
    
    print("  - PropertyClass (@property decorator)...")
    objects["property"] = [PropertyClass(i) for i in range(count)]
    
    print("  - GeneratorHolderClass (generator objects)...")
    objects["generator"] = [GeneratorHolderClass(i) for i in range(count)]
    
    print("  - ComplexNumberClass (complex numbers)...")
    objects["complex_number"] = [ComplexNumberClass(i) for i in range(count)]
    
    print("  - RangeClass (range objects)...")
    if not PY2:
        objects["range"] = [RangeClass(i) for i in range(count)]
    
    print("  - HighRefCountClass (high refcnt objects)...")
    objects["high_refcount"] = [HighRefCountClass(i) for i in range(count)]
    
    print("  - MultipleInheritance (multiple inheritance)...")
    objects["multi_inherit"] = [MultipleInheritance(i) for i in range(count)]
    
    print("  - ExceptionClass (exception objects)...")
    objects["exception"] = [ExceptionClass(i) for i in range(count)]
    
    print("  - MetaclassInstance (metaclass)...")
    objects["metaclass"] = [MetaclassInstance(i) for i in range(count)]
    
    # === 高级类型 ===
    print("\n[Advanced] Creating advanced test types...")
    
    print("  - FrameHolderClass (frame objects)...")
    objects["frame"] = [FrameHolderClass(i, depth=5) for i in range(count // 10)]
    
    print("  - CodeObjectClass (code objects)...")
    objects["code_object"] = [CodeObjectClass(i) for i in range(count)]
    
    print("  - BuiltinFunctionClass (builtin functions)...")
    objects["builtin_func"] = [BuiltinFunctionClass(i) for i in range(count)]
    
    print("  - ModuleClass (module objects)...")
    objects["module"] = [ModuleClass(i) for i in range(count // 10)]
    
    print("  - MemberDescrClass (member descriptors)...")
    objects["member_descr"] = [MemberDescrClass(i) for i in range(count)]
    
    print("  - GetSetDescrClass (getset descriptors)...")
    objects["getset_descr"] = [GetSetDescrClass(i) for i in range(count)]
    
    print("  - MethodDescrClass (method descriptors)...")
    objects["method_descr"] = [MethodDescrClass(i) for i in range(count)]
    
    print("  - WrapperDescrClass (wrapper descriptors)...")
    objects["wrapper_descr"] = [WrapperDescrClass(i) for i in range(count)]
    
    print("  - ClassMethodDescrClass (classmethod descriptors)...")
    objects["classmethod_descr"] = [ClassMethodDescrClass(i) for i in range(count)]
    
    print("  - BoundMethodClass (bound methods)...")
    objects["bound_method"] = [BoundMethodClass(i) for i in range(count)]
    
    print("  - TypeHintClass (typing module objects)...")
    objects["type_hint"] = [TypeHintClass(i) for i in range(count // 10)]
    
    print("  - RecursiveStructClass (deep recursive structures)...")
    objects["recursive"] = [RecursiveStructClass(i, depth=20) for i in range(count // 10)]
    
    print("  - LargeStringClass (large strings)...")
    objects["large_string"] = [LargeStringClass(i, size=5000) for i in range(count // 10)]
    
    print("  - ByteArrayClass (bytearray objects)...")
    objects["bytearray"] = [ByteArrayClass(i) for i in range(count)]
    
    if not PY2:
        print("  - MemoryViewClass (memoryview objects)...")
        objects["memoryview"] = [MemoryViewClass(i) for i in range(count // 10)]
    
    # Python 3.5+ 协程
    if sys.version_info >= (3, 5):
        print("  - CoroutineClass (coroutine objects, Python 3.5+)...")
        objects["coroutine"] = [CoroutineClass(i) for i in range(count // 10)]
    
    # Python 3.6+ 异步生成器
    if sys.version_info >= (3, 6):
        print("  - AsyncGenClass (async generator objects, Python 3.6+)...")
        objects["async_gen"] = [AsyncGenClass(i) for i in range(count // 10)]
    
    # Python 3.7+ dataclass
    if sys.version_info >= (3, 7) and DataClassInstance is not None:
        print("  - DataClassExample (dataclass, Python 3.7+)...")
        objects["dataclass"] = [DataClassInstance(i) for i in range(count)]
    
    # Python 3.10+ pattern matching
    if sys.version_info >= (3, 10) and PatternMatchClass is not None:
        print("  - PatternMatchClass (pattern matching, Python 3.10+)...")
        objects["pattern_match"] = [PatternMatchClass(i) for i in range(count // 10)]
    
    return objects


def print_summary(objects):
    """打印对象摘要"""
    print("\n" + "=" * 60)
    print("Object Summary")
    print("=" * 60)
    
    total = 0
    for name, obj_list in sorted(objects.items()):
        count = len(obj_list)
        total += count
        print("  {:<25} : {:>6} objects".format(name, count))
    
    print("-" * 60)
    print("  {:<25} : {:>6} objects".format("TOTAL", total))
    print("=" * 60)


def main():
    pid = os.getpid()
    python_version = sys.version.split()[0]
    
    print("=" * 60)
    print("Comprehensive Python Memory Test")
    print("=" * 60)
    print("PID:            %d" % pid)
    print("Python Version: %s" % python_version)
    print("Python 2/3:     %s" % ("Python 2" if PY2 else "Python 3"))
    print("=" * 60)
    
    # 创建测试对象
    print("\nCreating test objects...")
    objects = create_test_objects(count=1000)
    
    # 打印摘要
    print_summary(objects)
    
    # 计算预期验证指标
    print("\n" + "=" * 60)
    print("Expected Validation Metrics")
    print("=" * 60)
    print("  SimpleClass instances:        1000 (avg_size ~96 normal, ~300+ merge)")
    print("  NestedDictClass instances:    1000 (avg_size ~96 normal, ~2000+ merge)")
    print("  NestedListClass instances:    1000 (avg_size ~96 normal, ~1500+ merge)")
    print("  MethodHolderClass instances:  1000 (should have lambda/method types)")
    print("  SlottedClass instances:       1000 (no __dict__)")
    if PY2:
        print("  OldStyleClass instances:      1000 (PyInstanceObject)")
    print("=" * 60)
    
    # 就绪信号
    print("\n" + "=" * 60)
    print(">>> READY FOR GCORE <<<")
    print("gcore %d" % pid)
    print("=" * 60)
    
    print("\nTo analyze this process:")
    print("  1. gcore %d" % pid)
    print("  2. cd cmd && python3 maze-tar-coredump.py ../coredump.%d" % pid)
    print("  3. ./maze --tar coredump-*.tar.gz --text --json-output")
    print("  4. ./maze --tar coredump-*.tar.gz --text --json-output --py-merge")
    
    print("\nWaiting for coredump generation... (Ctrl+C to exit)")
    
    # 保持进程运行
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

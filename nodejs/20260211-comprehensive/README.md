# Node.js Comprehensive Objects Test

综合测试用例，覆盖尽可能多的 JavaScript/Node.js 对象类型。

## 测试目标

1. 验证 Maze 能识别各种 V8 InstanceType
2. 测试 Node.js 核心模块产生的对象
3. 覆盖 ES6+ 新特性对象
4. 包含边界情况和特殊对象

## 对象类型覆盖

### 1. 基础 JavaScript 类型 (~12,000 对象)
- Object (普通对象、嵌套对象)
- Array (密集、稀疏、混合、空数组)
- String/Number/Boolean (包装对象)
- Symbol, BigInt

### 2. 集合类型 (~3,000 对象)
- Map, Set
- WeakMap, WeakSet

### 3. 二进制数据类型 (~4,200 对象)
- Buffer
- ArrayBuffer, SharedArrayBuffer
- TypedArray (Int8, Uint8, Int16, Uint16, Int32, Uint32, Float32, Float64, BigInt64, BigUint64)
- DataView

### 4. 函数类型 (~3,700 对象)
- 普通函数、箭头函数
- AsyncFunction, GeneratorFunction, AsyncGeneratorFunction
- 动态创建函数 (new Function)
- 绑定函数 (bind)

### 5. 迭代器和生成器 (~3,100 对象)
- Generator, AsyncGenerator
- ArrayIterator, MapIterator, SetIterator, StringIterator

### 6. 内置对象 (~5,200 对象)
- Date, RegExp
- Error (Error, TypeError, RangeError, ReferenceError, SyntaxError, URIError, EvalError, AggregateError)
- Promise (pending, resolved, rejected)
- Proxy

### 7. ES6+ 特性 (~2,500 对象)
- WeakRef, FinalizationRegistry
- 带私有字段的类
- 带静态字段的类
- 继承类
- 带 getter/setter 的对象

### 8. Node.js 核心模块 (~3,500 对象)
- EventEmitter
- Stream (Readable, Writable, Duplex, Transform, PassThrough)
- URL, URLSearchParams
- crypto (Hash, Hmac)
- zlib (Gzip, Gunzip, Deflate, Inflate)
- vm (Script, Context)
- MessageChannel, MessagePort

### 9. 国际化对象 (~2,000 对象)
- Intl.DateTimeFormat
- Intl.NumberFormat
- Intl.Collator
- Intl.PluralRules
- Intl.RelativeTimeFormat
- Intl.ListFormat
- Intl.Segmenter (如果支持)

### 10. Web API 兼容对象 (~2,500 对象)
- TextEncoder, TextDecoder
- AbortController, AbortSignal
- Blob (如果支持)
- Headers, Request, Response (如果支持)
- FormData (如果支持)
- ReadableStream, WritableStream, TransformStream (如果支持)
- CompressionStream, DecompressionStream (如果支持)

### 11. 特殊对象 (~1,700 对象)
- null 原型对象 (Object.create(null))
- 冻结对象 (Object.freeze)
- 密封对象 (Object.seal)
- 不可扩展对象 (Object.preventExtensions)
- 循环引用对象
- 深度嵌套对象
- 大量属性对象
- arguments 对象
- Symbol 键对象
- 危险 getter 对象

### 12. 自定义类层次结构 (~2,450 对象)
- 简单类
- 多层继承 (Animal -> Mammal -> Dog)
- Mixin 模式
- 工厂模式
- 单例模式

## 运行方式

### 1. 启动测试进程

```bash
cd testdata/nodejs/20260211-comprehensive
node --expose-gc test.js
```

等待输出 "READY FOR GCORE"。

### 2. 捕获 Core Dump

```bash
sudo gcore <PID>
```

### 3. 打包

```bash
tar -czf coredump-$(date +%Y%m%d).tar.gz core.<PID> /usr/bin/node
```

### 4. 分析

```bash
./maze --tar testdata/nodejs/20260211-comprehensive/coredump-*.tar.gz --text --json-output
```

### 5. 验证

```bash
python3 testdata/nodejs/20260211-comprehensive/validate.py maze-result.json
```

## 预期结果

- 对象总数：50,000+
- 类型数：10+
- 内存占用：50-150 MB

## Node.js 版本要求

- Node.js 18.x 或 20.x
- 推荐使用 Node.js 20.x 以支持更多 Web API

## 文件结构

```
20260211-comprehensive/
├── README.md       # 本文件
├── test.js         # 测试脚本
└── validate.py     # 验证脚本
```

## 与 basic-objects 测试的区别

| 特性 | basic-objects | comprehensive |
|------|---------------|---------------|
| 对象数量 | ~24,000 | ~50,000+ |
| 类型覆盖 | 14 种 | 100+ 种 |
| ES6+ 特性 | 基础 | 完整 |
| Node.js 模块 | EventEmitter | Stream, crypto, zlib, vm, etc. |
| Web APIs | 无 | TextEncoder, Blob, Fetch API, etc. |
| 边界情况 | 无 | 循环引用, 深度嵌套, null 原型, etc. |
| 国际化 | 无 | Intl.* 完整覆盖 |

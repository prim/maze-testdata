/**
 * Node.js 综合内存分析测试用例
 * 
 * 测试目标：
 *   1. 验证 Maze 能识别尽可能多的 Node.js/V8 对象类型
 *   2. 覆盖 V8 内部各种 InstanceType
 *   3. 测试 Node.js 核心模块产生的对象
 * 
 * 测试数据：
 *   - 每种对象类型统一生成 1000 个
 *   - 便于对比分析和验证
 * 
 * 运行方式：
 *   node --expose-gc test.js
 *   # 等待 "READY FOR GCORE" 输出后捕获 coredump
 *   sudo gcore <PID>
 * 
 * Node.js 版本要求：v18.x+ (推荐 v20.x)
 */

'use strict';

const v8 = require('v8');
const path = require('path');
const events = require('events');
const stream = require('stream');
const crypto = require('crypto');
const zlib = require('zlib');
const url = require('url');
const vm = require('vm');
const { MessageChannel } = require('worker_threads');
const { Buffer } = require('buffer');

// 全局存储，防止 GC 回收
const globalStore = new Map();
let counter = 0;

// 统计信息
const stats = {};

// 统一的对象数量
const N = 1000;

function addStat(category, count = 1) {
    stats[category] = (stats[category] || 0) + count;
}

function store(obj, category) {
    globalStore.set(++counter, obj);
    addStat(category);
    return obj;
}

// ============================================================
// 1. 基础 JavaScript 类型
// ============================================================
function generateBasicTypes() {
    console.log('生成基础类型...');
    
    // 1.1 普通对象
    for (let i = 0; i < N; i++) {
        store({
            id: i,
            name: `object_${i}`,
            value: Math.random(),
            nested: { x: i, y: i * 2, z: { deep: true } }
        }, 'Object');
    }
    
    // 1.2 数组 - 密集数组
    for (let i = 0; i < N; i++) {
        store(Array.from({ length: 10 }, (_, idx) => idx + i), 'Array.dense');
    }
    
    // 1.3 数组 - 稀疏数组
    for (let i = 0; i < N; i++) {
        const sparse = [];
        sparse[0] = i;
        sparse[100] = i * 2;
        store(sparse, 'Array.sparse');
    }
    
    // 1.4 数组 - 混合类型
    for (let i = 0; i < N; i++) {
        store([i, `str_${i}`, { x: i }, [1, 2, 3], null, undefined], 'Array.mixed');
    }
    
    // 1.5 字符串对象
    for (let i = 0; i < N; i++) {
        // eslint-disable-next-line no-new-wrappers
        store(new String(`string_object_${i}_${'x'.repeat(i % 100)}`), 'String.object');
    }
    
    // 1.6 数字对象
    for (let i = 0; i < N; i++) {
        // eslint-disable-next-line no-new-wrappers
        store(new Number(i * Math.PI), 'Number.object');
    }
    
    // 1.7 布尔对象
    for (let i = 0; i < N; i++) {
        // eslint-disable-next-line no-new-wrappers
        store(new Boolean(i % 2 === 0), 'Boolean.object');
    }
    
    // 1.8 Symbol
    for (let i = 0; i < N; i++) {
        store({ sym: Symbol(`symbol_${i}`) }, 'Symbol');
    }
    
    // 1.9 BigInt
    for (let i = 0; i < N; i++) {
        store({ big: BigInt(i) * BigInt(Number.MAX_SAFE_INTEGER) }, 'BigInt');
    }
}

// ============================================================
// 2. 集合类型
// ============================================================
function generateCollections() {
    console.log('生成集合类型...');
    
    // 2.1 Map
    for (let i = 0; i < N; i++) {
        const map = new Map();
        for (let j = 0; j < 5; j++) {
            map.set(`key_${j}`, { value: i * j });
        }
        store(map, 'Map');
    }
    
    // 2.2 Set
    for (let i = 0; i < N; i++) {
        const set = new Set();
        for (let j = 0; j < 5; j++) {
            set.add(`item_${i}_${j}`);
        }
        store(set, 'Set');
    }
    
    // 2.3 WeakMap
    const weakMapKeys = [];
    for (let i = 0; i < N; i++) {
        const wm = new WeakMap();
        const key = { id: i };
        weakMapKeys.push(key);
        wm.set(key, `value_${i}`);
        store(wm, 'WeakMap');
    }
    store(weakMapKeys, 'WeakMap.keys');
    
    // 2.4 WeakSet
    const weakSetItems = [];
    for (let i = 0; i < N; i++) {
        const ws = new WeakSet();
        const item = { id: i };
        weakSetItems.push(item);
        ws.add(item);
        store(ws, 'WeakSet');
    }
    store(weakSetItems, 'WeakSet.items');
}

// ============================================================
// 3. 二进制数据类型
// ============================================================
function generateBinaryTypes() {
    console.log('生成二进制类型...');
    
    // 3.1 Buffer
    for (let i = 0; i < N; i++) {
        store(Buffer.alloc(64 + (i % 64), i % 256), 'Buffer');
    }
    
    // 3.2 ArrayBuffer
    for (let i = 0; i < N; i++) {
        store(new ArrayBuffer(128), 'ArrayBuffer');
    }
    
    // 3.3 SharedArrayBuffer
    try {
        for (let i = 0; i < N; i++) {
            store(new SharedArrayBuffer(64), 'SharedArrayBuffer');
        }
    } catch (e) {
        console.log('  SharedArrayBuffer 不可用');
    }
    
    // 3.4 各种 TypedArray
    const typedArrayTypes = [
        Int8Array, Uint8Array, Uint8ClampedArray,
        Int16Array, Uint16Array,
        Int32Array, Uint32Array,
        Float32Array, Float64Array,
        BigInt64Array, BigUint64Array
    ];
    
    for (const TypedArrayClass of typedArrayTypes) {
        for (let i = 0; i < N; i++) {
            const arr = new TypedArrayClass(16);
            if (TypedArrayClass.name.includes('Big')) {
                arr.fill(BigInt(i));
            } else {
                arr.fill(i % 128);
            }
            store(arr, TypedArrayClass.name);
        }
    }
    
    // 3.5 DataView
    for (let i = 0; i < N; i++) {
        const buffer = new ArrayBuffer(32);
        const view = new DataView(buffer);
        view.setInt32(0, i);
        store(view, 'DataView');
    }
}

// ============================================================
// 4. 函数类型
// ============================================================
function generateFunctionTypes() {
    console.log('生成函数类型...');
    
    // 4.1 普通函数
    for (let i = 0; i < N; i++) {
        const fn = function namedFunc() { return i; };
        fn.customProp = i;
        store(fn, 'Function');
    }
    
    // 4.2 箭头函数
    for (let i = 0; i < N; i++) {
        store(() => i * 2, 'ArrowFunction');
    }
    
    // 4.3 异步函数
    for (let i = 0; i < N; i++) {
        store(async function asyncFn() { return i; }, 'AsyncFunction');
    }
    
    // 4.4 生成器函数
    for (let i = 0; i < N; i++) {
        store(function* genFn() { yield i; yield i + 1; }, 'GeneratorFunction');
    }
    
    // 4.5 异步生成器函数
    for (let i = 0; i < N; i++) {
        store(async function* asyncGenFn() { yield i; }, 'AsyncGeneratorFunction');
    }
    
    // 4.6 动态创建的函数
    for (let i = 0; i < N; i++) {
        store(new Function('x', `return x + ${i}`), 'Function.dynamic');
    }
    
    // 4.7 绑定函数
    for (let i = 0; i < N; i++) {
        const obj = { value: i };
        const fn = function() { return this.value; };
        store(fn.bind(obj), 'BoundFunction');
    }
}

// ============================================================
// 5. 迭代器和生成器对象
// ============================================================
function generateIterators() {
    console.log('生成迭代器...');
    
    // 5.1 Generator 对象
    for (let i = 0; i < N; i++) {
        function* gen() {
            yield i;
            yield i + 1;
            yield i + 2;
        }
        const g = gen();
        g.next();
        store(g, 'Generator');
    }
    
    // 5.2 AsyncGenerator 对象
    for (let i = 0; i < N; i++) {
        async function* asyncGen() {
            yield i;
            yield i + 1;
        }
        store(asyncGen(), 'AsyncGenerator');
    }
    
    // 5.3 Array Iterator
    for (let i = 0; i < N; i++) {
        const arr = [1, 2, 3, 4, 5];
        store(arr[Symbol.iterator](), 'ArrayIterator');
    }
    
    // 5.4 Map Iterator
    for (let i = 0; i < N; i++) {
        const map = new Map([[1, 'a'], [2, 'b']]);
        store(map.entries(), 'MapIterator');
    }
    
    // 5.5 Set Iterator
    for (let i = 0; i < N; i++) {
        const set = new Set([1, 2, 3]);
        store(set.values(), 'SetIterator');
    }
    
    // 5.6 String Iterator
    for (let i = 0; i < N; i++) {
        store('hello'[Symbol.iterator](), 'StringIterator');
    }
}

// ============================================================
// 6. 内置对象类型
// ============================================================
function generateBuiltinObjects() {
    console.log('生成内置对象...');
    
    // 6.1 Date
    for (let i = 0; i < N; i++) {
        store(new Date(Date.now() + i * 86400000), 'Date');
    }
    
    // 6.2 RegExp
    for (let i = 0; i < N; i++) {
        store(new RegExp(`pattern_${i}_(\\w+)`, 'gim'), 'RegExp');
    }
    
    // 6.3 Error
    for (let i = 0; i < N; i++) {
        const err = new Error(`Error message ${i}`);
        err.code = `ERR_${i}`;
        store(err, 'Error');
    }
    
    // 6.4 TypeError
    for (let i = 0; i < N; i++) {
        store(new TypeError(`TypeError message ${i}`), 'TypeError');
    }
    
    // 6.5 RangeError
    for (let i = 0; i < N; i++) {
        store(new RangeError(`RangeError message ${i}`), 'RangeError');
    }
    
    // 6.6 Promise - pending
    for (let i = 0; i < N; i++) {
        store(new Promise(() => {}), 'Promise.pending');
    }
    
    // 6.7 Promise - resolved
    for (let i = 0; i < N; i++) {
        store(Promise.resolve(i), 'Promise.resolved');
    }
    
    // 6.8 Promise - rejected
    for (let i = 0; i < N; i++) {
        const rejected = Promise.reject(new Error(`reject_${i}`));
        rejected.catch(() => {});
        store(rejected, 'Promise.rejected');
    }
    
    // 6.9 Proxy
    for (let i = 0; i < N; i++) {
        const target = { value: i };
        const handler = {
            get(t, prop) { return t[prop]; },
            set(t, prop, val) { t[prop] = val; return true; }
        };
        store(new Proxy(target, handler), 'Proxy');
    }
}

// ============================================================
// 7. ES6+ 新特性对象
// ============================================================
function generateES6PlusFeatures() {
    console.log('生成 ES6+ 特性对象...');
    
    // 7.1 WeakRef
    const weakRefTargets = [];
    for (let i = 0; i < N; i++) {
        const target = { id: i, data: `data_${i}` };
        weakRefTargets.push(target);
        store(new WeakRef(target), 'WeakRef');
    }
    store(weakRefTargets, 'WeakRef.targets');
    
    // 7.2 FinalizationRegistry
    for (let i = 0; i < N; i++) {
        const registry = new FinalizationRegistry((heldValue) => {});
        const obj = { id: i };
        registry.register(obj, `cleanup_${i}`);
        store({ registry, obj }, 'FinalizationRegistry');
    }
    
    // 7.3 带私有字段的类
    class PrivateFieldsClass {
        #privateField;
        constructor(value) {
            this.#privateField = value;
            this.publicField = value * 2;
        }
    }
    for (let i = 0; i < N; i++) {
        store(new PrivateFieldsClass(i), 'Class.privateFields');
    }
    
    // 7.4 继承类
    class BaseClass {
        constructor(x) { this.x = x; }
    }
    class DerivedClass extends BaseClass {
        constructor(x, y) {
            super(x);
            this.y = y;
        }
    }
    for (let i = 0; i < N; i++) {
        store(new DerivedClass(i, i * 2), 'Class.derived');
    }
    
    // 7.5 带 getter/setter 的对象
    for (let i = 0; i < N; i++) {
        const obj = {
            _value: i,
            get value() { return this._value; },
            set value(v) { this._value = v; }
        };
        store(obj, 'Object.accessors');
    }
}

// ============================================================
// 8. Node.js 核心模块对象
// ============================================================
function generateNodeCoreObjects() {
    console.log('生成 Node.js 核心模块对象...');
    
    // 8.1 EventEmitter
    for (let i = 0; i < N; i++) {
        const emitter = new events.EventEmitter();
        emitter.on('event1', () => {});
        emitter.on('event2', () => {});
        store(emitter, 'EventEmitter');
    }
    
    // 8.2 Stream.Readable
    for (let i = 0; i < N; i++) {
        store(new stream.Readable({
            read() { this.push(null); }
        }), 'Stream.Readable');
    }
    
    // 8.3 Stream.Writable
    for (let i = 0; i < N; i++) {
        store(new stream.Writable({
            write(chunk, enc, cb) { cb(); }
        }), 'Stream.Writable');
    }
    
    // 8.4 Stream.Transform
    for (let i = 0; i < N; i++) {
        store(new stream.Transform({
            transform(chunk, enc, cb) { cb(null, chunk); }
        }), 'Stream.Transform');
    }
    
    // 8.5 URL
    for (let i = 0; i < N; i++) {
        store(new URL(`https://example.com/path/${i}?query=${i}`), 'URL');
    }
    
    // 8.6 URLSearchParams
    for (let i = 0; i < N; i++) {
        const params = new URLSearchParams();
        params.append('key1', `value_${i}`);
        store(params, 'URLSearchParams');
    }
    
    // 8.7 crypto.Hash
    for (let i = 0; i < N; i++) {
        const hash = crypto.createHash('sha256');
        hash.update(`data_${i}`);
        store(hash, 'crypto.Hash');
    }
    
    // 8.8 zlib.Gzip
    for (let i = 0; i < N; i++) {
        store(zlib.createGzip(), 'zlib.Gzip');
    }
    
    // 8.9 vm.Script
    for (let i = 0; i < N; i++) {
        store(new vm.Script(`x + ${i}`), 'vm.Script');
    }
    
    // 8.10 MessageChannel
    for (let i = 0; i < N; i++) {
        const channel = new MessageChannel();
        store({ channel, port1: channel.port1, port2: channel.port2 }, 'MessageChannel');
    }
}

// ============================================================
// 9. 国际化对象 (Intl)
// ============================================================
function generateIntlObjects() {
    console.log('生成国际化对象...');
    
    const locales = ['en-US', 'zh-CN', 'ja-JP', 'de-DE', 'fr-FR'];
    const perLocale = N / locales.length;
    
    // 9.1 Intl.DateTimeFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.DateTimeFormat(locales[i % locales.length], {
            dateStyle: 'full',
            timeStyle: 'long'
        }), 'Intl.DateTimeFormat');
    }
    
    // 9.2 Intl.NumberFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.NumberFormat(locales[i % locales.length], {
            style: 'currency',
            currency: 'USD'
        }), 'Intl.NumberFormat');
    }
    
    // 9.3 Intl.Collator
    for (let i = 0; i < N; i++) {
        store(new Intl.Collator(locales[i % locales.length]), 'Intl.Collator');
    }
    
    // 9.4 Intl.PluralRules
    for (let i = 0; i < N; i++) {
        store(new Intl.PluralRules(locales[i % locales.length]), 'Intl.PluralRules');
    }
    
    // 9.5 Intl.RelativeTimeFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.RelativeTimeFormat(locales[i % locales.length]), 'Intl.RelativeTimeFormat');
    }
    
    // 9.6 Intl.ListFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.ListFormat(locales[i % locales.length]), 'Intl.ListFormat');
    }
    
    // 9.7 Intl.Segmenter
    if (typeof Intl.Segmenter !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Intl.Segmenter(locales[i % locales.length]), 'Intl.Segmenter');
        }
    }
}

// ============================================================
// 10. Web API 兼容对象
// ============================================================
function generateWebAPIObjects() {
    console.log('生成 Web API 兼容对象...');
    
    // 10.1 TextEncoder
    for (let i = 0; i < N; i++) {
        store(new TextEncoder(), 'TextEncoder');
    }
    
    // 10.2 TextDecoder
    for (let i = 0; i < N; i++) {
        store(new TextDecoder('utf-8'), 'TextDecoder');
    }
    
    // 10.3 AbortController
    for (let i = 0; i < N; i++) {
        const controller = new AbortController();
        store({ controller, signal: controller.signal }, 'AbortController');
    }
    
    // 10.4 Blob
    if (typeof Blob !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Blob([`content_${i}`], { type: 'text/plain' }), 'Blob');
        }
    }
    
    // 10.5 Headers
    if (typeof Headers !== 'undefined') {
        for (let i = 0; i < N; i++) {
            const headers = new Headers();
            headers.set('Content-Type', 'application/json');
            store(headers, 'Headers');
        }
    }
    
    // 10.6 Response
    if (typeof Response !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Response(`body_${i}`), 'Response');
        }
    }
    
    // 10.7 Request
    if (typeof Request !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Request(`https://example.com/${i}`), 'Request');
        }
    }
    
    // 10.8 FormData
    if (typeof FormData !== 'undefined') {
        for (let i = 0; i < N; i++) {
            const fd = new FormData();
            fd.append('field1', `value_${i}`);
            store(fd, 'FormData');
        }
    }
    
    // 10.9 ReadableStream
    if (typeof ReadableStream !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new ReadableStream({
                start(controller) { controller.close(); }
            }), 'ReadableStream');
        }
    }
    
    // 10.10 WritableStream
    if (typeof WritableStream !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new WritableStream({
                write(chunk) {}
            }), 'WritableStream');
        }
    }
}

// ============================================================
// 11. 特殊对象和边界情况
// ============================================================
function generateSpecialObjects() {
    console.log('生成特殊对象...');
    
    // 11.1 null 原型对象
    for (let i = 0; i < N; i++) {
        const obj = Object.create(null);
        obj.id = i;
        obj.name = `null_proto_${i}`;
        store(obj, 'Object.nullProto');
    }
    
    // 11.2 冻结对象
    for (let i = 0; i < N; i++) {
        store(Object.freeze({ id: i, frozen: true }), 'Object.frozen');
    }
    
    // 11.3 密封对象
    for (let i = 0; i < N; i++) {
        store(Object.seal({ id: i, sealed: true }), 'Object.sealed');
    }
    
    // 11.4 循环引用对象
    for (let i = 0; i < N; i++) {
        const obj = { id: i };
        obj.self = obj;
        store(obj, 'Object.circular');
    }
    
    // 11.5 深度嵌套对象
    for (let i = 0; i < N; i++) {
        let obj = { depth: 0, id: i };
        let current = obj;
        for (let d = 1; d <= 5; d++) {
            current.child = { depth: d, id: i };
            current = current.child;
        }
        store(obj, 'Object.deepNested');
    }
    
    // 11.6 大量属性的对象
    for (let i = 0; i < N; i++) {
        const obj = {};
        for (let p = 0; p < 50; p++) {
            obj[`prop_${p}`] = p + i;
        }
        store(obj, 'Object.manyProps');
    }
    
    // 11.7 arguments 对象
    for (let i = 0; i < N; i++) {
        (function() {
            store(arguments, 'Arguments');
        })(i, i + 1, i + 2);
    }
    
    // 11.8 带 Symbol 键的对象
    for (let i = 0; i < N; i++) {
        const sym = Symbol(`key_${i}`);
        store({ [sym]: `value_${i}`, normalKey: i }, 'Object.symbolKeys');
    }
}

// ============================================================
// 12. 自定义类
// ============================================================
function generateCustomClasses() {
    console.log('生成自定义类...');
    
    // 12.1 简单类
    class SimpleClass {
        constructor(id) {
            this.id = id;
            this.timestamp = Date.now();
        }
    }
    for (let i = 0; i < N; i++) {
        store(new SimpleClass(i), 'SimpleClass');
    }
    
    // 12.2 多层继承
    class Animal {
        constructor(name) { this.name = name; }
    }
    class Mammal extends Animal {
        constructor(name, legs) {
            super(name);
            this.legs = legs;
        }
    }
    class Dog extends Mammal {
        constructor(name, breed) {
            super(name, 4);
            this.breed = breed;
        }
    }
    for (let i = 0; i < N; i++) {
        store(new Dog(`dog_${i}`, `breed_${i % 10}`), 'Dog');
    }
    
    // 12.3 工厂模式
    function createEntity(type, id) {
        return { type, id, created: Date.now() };
    }
    for (let i = 0; i < N; i++) {
        store(createEntity(`type_${i % 5}`, i), 'FactoryObject');
    }
}

// ============================================================
// 主函数
// ============================================================
function main() {
    console.log('========================================');
    console.log('Node.js 综合内存分析测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`V8 版本: ${process.versions.v8}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`平台: ${process.platform} ${process.arch}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    // 生成各类对象
    generateBasicTypes();
    generateCollections();
    generateBinaryTypes();
    generateFunctionTypes();
    generateIterators();
    generateBuiltinObjects();
    generateES6PlusFeatures();
    generateNodeCoreObjects();
    generateIntlObjects();
    generateWebAPIObjects();
    generateSpecialObjects();
    generateCustomClasses();
    
    // 强制 GC
    if (global.gc) {
        console.log('\n执行 GC...');
        global.gc();
    }
    
    // 统计输出
    console.log('\n========================================');
    console.log('对象统计');
    console.log('========================================');
    
    const sortedStats = Object.entries(stats).sort((a, b) => b[1] - a[1]);
    let total = 0;
    let typeCount = 0;
    for (const [category, count] of sortedStats) {
        console.log(`  ${category.padEnd(30)} : ${count}`);
        total += count;
        typeCount++;
    }
    console.log('----------------------------------------');
    console.log(`  ${'类型数'.padEnd(28)} : ${typeCount}`);
    console.log(`  ${'对象总数'.padEnd(28)} : ${total}`);
    console.log(`  ${'globalStore.size'.padEnd(28)} : ${globalStore.size}`);
    
    // 内存使用
    const mem = process.memoryUsage();
    console.log('\n========================================');
    console.log('内存使用');
    console.log('========================================');
    console.log(`  heapUsed  : ${(mem.heapUsed / 1024 / 1024).toFixed(2)} MB`);
    console.log(`  heapTotal : ${(mem.heapTotal / 1024 / 1024).toFixed(2)} MB`);
    console.log(`  rss       : ${(mem.rss / 1024 / 1024).toFixed(2)} MB`);
    console.log(`  external  : ${(mem.external / 1024 / 1024).toFixed(2)} MB`);
    
    // 生成 heap snapshot
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const snapshotFile = `heap-snapshot-${timestamp}.heapsnapshot`;
    console.log(`\n正在生成 heap snapshot: ${snapshotFile}`);
    v8.writeHeapSnapshot(snapshotFile);
    console.log(`Heap snapshot 已保存到: ${path.resolve(snapshotFile)}`);
    
    // Ready 信号
    console.log('\n========================================');
    console.log('READY FOR GCORE');
    console.log(`使用命令: sudo gcore ${process.pid}`);
    console.log('========================================\n');
    
    // 保持进程运行
    setInterval(() => {}, 30000);
    
    // 优雅退出
    process.on('SIGINT', () => {
        console.log('\n正在退出...');
        console.log(`最终 globalStore 大小: ${globalStore.size}`);
        process.exit(0);
    });
}

// 启动
main();

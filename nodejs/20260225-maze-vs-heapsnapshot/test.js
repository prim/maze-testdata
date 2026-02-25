/**
 * Maze vs chrome-heapsnapshot-parser 对比测试
 *
 * 综合测试用例，从 12 个独立测试中挑选代表性类型，每种 500 个。
 * 在输出 "READY FOR GCORE" 之前先生成 .heapsnapshot，
 * 确保 heapsnapshot 和 coredump 捕获的是近似同一时刻的堆状态。
 *
 * 覆盖类型：
 *   - 基础: Object, Array(dense/sparse), String/Number/Boolean 包装
 *   - 集合: Map, Set, WeakMap, WeakSet
 *   - TypedArray: Uint8Array, Int32Array, Float64Array
 *   - 内置: Date, RegExp, Error, TypeError, Promise
 *   - 函数: Function, ArrowFunction, AsyncFunction
 *   - 自定义类: SimpleClass, Dog (多层继承)
 *   - Node.js: EventEmitter, Buffer, URL
 */

'use strict';

const v8 = require('v8');
const path = require('path');
const events = require('events');
const { Buffer } = require('buffer');

const globalStore = new Map();
let counter = 0;
const stats = {};
const N = 500;

function addStat(category, count = 1) {
    stats[category] = (stats[category] || 0) + count;
}

function store(obj, category) {
    globalStore.set(++counter, obj);
    addStat(category);
    return obj;
}

// ============================================================
// 基础类型
// ============================================================
function generateBasicTypes() {
    console.log('生成基础类型...');

    // Object
    for (let i = 0; i < N; i++) {
        store({
            id: i,
            name: `object_${i}`,
            value: Math.random(),
            nested: { x: i, y: i * 2 }
        }, 'Object');
    }

    // Array - dense
    for (let i = 0; i < N; i++) {
        store(Array.from({ length: 10 }, (_, idx) => idx + i), 'Array.dense');
    }

    // Array - sparse
    for (let i = 0; i < N; i++) {
        const sparse = [];
        sparse[0] = i;
        sparse[100] = i * 2;
        store(sparse, 'Array.sparse');
    }

    // String object
    for (let i = 0; i < N; i++) {
        // eslint-disable-next-line no-new-wrappers
        store(new String(`string_object_${i}_${'x'.repeat(i % 50)}`), 'String.object');
    }

    // Number object
    for (let i = 0; i < N; i++) {
        // eslint-disable-next-line no-new-wrappers
        store(new Number(i * Math.PI), 'Number.object');
    }

    // Boolean object
    for (let i = 0; i < N; i++) {
        // eslint-disable-next-line no-new-wrappers
        store(new Boolean(i % 2 === 0), 'Boolean.object');
    }
}

// ============================================================
// 集合类型
// ============================================================
function generateCollections() {
    console.log('生成集合类型...');

    // Map
    for (let i = 0; i < N; i++) {
        const map = new Map();
        for (let j = 0; j < 5; j++) {
            map.set(`key_${j}`, { value: i * j });
        }
        store(map, 'Map');
    }

    // Set
    for (let i = 0; i < N; i++) {
        const set = new Set();
        for (let j = 0; j < 5; j++) {
            set.add(`item_${i}_${j}`);
        }
        store(set, 'Set');
    }

    // WeakMap
    const weakMapKeys = [];
    for (let i = 0; i < N; i++) {
        const wm = new WeakMap();
        const key = { id: i };
        weakMapKeys.push(key);
        wm.set(key, `value_${i}`);
        store(wm, 'WeakMap');
    }
    store(weakMapKeys, 'WeakMap.keys');

    // WeakSet
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
// TypedArray (代表性的 3 种)
// ============================================================
function generateTypedArrays() {
    console.log('生成 TypedArray...');

    // Uint8Array
    for (let i = 0; i < N; i++) {
        const arr = new Uint8Array(32);
        arr.fill(i % 256);
        store(arr, 'Uint8Array');
    }

    // Int32Array
    for (let i = 0; i < N; i++) {
        const arr = new Int32Array(16);
        arr.fill(i);
        store(arr, 'Int32Array');
    }

    // Float64Array
    for (let i = 0; i < N; i++) {
        const arr = new Float64Array(8);
        arr.fill(i * Math.PI);
        store(arr, 'Float64Array');
    }
}

// ============================================================
// 内置对象
// ============================================================
function generateBuiltinObjects() {
    console.log('生成内置对象...');

    // Date
    for (let i = 0; i < N; i++) {
        store(new Date(Date.now() + i * 86400000), 'Date');
    }

    // RegExp
    for (let i = 0; i < N; i++) {
        store(new RegExp(`pattern_${i}_(\\w+)`, 'gi'), 'RegExp');
    }

    // Error
    for (let i = 0; i < N; i++) {
        const err = new Error(`Error message ${i}`);
        err.code = `ERR_${i}`;
        store(err, 'Error');
    }

    // TypeError
    for (let i = 0; i < N; i++) {
        store(new TypeError(`TypeError message ${i}`), 'TypeError');
    }

    // Promise - pending
    for (let i = 0; i < N; i++) {
        store(new Promise(() => {}), 'Promise.pending');
    }

    // Promise - resolved
    for (let i = 0; i < N; i++) {
        store(Promise.resolve(i), 'Promise.resolved');
    }
}

// ============================================================
// 函数类型
// ============================================================
function generateFunctions() {
    console.log('生成函数类型...');

    // Function
    for (let i = 0; i < N; i++) {
        const fn = function namedFunc() { return i; };
        fn.customProp = i;
        store(fn, 'Function');
    }

    // ArrowFunction
    for (let i = 0; i < N; i++) {
        store(() => i * 2, 'ArrowFunction');
    }

    // AsyncFunction
    for (let i = 0; i < N; i++) {
        store(async function asyncFn() { return i; }, 'AsyncFunction');
    }
}

// ============================================================
// 自定义类
// ============================================================
class SimpleClass {
    constructor(id) {
        this.id = id;
        this.timestamp = Date.now();
    }
}

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

function generateCustomClasses() {
    console.log('生成自定义类...');

    // SimpleClass
    for (let i = 0; i < N; i++) {
        store(new SimpleClass(i), 'SimpleClass');
    }

    // Dog (多层继承: Animal -> Mammal -> Dog)
    for (let i = 0; i < N; i++) {
        store(new Dog(`dog_${i}`, `breed_${i % 10}`), 'Dog');
    }
}

// ============================================================
// Node.js 核心对象
// ============================================================
function generateNodeCore() {
    console.log('生成 Node.js 核心对象...');

    // EventEmitter
    for (let i = 0; i < N; i++) {
        const emitter = new events.EventEmitter();
        emitter.on('event1', () => {});
        emitter.on('event2', () => {});
        store(emitter, 'EventEmitter');
    }

    // Buffer
    for (let i = 0; i < N; i++) {
        store(Buffer.alloc(64 + (i % 64), i % 256), 'Buffer');
    }

    // URL
    for (let i = 0; i < N; i++) {
        store(new URL(`https://example.com/path/${i}?query=${i}`), 'URL');
    }
}

// ============================================================
// Main
// ============================================================
function main() {
    console.log('========================================');
    console.log('Maze vs Heapsnapshot 对比测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');

    generateBasicTypes();
    generateCollections();
    generateTypedArrays();
    generateBuiltinObjects();
    generateFunctions();
    generateCustomClasses();
    generateNodeCore();

    if (global.gc) {
        console.log('\n执行 GC...');
        global.gc();
    }

    // 打印统计
    console.log('\n========================================');
    console.log('对象统计');
    console.log('========================================');

    let total = 0;
    for (const [category, count] of Object.entries(stats).sort((a, b) => b[1] - a[1])) {
        console.log(`  ${category.padEnd(20)} : ${count}`);
        total += count;
    }
    console.log('----------------------------------------');
    console.log(`  ${'对象总数'.padEnd(18)} : ${total}`);

    // 先生成 heapsnapshot，再等待 gcore
    console.log('\n========================================');
    console.log('生成 HeapSnapshot...');
    const snapshotFile = v8.writeHeapSnapshot();
    console.log(`HeapSnapshot 已保存: ${snapshotFile}`);
    console.log('========================================');

    console.log('\n========================================');
    console.log('READY FOR GCORE');
    console.log(`使用命令: sudo gcore ${process.pid}`);
    console.log('========================================\n');

    setInterval(() => {}, 30000);
    process.on('SIGINT', () => process.exit(0));
}

main();

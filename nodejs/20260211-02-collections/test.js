/**
 * 集合类型测试
 * 
 * 测试对象：Map, Set, WeakMap, WeakSet, Array, TypedArray, ArrayBuffer, DataView
 */

'use strict';

const globalStore = new Map();
let counter = 0;
const stats = {};
const N = 1000;

function addStat(category, count = 1) {
    stats[category] = (stats[category] || 0) + count;
}

function store(obj, category) {
    globalStore.set(++counter, obj);
    addStat(category);
    return obj;
}

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
    
    // 2.5 Array - 密集数组
    for (let i = 0; i < N; i++) {
        const arr = [i, i+1, i+2, i+3, i+4];
        store(arr, 'Array.dense');
    }
    
    // 2.6 Array - 稀疏数组
    for (let i = 0; i < N; i++) {
        const arr = [];
        arr[0] = i;
        arr[100] = i * 2;
        arr[500] = i * 3;
        store(arr, 'Array.sparse');
    }
    
    // 2.7 Array - 对象数组
    for (let i = 0; i < N; i++) {
        const arr = Array.from({ length: 10 }, (_, j) => ({ idx: j, val: i * j }));
        store(arr, 'Array.objects');
    }
    
    // 2.8 ArrayBuffer
    for (let i = 0; i < N; i++) {
        const ab = new ArrayBuffer(64 + (i % 64));
        store(ab, 'ArrayBuffer');
    }
    
    // 2.9 DataView
    for (let i = 0; i < N; i++) {
        const ab = new ArrayBuffer(32);
        const dv = new DataView(ab);
        dv.setInt32(0, i);
        store(dv, 'DataView');
    }
    
    // 2.10 TypedArray - 各种类型 (数量不同以便验证类型识别正确)
    const typedArrayConfigs = [
        [Int8Array, 100],
        [Uint8Array, 200],
        [Uint8ClampedArray, 300],
        [Int16Array, 400],
        [Uint16Array, 100],
        [Int32Array, 200],
        [Uint32Array, 300],
        [Float32Array, 400],
        [Float64Array, 100],
        [BigInt64Array, 200],
        [BigUint64Array, 300]
    ];
    
    for (const [Ctor, count] of typedArrayConfigs) {
        for (let i = 0; i < count; i++) {
            const isBigInt = Ctor.name.startsWith('Big');
            const arr = isBigInt 
                ? new Ctor([BigInt(i), BigInt(i+1), BigInt(i+2)])
                : new Ctor([i, i+1, i+2, i+3, i+4]);
            store(arr, Ctor.name);
        }
    }
}

function main() {
    console.log('========================================');
    console.log('集合类型测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateCollections();
    
    if (global.gc) {
        console.log('\n执行 GC...');
        global.gc();
    }
    
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
    
    console.log('\n========================================');
    console.log('READY FOR GCORE');
    console.log(`使用命令: sudo gcore ${process.pid}`);
    console.log('========================================\n');
    
    setInterval(() => {}, 30000);
    process.on('SIGINT', () => process.exit(0));
}

main();

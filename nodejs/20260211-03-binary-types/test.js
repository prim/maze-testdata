/**
 * 二进制数据类型测试
 * 
 * 测试对象：Buffer, ArrayBuffer, SharedArrayBuffer, TypedArray, DataView
 */

'use strict';

const { Buffer } = require('buffer');

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

function main() {
    console.log('========================================');
    console.log('二进制数据类型测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateBinaryTypes();
    
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

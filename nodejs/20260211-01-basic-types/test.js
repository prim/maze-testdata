/**
 * 基础 JavaScript 类型测试
 * 
 * 测试对象：Object, Array, String, Number, Boolean, Symbol, BigInt
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

    // 1.10 闭包持有的对象
    // 引用链: NativeContext → Context(test.js) → Context(createHolder闭包) → Object
    for (let i = 0; i < N; i++) {
        const obj = { closureId: i, data: `closure_${i}`, payload: new Array(10).fill(i) };
        const holder = createHolder(obj);
        store(holder, 'Closure.holder');
    }
}

function createHolder(captured) {
    // captured 被闭包捕获，存活在 createHolder 的 Context 里
    return { get() { return captured; } };
}

function main() {
    console.log('========================================');
    console.log('基础 JavaScript 类型测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateBasicTypes();
    
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

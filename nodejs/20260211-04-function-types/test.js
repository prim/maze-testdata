/**
 * 函数类型测试
 * 
 * 测试对象：Function, ArrowFunction, AsyncFunction, GeneratorFunction, BoundFunction
 */

'use strict';

const globalStore = new Map();
const objectsByCategory = {};
let counter = 0;
const stats = {};
const N = 1000;

function addStat(category, count = 1) {
    stats[category] = (stats[category] || 0) + count;
}

function store(obj, category) {
    globalStore.set(++counter, obj);
    addStat(category);
    if (!objectsByCategory[category]) {
        objectsByCategory[category] = [];
    }
    objectsByCategory[category].push(obj);
    return obj;
}

function generateFunctionTypes() {
    console.log('生成函数类型...');
    
    // 4.1 普通函数 - 1000
    for (let i = 0; i < 1000; i++) {
        const fn = function namedFunc() { return i; };
        fn.customProp = i;
        store(fn, 'Function');
    }
    
    // 4.2 箭头函数 - 1100
    for (let i = 0; i < 1100; i++) {
        store(() => i * 2, 'ArrowFunction');
    }
    
    // 4.3 异步函数 - 1200
    for (let i = 0; i < 1200; i++) {
        store(async function asyncFn() { return i; }, 'AsyncFunction');
    }
    
    // 4.4 生成器函数 - 1300
    for (let i = 0; i < 1300; i++) {
        store(function* genFn() { yield i; yield i + 1; }, 'GeneratorFunction');
    }
    
    // 4.5 异步生成器函数 - 1400
    for (let i = 0; i < 1400; i++) {
        store(async function* asyncGenFn() { yield i; }, 'AsyncGeneratorFunction');
    }
    
    // 4.6 动态创建的函数 (anonymous) - 1500
    for (let i = 0; i < 1500; i++) {
        store(new Function('x', `return x + ${i}`), 'Function.dynamic');
    }
    
    // 4.7 绑定函数 - 1600
    for (let i = 0; i < 1600; i++) {
        const obj = { value: i };
        const fn = function boundTarget() { return this.value; };
        store(fn.bind(obj), 'BoundFunction');
    }
}

function main() {
    console.log('========================================');
    console.log('函数类型测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateFunctionTypes();
    
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

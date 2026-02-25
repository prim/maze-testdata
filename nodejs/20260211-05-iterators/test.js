/**
 * 迭代器和生成器对象测试
 * 
 * 测试对象：Generator, AsyncGenerator, ArrayIterator, MapIterator, SetIterator, StringIterator
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

function main() {
    console.log('========================================');
    console.log('迭代器和生成器对象测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateIterators();
    
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

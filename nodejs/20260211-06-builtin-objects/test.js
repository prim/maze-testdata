/**
 * 内置对象类型测试
 * 
 * 测试对象：Date, RegExp, Error, Promise, Proxy
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

function main() {
    console.log('========================================');
    console.log('内置对象类型测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateBuiltinObjects();
    
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

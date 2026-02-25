/**
 * 特殊对象和边界情况测试
 * 
 * 测试对象：null原型, 冻结对象, 密封对象, 循环引用, 深度嵌套, arguments, Symbol键
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

function main() {
    console.log('========================================');
    console.log('特殊对象和边界情况测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateSpecialObjects();
    
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

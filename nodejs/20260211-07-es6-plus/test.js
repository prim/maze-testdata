/**
 * ES6+ 新特性对象测试
 * 
 * 测试对象：WeakRef, FinalizationRegistry, 私有字段类, 继承类, getter/setter
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

function main() {
    console.log('========================================');
    console.log('ES6+ 新特性对象测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateES6PlusFeatures();
    
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

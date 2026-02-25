/**
 * 自定义类测试
 * 
 * 测试对象：SimpleClass, 多层继承 (Animal->Mammal->Dog), 工厂模式
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

function main() {
    console.log('========================================');
    console.log('自定义类测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateCustomClasses();
    
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

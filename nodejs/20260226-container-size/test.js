/**
 * 容器不同大小的 size 准确性测试
 *
 * 创建不同 entry 数量的 Map 和 Set，验证 Maze 报告的 size 是否准确。
 * 同时生成 heapsnapshot 作为 ground truth。
 *
 * sizes: [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
 * 每种大小创建 N=100 个实例
 * entry 用数字 key/value (Smi)，避免创建额外堆对象
 */

'use strict';

const v8 = require('v8');

const N = 200;
const sizes = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];

const globalStore = new Map();
let counter = 0;
const stats = {};

function addStat(category, count) {
    stats[category] = (stats[category] || 0) + (count || 1);
}

function store(obj, category) {
    globalStore.set(++counter, obj);
    addStat(category);
    return obj;
}

// ============================================================
// Map: 不同大小
// ============================================================
function generateMaps() {
    console.log('生成不同大小的 Map...');
    for (const size of sizes) {
        for (let i = 0; i < N; i++) {
            const map = new Map();
            for (let j = 0; j < size; j++) {
                map.set(j, j);  // Smi key/value，不创建额外堆对象
            }
            store(map, `Map(${size})`);
        }
    }
}

// ============================================================
// Set: 不同大小
// ============================================================
function generateSets() {
    console.log('生成不同大小的 Set...');
    for (const size of sizes) {
        for (let i = 0; i < N; i++) {
            const set = new Set();
            for (let j = 0; j < size; j++) {
                set.add(i * 10000 + j);  // 唯一 Smi 值
            }
            store(set, `Set(${size})`);
        }
    }
}

// ============================================================
// Main
// ============================================================
function main() {
    console.log('========================================');
    console.log('容器不同大小 size 准确性测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种大小实例数: ${N}`);
    console.log(`测试大小: ${sizes.join(', ')}`);
    console.log('========================================\n');

    generateMaps();
    generateSets();

    if (global.gc) {
        console.log('\n执行 GC...');
        global.gc();
    }

    // 打印统计
    console.log('\n========================================');
    console.log('对象统计');
    console.log('========================================');
    let total = 0;
    for (const [cat, cnt] of Object.entries(stats).sort()) {
        console.log(`  ${cat.padEnd(20)} : ${cnt}`);
        total += cnt;
    }
    console.log('----------------------------------------');
    console.log(`  ${'总计'.padEnd(18)} : ${total}`);

    // 生成 heapsnapshot
    console.log('\n生成 HeapSnapshot...');
    const snapshotFile = v8.writeHeapSnapshot();
    console.log(`HeapSnapshot 已保存: ${snapshotFile}`);

    console.log('\n========================================');
    console.log('READY FOR GCORE');
    console.log(`使用命令: sudo gcore ${process.pid}`);
    console.log('========================================\n');

    setInterval(() => {}, 30000);
    process.on('SIGINT', () => process.exit(0));
}

main();

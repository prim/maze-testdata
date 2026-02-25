/**
 * 国际化对象 (Intl) 测试
 * 
 * 测试对象：Intl.DateTimeFormat, NumberFormat, Collator, PluralRules, etc.
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

function generateIntlObjects() {
    console.log('生成国际化对象...');
    
    const locales = ['en-US', 'zh-CN', 'ja-JP', 'de-DE', 'fr-FR'];
    
    // 9.1 Intl.DateTimeFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.DateTimeFormat(locales[i % locales.length], {
            dateStyle: 'full',
            timeStyle: 'long'
        }), 'Intl.DateTimeFormat');
    }
    
    // 9.2 Intl.NumberFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.NumberFormat(locales[i % locales.length], {
            style: 'currency',
            currency: 'USD'
        }), 'Intl.NumberFormat');
    }
    
    // 9.3 Intl.Collator
    for (let i = 0; i < N; i++) {
        store(new Intl.Collator(locales[i % locales.length]), 'Intl.Collator');
    }
    
    // 9.4 Intl.PluralRules
    for (let i = 0; i < N; i++) {
        store(new Intl.PluralRules(locales[i % locales.length]), 'Intl.PluralRules');
    }
    
    // 9.5 Intl.RelativeTimeFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.RelativeTimeFormat(locales[i % locales.length]), 'Intl.RelativeTimeFormat');
    }
    
    // 9.6 Intl.ListFormat
    for (let i = 0; i < N; i++) {
        store(new Intl.ListFormat(locales[i % locales.length]), 'Intl.ListFormat');
    }
    
    // 9.7 Intl.Segmenter
    if (typeof Intl.Segmenter !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Intl.Segmenter(locales[i % locales.length]), 'Intl.Segmenter');
        }
    }
}

function main() {
    console.log('========================================');
    console.log('国际化对象 (Intl) 测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateIntlObjects();
    
    if (global.gc) {
        console.log('\n执行 GC...');
        global.gc();
    }
    
    console.log('\n========================================');
    console.log('对象统计');
    console.log('========================================');
    
    let total = 0;
    for (const [category, count] of Object.entries(stats).sort((a, b) => b[1] - a[1])) {
        console.log(`  ${category.padEnd(25)} : ${count}`);
        total += count;
    }
    console.log('----------------------------------------');
    console.log(`  ${'对象总数'.padEnd(23)} : ${total}`);
    
    console.log('\n========================================');
    console.log('READY FOR GCORE');
    console.log(`使用命令: sudo gcore ${process.pid}`);
    console.log('========================================\n');
    
    setInterval(() => {}, 30000);
    process.on('SIGINT', () => process.exit(0));
}

main();

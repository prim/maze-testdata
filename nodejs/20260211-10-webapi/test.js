/**
 * Web API 兼容对象测试
 * 
 * 测试对象：TextEncoder, TextDecoder, AbortController, Blob, Headers, Response, etc.
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

function generateWebAPIObjects() {
    console.log('生成 Web API 兼容对象...');
    
    // 10.1 TextEncoder
    for (let i = 0; i < N; i++) {
        store(new TextEncoder(), 'TextEncoder');
    }
    
    // 10.2 TextDecoder
    for (let i = 0; i < N; i++) {
        store(new TextDecoder('utf-8'), 'TextDecoder');
    }
    
    // 10.3 AbortController
    for (let i = 0; i < N; i++) {
        const controller = new AbortController();
        store({ controller, signal: controller.signal }, 'AbortController');
    }
    
    // 10.4 Blob
    if (typeof Blob !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Blob([`content_${i}`], { type: 'text/plain' }), 'Blob');
        }
    }
    
    // 10.5 Headers
    if (typeof Headers !== 'undefined') {
        for (let i = 0; i < N; i++) {
            const headers = new Headers();
            headers.set('Content-Type', 'application/json');
            store(headers, 'Headers');
        }
    }
    
    // 10.6 Response
    if (typeof Response !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Response(`body_${i}`), 'Response');
        }
    }
    
    // 10.7 Request
    if (typeof Request !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new Request(`https://example.com/${i}`), 'Request');
        }
    }
    
    // 10.8 FormData
    if (typeof FormData !== 'undefined') {
        for (let i = 0; i < N; i++) {
            const fd = new FormData();
            fd.append('field1', `value_${i}`);
            store(fd, 'FormData');
        }
    }
    
    // 10.9 ReadableStream
    if (typeof ReadableStream !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new ReadableStream({
                start(controller) { controller.close(); }
            }), 'ReadableStream');
        }
    }
    
    // 10.10 WritableStream
    if (typeof WritableStream !== 'undefined') {
        for (let i = 0; i < N; i++) {
            store(new WritableStream({
                write(chunk) {}
            }), 'WritableStream');
        }
    }
}

function main() {
    console.log('========================================');
    console.log('Web API 兼容对象测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateWebAPIObjects();
    
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

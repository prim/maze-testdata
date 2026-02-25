/**
 * Node.js 核心模块对象测试
 * 
 * 测试对象：EventEmitter, Stream, URL, crypto, zlib, vm, MessageChannel
 */

'use strict';

const events = require('events');
const stream = require('stream');
const crypto = require('crypto');
const zlib = require('zlib');
const url = require('url');
const vm = require('vm');
const { MessageChannel } = require('worker_threads');

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

function generateNodeCoreObjects() {
    console.log('生成 Node.js 核心模块对象...');
    
    // 8.1 EventEmitter
    for (let i = 0; i < N; i++) {
        const emitter = new events.EventEmitter();
        emitter.on('event1', () => {});
        emitter.on('event2', () => {});
        store(emitter, 'EventEmitter');
    }
    
    // 8.2 Stream.Readable
    for (let i = 0; i < N; i++) {
        store(new stream.Readable({
            read() { this.push(null); }
        }), 'Stream.Readable');
    }
    
    // 8.3 Stream.Writable
    for (let i = 0; i < N; i++) {
        store(new stream.Writable({
            write(chunk, enc, cb) { cb(); }
        }), 'Stream.Writable');
    }
    
    // 8.4 Stream.Transform
    for (let i = 0; i < N; i++) {
        store(new stream.Transform({
            transform(chunk, enc, cb) { cb(null, chunk); }
        }), 'Stream.Transform');
    }
    
    // 8.5 URL
    for (let i = 0; i < N; i++) {
        store(new URL(`https://example.com/path/${i}?query=${i}`), 'URL');
    }
    
    // 8.6 URLSearchParams
    for (let i = 0; i < N; i++) {
        const params = new URLSearchParams();
        params.append('key1', `value_${i}`);
        store(params, 'URLSearchParams');
    }
    
    // 8.7 crypto.Hash
    for (let i = 0; i < N; i++) {
        const hash = crypto.createHash('sha256');
        hash.update(`data_${i}`);
        store(hash, 'crypto.Hash');
    }
    
    // 8.8 zlib.Gzip
    for (let i = 0; i < N; i++) {
        store(zlib.createGzip(), 'zlib.Gzip');
    }
    
    // 8.9 vm.Script
    for (let i = 0; i < N; i++) {
        store(new vm.Script(`x + ${i}`), 'vm.Script');
    }
    
    // 8.10 MessageChannel
    for (let i = 0; i < N; i++) {
        const channel = new MessageChannel();
        store({ channel, port1: channel.port1, port2: channel.port2 }, 'MessageChannel');
    }
}

function main() {
    console.log('========================================');
    console.log('Node.js 核心模块对象测试');
    console.log('========================================');
    console.log(`Node.js 版本: ${process.version}`);
    console.log(`进程 PID: ${process.pid}`);
    console.log(`每种类型数量: ${N}`);
    console.log('========================================\n');
    
    generateNodeCoreObjects();
    
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

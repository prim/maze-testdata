/**
 * Node.js 内存分析测试用例
 * 
 * 测试目标：
 *   1. 验证 Maze 能识别各种 Node.js/V8 对象类型
 *   2. 统计对象数量和内存占用
 * 
 * 测试数据：
 *   - 10,000 个普通对象
 *   - 1,000 个数组
 *   - 1,000 个 Buffer
 *   - 1,000 个 Map
 *   - 1,000 个 Set
 *   - 等等
 * 
 * 运行方式：
 *   node test.js
 *   # 等待 "READY FOR GCORE" 输出后捕获 coredump
 * 
 * Node.js 版本要求：v18.x (已测试 v18.20.8)
 */

const v8 = require('v8');
const path = require('path');
const events = require('events');

// 全局 Map 存储所有实例，防止被 GC 回收
const globalMap = new Map();

// 自增计数器
let counter = 0;

// 对象计数
const stats = {
	objects: 0,
	arrays: 0,
	buffers: 0,
	dates: 0,
	regexps: 0,
	errors: 0,
	promises: 0,
	sets: 0,
	maps: 0,
	eventEmitters: 0,
	functions: 0,
	arrayBuffers: 0,
	typedArrays: 0,
	customClasses: 0
};

// 自定义类
class MyClass {
	constructor(id) {
		this.id = id;
		this.name = `instance_${id}`;
		this.timestamp = Date.now();
	}

	method() {
		return this.id * 2;
	}
}

// 生成不同类型的 Node.js 对象实例
function generateInstances() {
	console.log('开始生成各种类型的实例...');

	// 1. 基本对象类型 (10,000 个)
	for (let i = 0; i < 10000; i++) {
		globalMap.set(++counter, {
			id: i,
			name: `object_${i}`,
			value: Math.random(),
			nested: { x: i, y: i * 2 }
		});
		stats.objects++;
	}

	// 2. 数组 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		globalMap.set(++counter, Array.from({ length: 10 }, (_, idx) => idx + i));
		stats.arrays++;
	}

	// 3. Buffer (1,000 个)
	for (let i = 0; i < 1000; i++) {
		globalMap.set(++counter, Buffer.alloc(100, i % 256));
		stats.buffers++;
	}

	// 4. Date 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		globalMap.set(++counter, new Date(Date.now() + i * 1000));
		stats.dates++;
	}

	// 5. RegExp 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		globalMap.set(++counter, new RegExp(`pattern_${i}`, 'gi'));
		stats.regexps++;
	}

	// 6. Error 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const error = new Error(`Error message ${i}`);
		error.code = `ERR_${i}`;
		globalMap.set(++counter, error);
		stats.errors++;
	}

	// 7. Promise 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		globalMap.set(++counter, new Promise((resolve) => {
			setTimeout(() => resolve(i), 10000000);  // 很久才 resolve
		}));
		stats.promises++;
	}

	// 8. Set 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const set = new Set();
		for (let j = 0; j < 5; j++) {
			set.add(`item_${i}_${j}`);
		}
		globalMap.set(++counter, set);
		stats.sets++;
	}

	// 9. Map 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const map = new Map();
		for (let j = 0; j < 5; j++) {
			map.set(`key_${j}`, `value_${i}_${j}`);
		}
		globalMap.set(++counter, map);
		stats.maps++;
	}

	// 10. EventEmitter 对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const emitter = new events.EventEmitter();
		emitter.on('test', () => { });
		globalMap.set(++counter, emitter);
		stats.eventEmitters++;
	}

	// 11. 函数对象 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const func = function () { return i; };
		func.customProperty = i;
		globalMap.set(++counter, func);
		stats.functions++;
	}

	// 12. ArrayBuffer (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const buffer = new ArrayBuffer(64);
		globalMap.set(++counter, buffer);
		stats.arrayBuffers++;
	}

	// 13. TypedArray - Uint8Array (1,000 个)
	for (let i = 0; i < 1000; i++) {
		const typed = new Uint8Array(32);
		typed.fill(i % 256);
		globalMap.set(++counter, typed);
		stats.typedArrays++;
	}

	// 14. 自定义类实例 (1,000 个)
	for (let i = 0; i < 1000; i++) {
		globalMap.set(++counter, new MyClass(i));
		stats.customClasses++;
	}

	console.log(`总共生成了 ${globalMap.size} 个实例`);
	console.log('统计:', stats);
}

// 生成 heap snapshot
function generateHeapSnapshot() {
	const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
	const filename = `heap-snapshot-${timestamp}.heapsnapshot`;

	console.log(`正在生成 heap snapshot: ${filename}`);
	// v8.writeHeapSnapshot(filename);

    v8.writeHeapSnapshot(filename, {
        exposeNumericValues: true,
        exposeInternals: true
    });
	console.log(`Heap snapshot 已保存到: ${path.resolve(filename)}`);
}

// 主函数
function main() {
	console.log('========================================');
	console.log(`Node.js Version: ${process.version}`);
	console.log(`Process PID: ${process.pid}`);
	console.log('========================================');

	// 生成实例
	generateInstances();

	// 显示内存使用
	const mem = process.memoryUsage();
	console.log('内存使用:');
	console.log(`  - heapUsed: ${(mem.heapUsed / 1024 / 1024).toFixed(2)} MB`);
	console.log(`  - heapTotal: ${(mem.heapTotal / 1024 / 1024).toFixed(2)} MB`);
	console.log(`  - rss: ${(mem.rss / 1024 / 1024).toFixed(2)} MB`);

	generateHeapSnapshot();

	// 输出 READY 信号
	console.log('');
	console.log('READY FOR GCORE');
	console.log(`Use: sudo gcore ${process.pid}`);
	console.log('');

	// 保持进程运行
	setInterval(() => { }, 30000);

	// 监听退出信号
	process.on('SIGINT', () => {
		console.log('\n退出中...');
		console.log(`最终 Map 大小: ${globalMap.size}`);
		process.exit(0);
	});
}

// 启动
main();

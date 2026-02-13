// Stringify 全面验证测试
// 目标: 覆盖所有 Stringify 路径，验证输出格式正确性
// 用法: node --expose-gc testdata/nodejs/20260213-stringify-verify/test.js
//
// 设计原则:
// 1. 每种类型创建足够多的实例(N=200)确保在 maze 一级表格中出现
// 2. 每种类型包含边界情况和典型情况
// 3. 对象之间有引用关系，测试引用图中的 stringify
// 4. 所有对象挂在 globalThis 上防止 GC

const N = 200;

// ============================================================
// 1. HeapNumber — 各种浮点数值
// ============================================================
const heapNumbers = [];
for (let i = 0; i < N; i++) {
  heapNumbers.push(3.14159265);       // 普通浮点
  heapNumbers.push(-0);               // 负零
  heapNumbers.push(Infinity);         // 正无穷
  heapNumbers.push(-Infinity);        // 负无穷
  heapNumbers.push(NaN);              // NaN
  heapNumbers.push(1.7976931348623157e+308); // MAX_VALUE
  heapNumbers.push(5e-324);           // MIN_VALUE
  heapNumbers.push(0.1 + 0.2);       // 经典浮点精度
}
// 用对象包装确保 HeapNumber 被分配到堆上
const heapNumberHolders = [];
for (let i = 0; i < N; i++) {
  heapNumberHolders.push({ val: heapNumbers[i * 8] });
}

// ============================================================
// 2. String — 各种字符串类型
// ============================================================
const strings_ = [];
for (let i = 0; i < N; i++) {
  strings_.push("short");                          // SeqOneByteString
  strings_.push("a".repeat(256));                   // 较长 SeqOneByteString
  strings_.push("你好世界" + i);                     // TwoByteString (中文)
  strings_.push("hello" + "world");                 // 可能被优化为 ConsString
  strings_.push("abcdefghijklmnopqrstuvwxyz".slice(5, 15)); // SlicedString
  strings_.push("");                                // 空字符串
  strings_.push("a".repeat(1000));                  // 长字符串 (截断测试)
}

// ============================================================
// 3. Oddball — undefined/null/true/false
// ============================================================
const oddballHolders = [];
for (let i = 0; i < N; i++) {
  oddballHolders.push({
    u: undefined,
    n: null,
    t: true,
    f: false,
  });
}

// ============================================================
// 4. JSArray — 各种数组形态
// ============================================================
const arrays = [];
for (let i = 0; i < N; i++) {
  arrays.push([1, 2, 3]);                          // 纯 Smi 数组
  arrays.push([1.1, 2.2, 3.3]);                    // 纯 double 数组
  arrays.push(["a", "b", "c"]);                    // 纯字符串数组
  arrays.push([1, "mixed", null, true, {x: i}]);   // 混合类型
  arrays.push([]);                                  // 空数组
  arrays.push(new Array(1000));                     // holey 数组 (length=1000, 无元素)
  const sparse = [];
  sparse[0] = "first";
  sparse[999] = "last";
  arrays.push(sparse);                              // 稀疏数组
  arrays.push([...Array(20).keys()]);               // 较长数组 (测试截断)
}

// ============================================================
// 5. JSObject — 各种对象形态
// ============================================================
const objects = [];
for (let i = 0; i < N; i++) {
  objects.push({a: 1, b: "hello", c: true});        // 普通对象
  objects.push({});                                  // 空对象
  objects.push(Object.create(null));                 // 无原型对象
  objects.push({nested: {deep: {value: i}}});        // 嵌套对象
  // 大量属性的对象 (会使用 dictionary mode)
  const big = {};
  for (let j = 0; j < 50; j++) big[`prop${j}`] = j;
  objects.push(big);
}

// ============================================================
// 6. JSFunction — 各种函数形态
// ============================================================
const functions = [];
for (let i = 0; i < N; i++) {
  functions.push(function namedFunc() { return i; });
  functions.push(() => i);                           // 箭头函数
  functions.push(function() { return i; });          // 匿名函数
  functions.push(async function asyncFunc() {});     // async 函数
  functions.push(class MyClass {});                  // class (也是函数)
}

// ============================================================
// 7. JSPromise — 三种状态
// ============================================================
const promises = [];
for (let i = 0; i < N; i++) {
  // pending
  promises.push(new Promise(() => {}));
  // fulfilled with Smi
  promises.push(Promise.resolve(42));
  // fulfilled with string
  promises.push(Promise.resolve("hello"));
  // fulfilled with object
  promises.push(Promise.resolve({result: i}));
  // rejected
  const rejected = Promise.reject(new Error(`err${i}`));
  rejected.catch(() => {});
  promises.push(rejected);
  // fulfilled with undefined
  promises.push(Promise.resolve(undefined));
  // fulfilled with null
  promises.push(Promise.resolve(null));
}

// ============================================================
// 8. JSRegExp — 各种正则
// ============================================================
const regexps = [];
for (let i = 0; i < N; i++) {
  regexps.push(/^hello$/gi);                        // 字面量 + flags
  regexps.push(new RegExp(`pat${i}`, "ms"));        // 动态 + ms flags
  regexps.push(/simple/);                           // 无 flags
  regexps.push(new RegExp("unicode", "u"));         // unicode flag
  regexps.push(/test/dgimsuy);                      // 所有 flags (除 v)
  regexps.push(new RegExp("", ""));                 // 空 pattern
  regexps.push(/(?:)/);                             // 默认空 pattern
}

// ============================================================
// 9. JSDate — 各种日期
// ============================================================
const dates = [];
for (let i = 0; i < N; i++) {
  dates.push(new Date("2024-01-15T10:30:00Z"));     // 正常 UTC
  dates.push(new Date(0));                           // epoch
  dates.push(new Date(-1));                          // epoch 前 1ms
  dates.push(new Date(1700000000000));               // 2023-11-14
  dates.push(new Date("invalid"));                   // Invalid Date (NaN)
  dates.push(new Date(8640000000000000));            // 最大合法日期
  dates.push(new Date(-8640000000000000));           // 最小合法日期
  dates.push(new Date(253402300799999));             // 9999-12-31T23:59:59.999Z
}

// ============================================================
// 10. JSArrayBuffer — 各种大小
// ============================================================
const arrayBuffers = [];
for (let i = 0; i < N; i++) {
  arrayBuffers.push(new ArrayBuffer(0));             // 空
  arrayBuffers.push(new ArrayBuffer(1));             // 最小
  arrayBuffers.push(new ArrayBuffer(1024));          // 1KB
  arrayBuffers.push(new ArrayBuffer(65536));         // 64KB
}

// ============================================================
// 11. JSTypedArray — 全部 11 种
// ============================================================
const typedArrays = [];
for (let i = 0; i < N; i++) {
  typedArrays.push(new Uint8Array(10));
  typedArrays.push(new Int8Array(20));
  typedArrays.push(new Uint16Array(30));
  typedArrays.push(new Int16Array(40));
  typedArrays.push(new Uint32Array(50));
  typedArrays.push(new Int32Array(60));
  typedArrays.push(new Float32Array(70));
  typedArrays.push(new Float64Array(80));
  typedArrays.push(new Uint8ClampedArray(90));
  typedArrays.push(new BigInt64Array(5));
  typedArrays.push(new BigUint64Array(5));
  // 边界: 空 TypedArray
  typedArrays.push(new Uint8Array(0));
  // 边界: 从 ArrayBuffer 的 offset 创建
  const buf = new ArrayBuffer(100);
  typedArrays.push(new Uint8Array(buf, 10, 50));
}

// ============================================================
// 12. DataView
// ============================================================
const dataViews = [];
for (let i = 0; i < N; i++) {
  dataViews.push(new DataView(new ArrayBuffer(32)));
  dataViews.push(new DataView(new ArrayBuffer(0)));  // 空 DataView
}

// ============================================================
// 13. Generator / AsyncGenerator
// ============================================================
function* genFunc() { yield 1; yield 2; }
function* anotherGen() { yield "a"; }
async function* asyncGenFunc() { yield 1; }

const generators = [];
for (let i = 0; i < N; i++) {
  generators.push(genFunc());
  generators.push(anotherGen());
  generators.push(asyncGenFunc());
}

// ============================================================
// 14. Set / Map — 各种大小
// ============================================================
const sets = [];
const maps = [];
for (let i = 0; i < N; i++) {
  // 空 Set/Map
  sets.push(new Set());
  maps.push(new Map());
  // 小 Set/Map
  sets.push(new Set([1, 2, 3]));
  maps.push(new Map([["a", 1], ["b", 2]]));
  // 大 Set/Map
  const bigSet = new Set();
  const bigMap = new Map();
  for (let j = 0; j < 100; j++) {
    bigSet.add(j);
    bigMap.set(`key${j}`, j);
  }
  sets.push(bigSet);
  maps.push(bigMap);
}

// ============================================================
// 15. WeakMap / WeakSet
// ============================================================
const weakMaps = [];
const weakSets = [];
const weakKeys = []; // prevent GC
for (let i = 0; i < N; i++) {
  const wm = new WeakMap();
  const key1 = {id: i};
  wm.set(key1, `val${i}`);
  weakMaps.push(wm);
  weakKeys.push(key1);

  const ws = new WeakSet();
  const key2 = {wsId: i};
  ws.add(key2);
  weakSets.push(ws);
  weakKeys.push(key2);
}

// ============================================================
// 16. Error 子类型
// ============================================================
const errors = [];
for (let i = 0; i < N; i++) {
  errors.push(new Error(`error${i}`));
  errors.push(new TypeError(`type${i}`));
  errors.push(new RangeError(`range${i}`));
  errors.push(new ReferenceError(`ref${i}`));
  errors.push(new SyntaxError(`syntax${i}`));
  errors.push(new URIError(`uri${i}`));
  errors.push(new EvalError(`eval${i}`));
}

// ============================================================
// 17. Symbol
// ============================================================
const symbols = [];
const symbolHolders = [];
for (let i = 0; i < N; i++) {
  const s = Symbol(`desc${i}`);
  symbols.push(s);
  symbolHolders.push({[s]: i, sym: s});
}

// ============================================================
// 18. 引用链测试 — 对象之间的引用关系
// ============================================================
const refChain = [];
for (let i = 0; i < N; i++) {
  const root = {
    name: `root${i}`,
    arr: [1, 2, 3],
    map: new Map([["k", "v"]]),
    set: new Set([10, 20]),
    promise: Promise.resolve(i),
    date: new Date("2024-06-15"),
    regexp: /test/gi,
    buffer: new ArrayBuffer(64),
    typed: new Float64Array(8),
    gen: genFunc(),
    nested: {
      inner: {
        deep: new Map([["deep", true]]),
      },
    },
  };
  refChain.push(root);
}

// ============================================================
// 19. SharedArrayBuffer (如果支持)
// ============================================================
const sharedBuffers = [];
try {
  for (let i = 0; i < N; i++) {
    sharedBuffers.push(new SharedArrayBuffer(256));
  }
} catch(e) {
  console.log("SharedArrayBuffer not available:", e.message);
}

// ============================================================
// 20. Proxy (特殊对象)
// ============================================================
const proxies = [];
for (let i = 0; i < N; i++) {
  const target = {x: i};
  const handler = {
    get(t, p) { return t[p]; }
  };
  proxies.push(new Proxy(target, handler));
  proxies.push(target); // keep target alive
}

// ============================================================
// Keep alive
// ============================================================
globalThis.__verify = {
  heapNumbers, heapNumberHolders,
  strings: strings_,
  oddballHolders,
  arrays,
  objects,
  functions,
  promises,
  regexps,
  dates,
  arrayBuffers,
  typedArrays,
  dataViews,
  generators,
  sets, maps,
  weakMaps, weakSets, weakKeys,
  errors,
  symbols, symbolHolders,
  refChain,
  sharedBuffers,
  proxies,
};

console.log("=== Stringify Verify Test ===");
console.log("PID:", process.pid);
console.log("Types created:");
console.log("  HeapNumber holders:", heapNumberHolders.length);
console.log("  Strings:", strings_.length);
console.log("  Oddball holders:", oddballHolders.length);
console.log("  Arrays:", arrays.length);
console.log("  Objects:", objects.length);
console.log("  Functions:", functions.length);
console.log("  Promises:", promises.length);
console.log("  RegExps:", regexps.length);
console.log("  Dates:", dates.length);
console.log("  ArrayBuffers:", arrayBuffers.length);
console.log("  TypedArrays:", typedArrays.length);
console.log("  DataViews:", dataViews.length);
console.log("  Generators:", generators.length);
console.log("  Sets:", sets.length);
console.log("  Maps:", maps.length);
console.log("  WeakMaps:", weakMaps.length);
console.log("  WeakSets:", weakSets.length);
console.log("  Errors:", errors.length);
console.log("  Symbols:", symbols.length);
console.log("  RefChain:", refChain.length);
console.log("  SharedBuffers:", sharedBuffers.length);
console.log("  Proxies:", proxies.length);
console.log("\nWaiting for gcore... (Ctrl+C to exit)");

setInterval(() => {}, 60000);

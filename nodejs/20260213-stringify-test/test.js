// Stringify 测试用例
// 覆盖所有新增 stringify 的类型
// 用法: node --expose-gc testdata/nodejs/20260213-stringify-test/test.js
// 然后 gcore 抓 coredump，用 maze --show-stringify 验证

const N = 100;

// ============================================================
// 1. Oddball (通过对象属性引用 undefined/null/true/false)
// ============================================================
const oddballs = [];
for (let i = 0; i < N; i++) {
  oddballs.push({
    u: undefined,
    n: null,
    t: true,
    f: false,
  });
}

// ============================================================
// 2. Array (dense / sparse / empty / mixed)
// ============================================================
const arrays = [];
for (let i = 0; i < N; i++) {
  // dense
  arrays.push([1, 2, 3, "hello", true]);
  // sparse
  const sparse = [];
  sparse[0] = "first";
  sparse[100] = "last";
  arrays.push(sparse);
  // empty
  arrays.push([]);
  // mixed types
  arrays.push([i, `str${i}`, null, undefined, { x: i }]);
}

// ============================================================
// 3. Promise (pending / fulfilled / rejected)
// ============================================================
const promises = [];
for (let i = 0; i < N; i++) {
  // pending
  promises.push(new Promise(() => {}));
  // fulfilled
  promises.push(Promise.resolve(42 + i));
  // rejected (suppress unhandled rejection)
  const rejected = Promise.reject(new Error(`err${i}`));
  rejected.catch(() => {});
  promises.push(rejected);
}

// ============================================================
// 4. RegExp (动态 / 字面量)
// ============================================================
const regexps = [];
for (let i = 0; i < N; i++) {
  regexps.push(/^hello\d+$/gi);
  regexps.push(new RegExp(`pattern${i}`, "ms"));
  regexps.push(/simple/);
  regexps.push(new RegExp("unicode", "u"));
}

// ============================================================
// 5. Date (正常 / Invalid)
// ============================================================
const dates = [];
for (let i = 0; i < N; i++) {
  dates.push(new Date("2024-01-15T10:30:00Z"));
  dates.push(new Date(1700000000000 + i * 1000));
  dates.push(new Date("invalid-date")); // Invalid Date
  dates.push(new Date(0)); // epoch
}

// ============================================================
// 6. ArrayBuffer
// ============================================================
const arrayBuffers = [];
for (let i = 0; i < N; i++) {
  arrayBuffers.push(new ArrayBuffer(1024));
  arrayBuffers.push(new ArrayBuffer(64));
  arrayBuffers.push(new ArrayBuffer(0));
}

// ============================================================
// 7. TypedArray (11 种)
// ============================================================
const typedArrays = [];
for (let i = 0; i < N; i++) {
  typedArrays.push(new Uint8Array(10));
  typedArrays.push(new Int8Array(10));
  typedArrays.push(new Uint16Array(10));
  typedArrays.push(new Int16Array(10));
  typedArrays.push(new Uint32Array(10));
  typedArrays.push(new Int32Array(10));
  typedArrays.push(new Float32Array(10));
  typedArrays.push(new Float64Array(10));
  typedArrays.push(new Uint8ClampedArray(10));
  typedArrays.push(new BigInt64Array(10));
  typedArrays.push(new BigUint64Array(10));
}

// ============================================================
// 8. DataView
// ============================================================
const dataViews = [];
for (let i = 0; i < N; i++) {
  dataViews.push(new DataView(new ArrayBuffer(32)));
}

// ============================================================
// 9. Generator / AsyncGenerator
// ============================================================
function* myGen() {
  yield 1;
  yield 2;
  yield 3;
}

async function* myAsyncGen() {
  yield "a";
  yield "b";
}

const generators = [];
for (let i = 0; i < N; i++) {
  generators.push(myGen());
  generators.push(myAsyncGen());
}

// ============================================================
// 10. WeakMap / WeakSet
// ============================================================
const weakMaps = [];
const weakSets = [];
for (let i = 0; i < N; i++) {
  const wm = new WeakMap();
  const key = { id: i };
  wm.set(key, `value${i}`);
  weakMaps.push(wm);
  weakMaps.push(key); // prevent GC

  const ws = new WeakSet();
  const wsKey = { wsId: i };
  ws.add(wsKey);
  weakSets.push(ws);
  weakSets.push(wsKey); // prevent GC
}

// ============================================================
// 11. Error / TypeError (对照组)
// ============================================================
const errors = [];
for (let i = 0; i < N; i++) {
  errors.push(new Error(`error${i}`));
  errors.push(new TypeError(`type-error${i}`));
  errors.push(new RangeError(`range-error${i}`));
}

// ============================================================
// Keep alive — 等待 gcore
// ============================================================
console.log("Stringify test objects created. PID:", process.pid);
console.log("Objects summary:");
console.log("  oddballs:", oddballs.length);
console.log("  arrays:", arrays.length);
console.log("  promises:", promises.length);
console.log("  regexps:", regexps.length);
console.log("  dates:", dates.length);
console.log("  arrayBuffers:", arrayBuffers.length);
console.log("  typedArrays:", typedArrays.length);
console.log("  dataViews:", dataViews.length);
console.log("  generators:", generators.length);
console.log("  weakMaps:", weakMaps.length);
console.log("  weakSets:", weakSets.length);
console.log("  errors:", errors.length);
console.log("\nWaiting for gcore... (Ctrl+C to exit)");

// Keep references alive
globalThis.__test = {
  oddballs, arrays, promises, regexps, dates,
  arrayBuffers, typedArrays, dataViews, generators,
  weakMaps, weakSets, errors,
};

// Sleep forever
setInterval(() => {}, 60000);

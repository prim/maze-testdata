// 引用图 (Reference Graph) 全面验证测试
// 目标: 测试 --random-dot 输出的引用图是否正确反映对象间的引用关系
// 用法: node --expose-gc testdata/nodejs/20260213-refgraph-verify/test.js
//
// 设计原则:
// 1. 每个场景创建明确的、可追踪的引用链
// 2. 引用链中包含不同 V8 类型的节点，验证跨类型引用
// 3. 场景之间相互独立，便于定位问题
// 4. 每个场景创建 N=200 份实例，确保在一级表格中出现
// 5. 对象命名有规律，便于在 dot 图中识别
//
// 验证方法:
//   1. gcore 抓 coredump
//   2. ./maze --pid <PID> --text --limit 50  查看一级表格
//   3. ./maze --pid <PID> --random-dot <ROW>  查看引用图
//   4. 对照下面每个场景的 "预期引用链" 检查 dot 图

const N = 200;

// ============================================================
// 场景 1: 线性引用链 (Object → Object → Object)
// 预期引用链: root1 → mid1 → leaf1
// 验证: dot 图应显示 3 个 Object 节点的线性链
// ============================================================
const scenario1 = [];
for (let i = 0; i < N; i++) {
  const leaf = { type: "s1-leaf", value: i };
  const mid = { type: "s1-mid", child: leaf };
  const root = { type: "s1-root", child: mid };
  scenario1.push(root);
}

// ============================================================
// 场景 2: Map 作为中间节点 (Object → Map → Object)
// 预期引用链: holder → Map → valueObj
// 验证: dot 图应显示 Object → Map(1) → Object 的引用路径
// ============================================================
const scenario2 = [];
for (let i = 0; i < N; i++) {
  const valueObj = { type: "s2-value", id: i };
  const m = new Map();
  m.set("data", valueObj);
  const holder = { type: "s2-holder", store: m };
  scenario2.push(holder);
}

// ============================================================
// 场景 3: Set 作为中间节点 (Object → Set → Object)
// 预期引用链: holder → Set → element
// 验证: dot 图应显示 Object → Set(1) → Object 的引用路径
// ============================================================
const scenario3 = [];
for (let i = 0; i < N; i++) {
  const element = { type: "s3-element", id: i };
  const s = new Set();
  s.add(element);
  const holder = { type: "s3-holder", store: s };
  scenario3.push(holder);
}

// ============================================================
// 场景 4: Array 作为中间节点 (Object → Array → Object)
// 预期引用链: holder → Array(3) → child objects
// 验证: dot 图应显示 Object → Array → 多个 Object 的扇出
// ============================================================
const scenario4 = [];
for (let i = 0; i < N; i++) {
  const c1 = { type: "s4-child", idx: 0 };
  const c2 = { type: "s4-child", idx: 1 };
  const c3 = { type: "s4-child", idx: 2 };
  const arr = [c1, c2, c3];
  const holder = { type: "s4-holder", items: arr };
  scenario4.push(holder);
}

// ============================================================
// 场景 5: Promise 引用链 (Object → Promise → resolved value)
// 预期引用链: holder → Promise(fulfilled) → resultObj
// 验证: dot 图应显示 Object → Promise(fulfilled) → Object
// ============================================================
const scenario5 = [];
for (let i = 0; i < N; i++) {
  const resultObj = { type: "s5-result", id: i };
  const p = Promise.resolve(resultObj);
  const holder = { type: "s5-holder", promise: p };
  scenario5.push(holder);
}

// ============================================================
// 场景 6: Function 闭包引用 (Object → Function → 闭包变量)
// 预期引用链: holder → Function → Context → captured
// 验证: dot 图应显示 Object → Function → Context → Object
// ============================================================
const scenario6 = [];
for (let i = 0; i < N; i++) {
  const captured = { type: "s6-captured", id: i };
  const fn = function s6func() { return captured; };
  const holder = { type: "s6-holder", callback: fn };
  scenario6.push(holder);
}

// ============================================================
// 场景 7: 多类型混合引用链
// (Object → Map → Array → Set → Object)
// 预期引用链: root → Map → Array → Set → leaf
// 验证: dot 图应显示 4 种不同类型节点的链式引用
// ============================================================
const scenario7 = [];
for (let i = 0; i < N; i++) {
  const leaf = { type: "s7-leaf", id: i };
  const s = new Set([leaf]);
  const arr = [s];
  const m = new Map([["chain", arr]]);
  const root = { type: "s7-root", data: m };
  scenario7.push(root);
}

// ============================================================
// 场景 8: 树形引用 (一个父节点引用多个不同类型子节点)
// 预期引用链: parent → {Map, Set, Array, Date, RegExp, Promise}
// 验证: dot 图应显示一个 Object 扇出到 6 种不同类型
// ============================================================
const scenario8 = [];
for (let i = 0; i < N; i++) {
  const parent = {
    type: "s8-parent",
    myMap: new Map([["k", i]]),
    mySet: new Set([i, i + 1]),
    myArr: [i, i + 1, i + 2],
    myDate: new Date("2024-06-15"),
    myRegex: /test/gi,
    myPromise: Promise.resolve(i),
  };
  scenario8.push(parent);
}

// ============================================================
// 场景 9: 循环引用 (Object ↔ Object)
// 预期引用链: a ↔ b (双向引用)
// 验证: dot 图应显示两个 Object 之间的双向边
// ============================================================
const scenario9 = [];
for (let i = 0; i < N; i++) {
  const a = { type: "s9-a", id: i };
  const b = { type: "s9-b", id: i };
  a.peer = b;
  b.peer = a;
  scenario9.push(a);
}

// ============================================================
// 场景 10: 三角循环引用 (A → B → C → A)
// 预期引用链: a → b → c → a
// 验证: dot 图应显示三角形循环
// ============================================================
const scenario10 = [];
for (let i = 0; i < N; i++) {
  const a = { type: "s10-a" };
  const b = { type: "s10-b" };
  const c = { type: "s10-c" };
  a.next = b;
  b.next = c;
  c.next = a;
  scenario10.push(a);
}

// ============================================================
// 场景 11: Map 的 key 和 value 都是对象
// 预期引用链: holder → Map → {keyObj, valueObj}
// 验证: dot 图应显示 Map 同时引用 key 和 value 对象
// ============================================================
const scenario11 = [];
for (let i = 0; i < N; i++) {
  const keyObj = { type: "s11-key", id: i };
  const valueObj = { type: "s11-value", id: i };
  const m = new Map();
  m.set(keyObj, valueObj);
  const holder = { type: "s11-holder", store: m };
  scenario11.push(holder);
}

// ============================================================
// 场景 12: WeakMap 引用 (Object → WeakMap → key/value)
// 预期引用链: holder → WeakMap, key → value
// 验证: dot 图应显示 WeakMap 的引用关系
// ============================================================
const scenario12 = [];
const scenario12keys = []; // prevent GC of keys
for (let i = 0; i < N; i++) {
  const key = { type: "s12-key", id: i };
  const value = { type: "s12-value", id: i };
  const wm = new WeakMap();
  wm.set(key, value);
  scenario12keys.push(key);
  const holder = { type: "s12-holder", wm: wm, keyRef: key };
  scenario12.push(holder);
}

// ============================================================
// 场景 13: Error 对象引用链 (Object → Error → stack)
// 预期引用链: holder → Error → (内部 stack 字符串)
// 验证: dot 图应显示 Object → Error 的引用
// ============================================================
const scenario13 = [];
for (let i = 0; i < N; i++) {
  const err = new TypeError(`scenario13-error-${i}`);
  const holder = { type: "s13-holder", error: err, id: i };
  scenario13.push(holder);
}

// ============================================================
// 场景 14: Generator 引用链 (Object → Generator → Function)
// 预期引用链: holder → Generator → genFunc
// 验证: dot 图应显示 Object → Generator 的引用
// ============================================================
function* scenario14Gen(data) {
  yield data.value;
  yield data.value * 2;
}
const scenario14 = [];
for (let i = 0; i < N; i++) {
  const data = { value: i };
  const gen = scenario14Gen(data);
  gen.next(); // advance to first yield
  const holder = { type: "s14-holder", gen: gen, data: data };
  scenario14.push(holder);
}

// ============================================================
// 场景 15: TypedArray → ArrayBuffer 引用
// 预期引用链: holder → TypedArray → ArrayBuffer
// 验证: dot 图应显示 Object → TypedArray → ArrayBuffer
// ============================================================
const scenario15 = [];
for (let i = 0; i < N; i++) {
  const buf = new ArrayBuffer(64);
  const view = new Float64Array(buf);
  const holder = { type: "s15-holder", view: view, buf: buf };
  scenario15.push(holder);
}

// ============================================================
// 场景 16: 深层嵌套 (5 层 Object 链)
// 预期引用链: L0 → L1 → L2 → L3 → L4
// 验证: dot 图应显示 5 层深度的线性链
// ============================================================
const scenario16 = [];
for (let i = 0; i < N; i++) {
  const L4 = { type: "s16-L4", id: i };
  const L3 = { type: "s16-L3", child: L4 };
  const L2 = { type: "s16-L2", child: L3 };
  const L1 = { type: "s16-L1", child: L2 };
  const L0 = { type: "s16-L0", child: L1 };
  scenario16.push(L0);
}

// ============================================================
// 场景 17: 共享引用 (多个父节点引用同一个子节点)
// 预期引用链: parent1 → shared ← parent2
// 验证: dot 图应显示两个 Object 都指向同一个 Object
// ============================================================
const scenario17 = [];
for (let i = 0; i < N; i++) {
  const shared = { type: "s17-shared", id: i };
  const parent1 = { type: "s17-p1", ref: shared };
  const parent2 = { type: "s17-p2", ref: shared };
  scenario17.push(parent1);
  scenario17.push(parent2);
}

// ============================================================
// 场景 18: Map 嵌套 Map (Map → Map → Object)
// 预期引用链: outer → innerMap → leaf
// 验证: dot 图应显示 Map → Map → Object 的嵌套引用
// ============================================================
const scenario18 = [];
for (let i = 0; i < N; i++) {
  const leaf = { type: "s18-leaf", id: i };
  const inner = new Map([["data", leaf]]);
  const outer = new Map([["nested", inner]]);
  const holder = { type: "s18-holder", store: outer };
  scenario18.push(holder);
}

// ============================================================
// 场景 19: Set 包含 Map，Map 包含 Array (Set → Map → Array → Object)
// 预期引用链: holder → Set → Map → Array → leaf
// 验证: dot 图应显示 4 种容器类型的嵌套引用
// ============================================================
const scenario19 = [];
for (let i = 0; i < N; i++) {
  const leaf = { type: "s19-leaf", id: i };
  const arr = [leaf];
  const m = new Map([["items", arr]]);
  const s = new Set([m]);
  const holder = { type: "s19-holder", store: s };
  scenario19.push(holder);
}

// ============================================================
// 场景 20: 综合场景 — 模拟真实应用的对象图
// 模拟: UserSession → {user, permissions, cache, eventHandlers}
// 预期引用链: session → user(Object), permissions(Set),
//             cache(Map → Array → Object), handlers(Array → Function)
// ============================================================
const scenario20 = [];
for (let i = 0; i < N; i++) {
  const userData = { type: "s20-user", name: `user${i}`, email: `u${i}@test.com` };
  const permissions = new Set(["read", "write", "admin"]);

  const cacheItem1 = { type: "s20-cache-item", key: "profile", data: { age: 25 + i } };
  const cacheItem2 = { type: "s20-cache-item", key: "prefs", data: { theme: "dark" } };
  const cache = new Map();
  cache.set("profile", cacheItem1);
  cache.set("prefs", cacheItem2);

  const capturedSession = { id: i };
  const onLogin = function onLogin() { return capturedSession; };
  const onLogout = function onLogout() { return capturedSession; };
  const handlers = [onLogin, onLogout];

  const session = {
    type: "s20-session",
    user: userData,
    permissions: permissions,
    cache: cache,
    handlers: handlers,
    createdAt: new Date(),
    pattern: /^session-\d+$/,
  };
  scenario20.push(session);
}

// ============================================================
// Keep alive — 所有场景挂在 globalThis 上
// ============================================================
globalThis.__refgraph = {
  s1_linear: scenario1,
  s2_map_ref: scenario2,
  s3_set_ref: scenario3,
  s4_array_ref: scenario4,
  s5_promise_ref: scenario5,
  s6_closure_ref: scenario6,
  s7_mixed_chain: scenario7,
  s8_tree_fanout: scenario8,
  s9_cycle_pair: scenario9,
  s10_cycle_triangle: scenario10,
  s11_map_obj_key: scenario11,
  s12_weakmap: scenario12,
  s12_keys: scenario12keys,
  s13_error: scenario13,
  s14_generator: scenario14,
  s15_typedarray: scenario15,
  s16_deep_nest: scenario16,
  s17_shared_ref: scenario17,
  s18_nested_map: scenario18,
  s19_nested_containers: scenario19,
  s20_real_world: scenario20,
};

console.log("=== Reference Graph Verify Test ===");
console.log("PID:", process.pid);
console.log("Scenarios created:");
console.log("  S1  Linear chain (Obj→Obj→Obj):", scenario1.length);
console.log("  S2  Map reference (Obj→Map→Obj):", scenario2.length);
console.log("  S3  Set reference (Obj→Set→Obj):", scenario3.length);
console.log("  S4  Array reference (Obj→Arr→Obj):", scenario4.length);
console.log("  S5  Promise reference (Obj→Promise→Obj):", scenario5.length);
console.log("  S6  Closure reference (Obj→Fn→Ctx→Obj):", scenario6.length);
console.log("  S7  Mixed chain (Obj→Map→Arr→Set→Obj):", scenario7.length);
console.log("  S8  Tree fanout (Obj→{Map,Set,Arr,Date,RegExp,Promise}):", scenario8.length);
console.log("  S9  Cycle pair (A↔B):", scenario9.length);
console.log("  S10 Cycle triangle (A→B→C→A):", scenario10.length);
console.log("  S11 Map obj key (Map→{keyObj,valObj}):", scenario11.length);
console.log("  S12 WeakMap (Obj→WeakMap→key/val):", scenario12.length);
console.log("  S13 Error chain (Obj→Error):", scenario13.length);
console.log("  S14 Generator (Obj→Gen→Fn):", scenario14.length);
console.log("  S15 TypedArray (Obj→TypedArray→ArrayBuffer):", scenario15.length);
console.log("  S16 Deep nest (5-level Obj chain):", scenario16.length);
console.log("  S17 Shared ref (P1→shared←P2):", scenario17.length);
console.log("  S18 Nested Map (Map→Map→Obj):", scenario18.length);
console.log("  S19 Nested containers (Set→Map→Arr→Obj):", scenario19.length);
console.log("  S20 Real-world session graph:", scenario20.length);
console.log("\nTotal objects (approx):", N * 20 * 3, "(scenarios × avg nodes)");
console.log("\nVerification steps:");
console.log("  1. gcore", process.pid);
console.log("  2. ./maze --pid", process.pid, "--text --limit 50");
console.log("  3. ./maze --pid", process.pid, "--random-dot <ROW>");
console.log("  4. Compare dot output with expected reference chains above");
console.log("\nWaiting for gcore... (Ctrl+C to exit)");

setInterval(() => {}, 60000);

//! Maze Rust fixture: complex live types.
//!
//! Builds a stable Rust object graph (global statics, TLS, Box/Vec/String,
//! Rc/Arc cycle, HashMap/HashSet/VecDeque, enums, `dyn Trait`, a closure, a
//! parked async generator, and FFI C/mmap allocations), dumps ground truth to
//! `rust-fixture-ground-truth.json`, then parks forever so a core can be
//! captured while every root and backing allocation is still live.
//!
//! The ground-truth file records addresses, lengths and capacities the Phase 1+
//! analyzers will reconcile against; Phase 0 only needs the ELF/DWARF identity
//! and the capture manifest.

use std::cell::RefCell;
use std::collections::{HashMap, HashSet, VecDeque};
use std::ffi::c_void;
use std::io::Write;
use std::rc::Rc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::Duration;

// ---------------------------------------------------------------------------
// Types that a Rust analyzer must be able to name from DWARF.
// ---------------------------------------------------------------------------

#[derive(Debug)]
struct Person {
    name: String,
    age: u32,
    tags: Vec<String>,
}

#[derive(Debug)]
enum Event {
    Started,
    Updated(u64),
    User { id: u64, name: String },
}

// RcNode is a single-threaded reference cycle (Rc + rc::Weak), kept off any
// static so the !Send/!Sync contents never force a OnceLock<...> constraint.
struct RcNode {
    label: String,
    next: RefCell<Option<Rc<RcNode>>>,
    back: RefCell<Option<std::rc::Weak<RcNode>>>,
}

// ArcNode is the thread-safe analogue (Arc + Mutex + sync::Weak); it can live
// in a static because every field is Send + Sync.
struct ArcNode {
    label: String,
    next: Mutex<Option<Arc<ArcNode>>>,
    back: Mutex<Option<std::sync::Weak<ArcNode>>>,
}

trait Speaker: Send + Sync {
    fn line(&self) -> String;
}

struct Dog {
    name: String,
}
impl Speaker for Dog {
    fn line(&self) -> String {
        format!("woof {}", self.name)
    }
}

struct Cat {
    name: String,
}
impl Speaker for Cat {
    fn line(&self) -> String {
        format!("meow {}", self.name)
    }
}

// ---------------------------------------------------------------------------
// Roots: statics, TLS, and FFI allocations that must survive to the core.
// ---------------------------------------------------------------------------

static GLOBAL_CACHE: OnceLock<Mutex<HashMap<String, Box<Person>>>> = OnceLock::new();
static GLOBAL_SPEAKERS: OnceLock<Vec<Box<dyn Speaker>>> = OnceLock::new();
static GLOBAL_VEC: OnceLock<Vec<Person>> = OnceLock::new();
static GLOBAL_ARC_NODE: OnceLock<Arc<ArcNode>> = OnceLock::new();
static GLOBAL_SET: OnceLock<HashSet<u64>> = OnceLock::new();
static GLOBAL_DEQUE: OnceLock<VecDeque<String>> = OnceLock::new();
static GLOBAL_SLICE_VIEW: OnceLock<&'static [u64]> = OnceLock::new();
// Addresses are stored as usize (raw pointers are neither Send nor Sync, so a
// OnceLock<*mut ...> would not compile). The backing allocations are leaked and
// stay live for the whole fixture lifetime.
static GLOBAL_C_CLASS_ADDR: OnceLock<usize> = OnceLock::new();
static GLOBAL_MMAP_ADDR: OnceLock<usize> = OnceLock::new();
static GLOBAL_FUTURE_ADDR: OnceLock<usize> = OnceLock::new();

thread_local! {
    static TLS_BUFFER: RefCell<Option<Box<Vec<u64>>>> = const { RefCell::new(None) };
    static TLS_COUNTER: RefCell<u64> = const { RefCell::new(0) };
}

// ---------------------------------------------------------------------------
// Minimal libc FFI surface (no crates). Uses the system allocator -> glibc
// ptmalloc on the target profile, plus a direct mmap for an anonymous region.
// ---------------------------------------------------------------------------

#[link(name = "c")]
#[allow(dead_code)] // the FFI surface is fixture surface; not every entry is called
extern "C" {
    fn malloc(size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn mmap(
        addr: *mut c_void,
        len: usize,
        prot: i32,
        flags: i32,
        fd: i32,
        offset: i64,
    ) -> *mut c_void;
    fn munmap(addr: *mut c_void, len: usize) -> i32;
}

const PROT_READ: i32 = 1;
const PROT_WRITE: i32 = 2;
const MAP_PRIVATE: i32 = 2;
const MAP_ANONYMOUS: i32 = 0x20;

// ---------------------------------------------------------------------------
// A dependency-free async generator: `pending_task` is a real async fn, so
// rustc materializes its generator state struct in DWARF. The fixture leaks the
// boxed generator and records its heap address; Phase 1+ can map that address
// back to the compiler-generated state type.
// ---------------------------------------------------------------------------

async fn pending_task(n: u64) -> u64 {
    let mut acc = n;
    for _ in 0..3 {
        acc = acc.wrapping_mul(31).wrapping_add(7);
    }
    acc
}

// ---------------------------------------------------------------------------
// Shared ground-truth writer (the owner thread appends, main thread persists).
// ---------------------------------------------------------------------------

static TRUTH: OnceLock<Mutex<Vec<(String, String)>>> = OnceLock::new();
static TRUTH_THREAD_DONE: AtomicBool = AtomicBool::new(false);

fn truth_kv(key: &str, value: String) {
    let buffer = TRUTH.get_or_init(|| Mutex::new(Vec::new()));
    buffer.lock().unwrap().push((key.to_string(), value));
}

fn truth_kv_usize(key: &str, value: usize) {
    truth_kv(key, format!("{:#x}", value));
}

fn addr_of<T>(ptr: *const T) -> usize {
    ptr as usize
}

fn write_ground_truth() {
    let buffer = TRUTH.get_or_init(|| Mutex::new(Vec::new()));
    let values = buffer.lock().unwrap().clone();
    let mut body = String::from("{\n");
    for (i, (k, v)) in values.iter().enumerate() {
        let comma = if i + 1 == values.len() { "" } else { "," };
        body.push_str(&format!("  {:?}: {:?}{}\n", k, v, comma));
    }
    body.push_str("}\n");
    let mut file = std::fs::File::create("rust-fixture-ground-truth.json")
        .expect("create ground truth file");
    file.write_all(body.as_bytes()).expect("write ground truth");
}

fn main() {
    truth_kv("fixture".to_string().as_str(), "20260806-complex-types-live".to_string());

    // -- global cache: HashMap<String, Box<Person>> --------------------------
    let cache = GLOBAL_CACHE.get_or_init(|| {
        let mut map = HashMap::new();
        map.insert(
            "alice".to_string(),
            Box::new(Person {
                name: "Alice".to_string(),
                age: 31,
                tags: vec!["admin".to_string(), "rust".to_string()],
            }),
        );
        map.insert(
            "bob".to_string(),
            Box::new(Person {
                name: "Bob".to_string(),
                age: 42,
                tags: vec!["user".to_string()],
            }),
        );
        map.insert(
            "carol".to_string(),
            Box::new(Person {
                name: "Carol".to_string(),
                age: 27,
                tags: vec!["moderator".to_string(), "go".to_string()],
            }),
        );
        Mutex::new(map)
    });
    {
        let map = cache.lock().unwrap();
        truth_kv_usize("global_cache_addr", addr_of(&*map));
        truth_kv_usize("global_cache_len", map.len());
        truth_kv_usize("global_cache_cap", map.capacity());
        if let Some(boxed) = map.get("bob") {
            let person: &Person = &**boxed;
            truth_kv_usize("box_bob_addr", addr_of(person));
            truth_kv_usize("box_bob_name_ptr", addr_of(person.name.as_ptr()));
            truth_kv_usize("box_bob_name_len", person.name.len());
            truth_kv_usize("box_bob_tags_ptr", addr_of(person.tags.as_ptr()));
            truth_kv_usize("box_bob_tags_len", person.tags.len());
            truth_kv_usize("box_bob_tags_cap", person.tags.capacity());
        }
    }

    // -- dyn Trait objects ----------------------------------------------------
    let speakers = GLOBAL_SPEAKERS.get_or_init(|| {
        let mut v: Vec<Box<dyn Speaker>> = Vec::new();
        v.push(Box::new(Dog { name: "rex".to_string() }));
        v.push(Box::new(Cat { name: "tama".to_string() }));
        v
    });
    truth_kv_usize("speakers_ptr", addr_of(speakers.as_ptr()));
    truth_kv_usize("speakers_len", speakers.len());

    // -- Vec<Person> backing --------------------------------------------------
    let people = GLOBAL_VEC.get_or_init(|| {
        vec![
            Person { name: "p1".to_string(), age: 1, tags: vec![] },
            Person { name: "p2".to_string(), age: 2, tags: vec!["x".to_string()] },
            Person { name: "p3".to_string(), age: 3, tags: vec!["y".to_string(), "z".to_string()] },
        ]
    });
    truth_kv_usize("vec_ptr", addr_of(people.as_ptr()));
    truth_kv_usize("vec_len", people.len());
    truth_kv_usize("vec_cap", people.capacity());

    // -- Rc cycle (Rc + Weak) -------------------------------------------------
    let a = Rc::new(RcNode {
        label: "cycle-a".to_string(),
        next: RefCell::new(None),
        back: RefCell::new(None),
    });
    let b = Rc::new(RcNode {
        label: "cycle-b".to_string(),
        next: RefCell::new(None),
        back: RefCell::new(None),
    });
    *a.next.borrow_mut() = Some(b.clone());
    *b.back.borrow_mut() = Some(Rc::downgrade(&a));
    truth_kv_usize("rc_cycle_a_addr", addr_of(Rc::as_ptr(&a)));
    truth_kv_usize("rc_cycle_b_addr", addr_of(Rc::as_ptr(&b)));
    drop(b);

    // -- Arc shared node -------------------------------------------------------
    let arc_node = GLOBAL_ARC_NODE.get_or_init(|| Arc::new(ArcNode {
        label: "arc-node".to_string(),
        next: Mutex::new(None),
        back: Mutex::new(None),
    }));
    truth_kv_usize("arc_node_addr", addr_of(Arc::as_ptr(arc_node)));
    {
        let clone = Arc::clone(arc_node);
        let strong = Arc::strong_count(&clone);
        let weak = Arc::weak_count(&clone);
        truth_kv("arc_strong_count", format!("{}", strong));
        truth_kv("arc_weak_count", format!("{}", weak));
        drop(clone);
    }

    // -- HashSet / VecDeque ----------------------------------------------------
    let set = GLOBAL_SET.get_or_init(|| (0u64..64).collect());
    truth_kv_usize("hashset_len", set.len());
    let deque = GLOBAL_DEQUE.get_or_init(|| {
        let mut d = VecDeque::new();
        for i in 0..16 {
            d.push_back(format!("item-{:02}", i));
        }
        d
    });
    truth_kv_usize("vecdeque_len", deque.len());
    truth_kv_usize("vecdeque_cap", deque.capacity());

    // -- slice view ------------------------------------------------------------
    let backing: &'static [u64] =
        Box::leak(vec![1u64, 2, 3, 4, 5, 6, 7, 8].into_boxed_slice());
    let _ = GLOBAL_SLICE_VIEW.set(backing);
    truth_kv_usize("slice_ptr", addr_of(backing.as_ptr()));
    truth_kv_usize("slice_len", backing.len());

    // -- TLS --------------------------------------------------------------------
    TLS_BUFFER.with(|cell| {
        *cell.borrow_mut() = Some(Box::new((0u64..256).collect()));
        if let Some(buf) = cell.borrow().as_ref() {
            truth_kv_usize("tls_buffer_ptr", addr_of(buf.as_ptr()));
            truth_kv_usize("tls_buffer_len", buf.len());
            truth_kv_usize("tls_buffer_cap", buf.capacity());
        }
    });
    TLS_COUNTER.with(|c| {
        *c.borrow_mut() = 12345;
        truth_kv_usize("tls_counter", *c.borrow() as usize);
    });

    // -- enum / Option / Result / closure on a named stack thread --------------
    let owner = thread::Builder::new()
        .name("fixture-owner".to_string())
        .spawn(move || {
            let event = Event::User { id: 7, name: "stack-user".to_string() };
            let maybe = Some(Person { name: "opt".to_string(), age: 9, tags: vec![] });
            let result: Result<u64, String> = Ok(42);
            let closure = |x: u64| -> u64 { x * 2 + event_match_size(&event) };
            let closed = closure(21);
            truth_kv_usize("stack_event_addr", addr_of(&event as *const Event));
            truth_kv_usize("stack_option_addr", addr_of(&maybe as *const Option<Person>));
            truth_kv_usize("stack_result_addr", addr_of(&result as *const Result<u64, String>));
            truth_kv("closure_result", format!("{}", closed));
            TRUTH_THREAD_DONE.store(true, Ordering::SeqCst);
            loop {
                thread::park();
            }
        })
        .expect("spawn owner thread");

    // -- async generator state (leaked on the heap, address recorded) -----------
    let boxed = Box::new(pending_task(42));
    let raw = Box::into_raw(boxed);
    let _ = GLOBAL_FUTURE_ADDR.set(raw as usize);
    truth_kv_usize("future_addr", raw as usize);

    // -- FFI C allocation + mmap (deliberately untyped from Rust's view) -------
    let c_class = unsafe { malloc(4096) };
    if !c_class.is_null() {
        unsafe { *(c_class as *mut u8) = 0xAB };
        let _ = GLOBAL_C_CLASS_ADDR.set(c_class as usize);
        truth_kv_usize("c_class_addr", c_class as usize);
    }
    let map = unsafe {
        mmap(std::ptr::null_mut(), 65536, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0)
    };
    if map != (usize::MAX as *mut c_void) {
        let _ = GLOBAL_MMAP_ADDR.set(map as usize);
        truth_kv_usize("mmap_addr", map as usize);
    }

    // -- wait for the owner thread's ground truth, persist, then park -----------
    while !TRUTH_THREAD_DONE.load(Ordering::SeqCst) {
        thread::sleep(Duration::from_millis(10));
    }
    truth_kv_usize("pid", std::process::id() as usize);
    write_ground_truth();

    println!("============================================================");
    println!(">>> READY FOR GCORE {} <<<", std::process::id());
    println!("============================================================");

    // Keep the process alive with all roots reachable; gcore attaches here.
    loop {
        thread::sleep(Duration::from_secs(3600));
    }
}

fn event_match_size(event: &Event) -> u64 {
    match event {
        Event::Started => 0,
        Event::Updated(n) => *n,
        Event::User { id, .. } => *id,
    }
}

//! High-cardinality Rust complex-types live fixture for Maze.
//!
//! The smaller 20260806 fixture is an ABI and fail-closed conformance case.
//! This fixture follows the Python complex-types tests instead: it creates many
//! independent instances of each language/container family so Web top results
//! have useful counts, while publishing a deterministic ground-truth summary.

#![allow(dead_code)]

use std::cell::RefCell;
use std::collections::{
    BTreeMap, BTreeSet, BinaryHeap, HashMap, HashSet, LinkedList, VecDeque,
};
use std::ffi::c_void;
use std::future::Future;
use std::hint::black_box;
use std::io::{BufWriter, Write};
use std::mem::size_of;
use std::pin::Pin;
use std::rc::Rc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock, Weak};
use std::thread;
use std::time::Duration;

const PERSON_COUNT: usize = 1_000;
const ENTITY_COUNT: usize = 300;
const TREE_ROOT_COUNT: usize = 200;
const TREE_NODE_COUNT: usize = TREE_ROOT_COUNT * 3;
const VECTOR_COUNT: usize = 500;
const HASH_MAP_COUNT: usize = 300;
const HASH_SET_COUNT: usize = 240;
const BTREE_MAP_COUNT: usize = 120;
const BTREE_SET_COUNT: usize = 120;
const DEQUE_COUNT: usize = 300;
const LINKED_LIST_COUNT: usize = 120;
const BINARY_HEAP_COUNT: usize = 200;
const SHORT_STRING_COUNT: usize = 1_000;
const MEDIUM_STRING_COUNT: usize = 500;
const LONG_STRING_COUNT: usize = 200;
const BYTE_BUFFER_COUNT: usize = 400;
const LANGUAGE_RECORD_COUNT: usize = 500;
const SPEAKER_COUNT: usize = 300;
const ARC_NODE_COUNT: usize = 200;
const RC_NODE_COUNT: usize = 128;
const FUTURE_COUNT: usize = 200;
const TLS_THREAD_COUNT: usize = 4;
const TLS_RECORDS_PER_THREAD: usize = 128;
const RAW_ALLOC_COUNT: usize = 64;
const RAW_ALLOC_SIZE: usize = 4_096;
const EXPECTED_READY_THREADS: usize = TLS_THREAD_COUNT + 1;

#[derive(Debug)]
enum Presence {
    Online { session_id: u64 },
    Idle(u32),
    Offline,
}

#[derive(Debug)]
struct Person {
    id: u64,
    name: String,
    email: String,
    tags: Vec<String>,
    scores: [u32; 8],
    presence: Presence,
}

#[derive(Debug)]
struct GameEntity {
    entity_id: u64,
    kind: String,
    position: (f64, f64, f64),
    hp: u32,
    inventory: Vec<String>,
    attributes: HashMap<String, i64>,
}

#[derive(Debug)]
struct TreeNode {
    value: u64,
    label: String,
    left: Option<Box<TreeNode>>,
    right: Option<Box<TreeNode>>,
}

#[derive(Debug)]
struct Payload {
    id: u64,
    label: String,
    bytes: Vec<u8>,
}

#[derive(Debug)]
enum Event {
    Created,
    Updated { field: String, version: u64 },
    Deleted(String),
}

#[derive(Debug)]
struct LanguageRecord {
    id: u64,
    event: Event,
    optional: Option<Box<Payload>>,
    result: Result<Vec<u64>, String>,
    pair: (String, u64),
    fixed: [u8; 32],
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

struct SharedNode {
    id: u64,
    label: String,
    children: Mutex<Vec<Arc<SharedNode>>>,
    parent: Mutex<Option<Weak<SharedNode>>>,
}

struct RcNode {
    id: u64,
    label: String,
    next: RefCell<Option<Rc<RcNode>>>,
    previous: RefCell<Option<std::rc::Weak<RcNode>>>,
}

struct TlsRecord {
    thread_id: usize,
    slot: usize,
    label: String,
    payload: Vec<u64>,
}

struct Fixture {
    persons: Vec<Box<Person>>,
    entities: Vec<Box<GameEntity>>,
    trees: Vec<Box<TreeNode>>,
    vectors: Vec<Box<Vec<u64>>>,
    hash_maps: Vec<Box<HashMap<String, u64>>>,
    hash_sets: Vec<Box<HashSet<u64>>>,
    btree_maps: Vec<Box<BTreeMap<u64, String>>>,
    btree_sets: Vec<Box<BTreeSet<String>>>,
    deques: Vec<Box<VecDeque<String>>>,
    linked_lists: Vec<Box<LinkedList<Payload>>>,
    binary_heaps: Vec<Box<BinaryHeap<u64>>>,
    strings: Vec<Box<String>>,
    byte_buffers: Vec<Box<Vec<u8>>>,
    language_records: Vec<Box<LanguageRecord>>,
    speakers: Vec<Box<dyn Speaker>>,
    arc_nodes: Vec<Arc<SharedNode>>,
}

type PendingFuture = Pin<Box<dyn Future<Output = u64> + Send>>;

static FIXTURE: OnceLock<Fixture> = OnceLock::new();
static FUTURES: OnceLock<Mutex<Vec<PendingFuture>>> = OnceLock::new();
static RAW_ALLOCS: OnceLock<Vec<usize>> = OnceLock::new();
static MMAPS: OnceLock<Vec<(usize, usize)>> = OnceLock::new();
static TRUTH: OnceLock<Mutex<Vec<(String, String)>>> = OnceLock::new();
static READY_THREADS: AtomicUsize = AtomicUsize::new(0);

thread_local! {
    static TLS_RECORDS: RefCell<Vec<Box<TlsRecord>>> = const { RefCell::new(Vec::new()) };
}

#[link(name = "c")]
extern "C" {
    fn malloc(size: usize) -> *mut c_void;
    fn mmap(
        addr: *mut c_void,
        len: usize,
        prot: i32,
        flags: i32,
        fd: i32,
        offset: i64,
    ) -> *mut c_void;
}

const PROT_READ: i32 = 1;
const PROT_WRITE: i32 = 2;
const MAP_PRIVATE: i32 = 2;
const MAP_ANONYMOUS: i32 = 0x20;

fn truth_hex(name: &str, address: usize) {
    TRUTH
        .get_or_init(|| Mutex::new(Vec::new()))
        .lock()
        .unwrap()
        .push((name.to_string(), format!("{:#x}", address)));
}

fn padded_string(prefix: &str, index: usize, length: usize) -> String {
    let mut value = String::with_capacity(length);
    value.push_str(&format!("{}-{:04}-", prefix, index));
    let fill = (b'a' + (index % 26) as u8) as char;
    while value.len() < length {
        value.push(fill);
    }
    value
}

fn make_person(index: usize) -> Person {
    Person {
        id: index as u64,
        name: padded_string("person", index, 48 + index % 16),
        email: padded_string("email", index, 80 + index % 24),
        tags: vec![
            padded_string("tag-a", index, 24),
            padded_string("tag-b", index, 32),
        ],
        scores: [
            index as u32,
            index.wrapping_mul(3) as u32,
            index.wrapping_mul(5) as u32,
            index.wrapping_mul(7) as u32,
            11,
            13,
            17,
            19,
        ],
        presence: match index % 3 {
            0 => Presence::Online {
                session_id: 100_000 + index as u64,
            },
            1 => Presence::Idle((index % 300) as u32),
            _ => Presence::Offline,
        },
    }
}

fn make_entity(index: usize) -> GameEntity {
    let mut attributes = HashMap::with_capacity(8);
    for slot in 0..8 {
        attributes.insert(
            padded_string("attribute", index * 10 + slot, 32),
            (index * 100 + slot) as i64,
        );
    }
    GameEntity {
        entity_id: index as u64,
        kind: padded_string("entity", index, 40),
        position: (index as f64, index as f64 * 1.5, index as f64 * -0.25),
        hp: 100 + (index % 900) as u32,
        inventory: (0..4)
            .map(|slot| padded_string("inventory", index * 10 + slot, 32))
            .collect(),
        attributes,
    }
}

fn make_tree(index: usize) -> Box<TreeNode> {
    let leaf = |value: usize, side: &str| {
        Box::new(TreeNode {
            value: value as u64,
            label: padded_string(side, value, 48),
            left: None,
            right: None,
        })
    };
    Box::new(TreeNode {
        value: index as u64,
        label: padded_string("tree-root", index, 64),
        left: Some(leaf(index * 2, "tree-left")),
        right: Some(leaf(index * 2 + 1, "tree-right")),
    })
}

fn make_payload(id: usize, prefix: &str, bytes: usize) -> Payload {
    Payload {
        id: id as u64,
        label: padded_string(prefix, id, 48),
        bytes: vec![(id % 251) as u8; bytes],
    }
}

fn build_fixture() -> Fixture {
    let persons = (0..PERSON_COUNT)
        .map(|index| Box::new(make_person(index)))
        .collect();
    let entities = (0..ENTITY_COUNT)
        .map(|index| Box::new(make_entity(index)))
        .collect();
    let trees = (0..TREE_ROOT_COUNT).map(make_tree).collect();

    let vectors = (0..VECTOR_COUNT)
        .map(|index| {
            let len = 8 + index % 48;
            Box::new(
                (0..len)
                    .map(|slot| (index * 1_000 + slot) as u64)
                    .collect(),
            )
        })
        .collect();

    let hash_maps = (0..HASH_MAP_COUNT)
        .map(|index| {
            let mut map = HashMap::with_capacity(16);
            for slot in 0..16 {
                map.insert(
                    padded_string("hash-key", index * 100 + slot, 32),
                    (index * 1_000 + slot) as u64,
                );
            }
            Box::new(map)
        })
        .collect();

    let hash_sets = (0..HASH_SET_COUNT)
        .map(|index| {
            Box::new(
                (0..32)
                    .map(|slot| (index * 1_000 + slot) as u64)
                    .collect(),
            )
        })
        .collect();

    let btree_maps = (0..BTREE_MAP_COUNT)
        .map(|index| {
            let mut map = BTreeMap::new();
            for slot in 0..24 {
                map.insert(
                    (index * 100 + slot) as u64,
                    padded_string("btree-value", index * 100 + slot, 40),
                );
            }
            Box::new(map)
        })
        .collect();

    let btree_sets = (0..BTREE_SET_COUNT)
        .map(|index| {
            Box::new(
                (0..24)
                    .map(|slot| padded_string("btree-set", index * 100 + slot, 40))
                    .collect(),
            )
        })
        .collect();

    let deques = (0..DEQUE_COUNT)
        .map(|index| {
            let mut deque = VecDeque::with_capacity(16);
            for slot in 0..16 {
                deque.push_back(padded_string("deque", index * 100 + slot, 36));
            }
            for _ in 0..5 {
                let front = deque.pop_front().unwrap();
                deque.push_back(front);
            }
            Box::new(deque)
        })
        .collect();

    let linked_lists = (0..LINKED_LIST_COUNT)
        .map(|index| {
            let mut list = LinkedList::new();
            for slot in 0..16 {
                list.push_back(make_payload(index * 100 + slot, "linked", 48 + slot));
            }
            Box::new(list)
        })
        .collect();

    let binary_heaps = (0..BINARY_HEAP_COUNT)
        .map(|index| {
            Box::new(
                (0..64)
                    .map(|slot| (index * 1_000 + slot * 17) as u64)
                    .collect(),
            )
        })
        .collect();

    let mut strings = Vec::with_capacity(
        SHORT_STRING_COUNT + MEDIUM_STRING_COUNT + LONG_STRING_COUNT,
    );
    strings.extend(
        (0..SHORT_STRING_COUNT).map(|index| Box::new(padded_string("short", index, 32))),
    );
    strings.extend(
        (0..MEDIUM_STRING_COUNT)
            .map(|index| Box::new(padded_string("medium", index, 128))),
    );
    strings.extend(
        (0..LONG_STRING_COUNT).map(|index| Box::new(padded_string("long", index, 640))),
    );

    let byte_buffers = (0..BYTE_BUFFER_COUNT)
        .map(|index| {
            let size = 128 + (index % 8) * 128;
            Box::new(vec![(index % 251) as u8; size])
        })
        .collect();

    let language_records = (0..LANGUAGE_RECORD_COUNT)
        .map(|index| {
            let event = match index % 3 {
                0 => Event::Created,
                1 => Event::Updated {
                    field: padded_string("field", index, 32),
                    version: index as u64,
                },
                _ => Event::Deleted(padded_string("deleted", index, 40)),
            };
            let result = if index % 4 == 0 {
                Err(padded_string("error", index, 64))
            } else {
                Ok((0..16).map(|slot| (index * 100 + slot) as u64).collect())
            };
            Box::new(LanguageRecord {
                id: index as u64,
                event,
                optional: Some(Box::new(make_payload(index, "optional", 96))),
                result,
                pair: (padded_string("pair", index, 48), index as u64),
                fixed: [index as u8; 32],
            })
        })
        .collect();

    let speakers: Vec<Box<dyn Speaker>> = (0..SPEAKER_COUNT)
        .map(|index| {
            if index % 2 == 0 {
                Box::new(Dog {
                    name: padded_string("dog", index, 48),
                }) as Box<dyn Speaker>
            } else {
                Box::new(Cat {
                    name: padded_string("cat", index, 48),
                }) as Box<dyn Speaker>
            }
        })
        .collect();

    let arc_nodes: Vec<Arc<SharedNode>> = (0..ARC_NODE_COUNT)
        .map(|index| {
            Arc::new(SharedNode {
                id: index as u64,
                label: padded_string("arc-node", index, 56),
                children: Mutex::new(Vec::new()),
                parent: Mutex::new(None),
            })
        })
        .collect();
    for index in 0..ARC_NODE_COUNT - 1 {
        arc_nodes[index]
            .children
            .lock()
            .unwrap()
            .push(Arc::clone(&arc_nodes[index + 1]));
        *arc_nodes[index + 1].parent.lock().unwrap() = Some(Arc::downgrade(&arc_nodes[index]));
    }

    Fixture {
        persons,
        entities,
        trees,
        vectors,
        hash_maps,
        hash_sets,
        btree_maps,
        btree_sets,
        deques,
        linked_lists,
        binary_heaps,
        strings,
        byte_buffers,
        language_records,
        speakers,
        arc_nodes,
    }
}

async fn pending_task(id: u64) -> u64 {
    std::future::pending::<()>().await;
    id
}

fn build_futures() -> Mutex<Vec<PendingFuture>> {
    Mutex::new(
        (0..FUTURE_COUNT)
            .map(|index| Box::pin(pending_task(index as u64)) as PendingFuture)
            .collect(),
    )
}

fn spawn_tls_workers() {
    for thread_id in 0..TLS_THREAD_COUNT {
        thread::Builder::new()
            .name(format!("rust-tls-{}", thread_id))
            .spawn(move || {
                TLS_RECORDS.with(|cell| {
                    let records: Vec<Box<TlsRecord>> = (0..TLS_RECORDS_PER_THREAD)
                        .map(|slot| {
                            Box::new(TlsRecord {
                                thread_id,
                                slot,
                                label: padded_string(
                                    "tls",
                                    thread_id * 1_000 + slot,
                                    48,
                                ),
                                payload: (0..64)
                                    .map(|value| {
                                        (thread_id * 1_000_000 + slot * 100 + value) as u64
                                    })
                                    .collect(),
                            })
                        })
                        .collect();
                    if let Some(first) = records.first() {
                        truth_hex(
                            &format!("tls_thread_{}_first", thread_id),
                            &**first as *const TlsRecord as usize,
                        );
                    }
                    *cell.borrow_mut() = records;
                });
                READY_THREADS.fetch_add(1, Ordering::SeqCst);
                loop {
                    TLS_RECORDS.with(|cell| black_box(cell.borrow().len()));
                    thread::park();
                }
            })
            .expect("spawn TLS fixture thread");
    }
}

fn spawn_rc_graph() {
    thread::Builder::new()
        .name("rust-rc-cycle".to_string())
        .spawn(|| {
            let nodes: Vec<Rc<RcNode>> = (0..RC_NODE_COUNT)
                .map(|index| {
                    Rc::new(RcNode {
                        id: index as u64,
                        label: padded_string("rc-node", index, 56),
                        next: RefCell::new(None),
                        previous: RefCell::new(None),
                    })
                })
                .collect();
            for index in 0..RC_NODE_COUNT {
                let next = (index + 1) % RC_NODE_COUNT;
                *nodes[index].next.borrow_mut() = Some(Rc::clone(&nodes[next]));
                *nodes[next].previous.borrow_mut() = Some(Rc::downgrade(&nodes[index]));
            }
            truth_hex("rc_first", Rc::as_ptr(&nodes[0]) as usize);
            truth_hex("rc_last", Rc::as_ptr(nodes.last().unwrap()) as usize);
            READY_THREADS.fetch_add(1, Ordering::SeqCst);
            loop {
                black_box(&nodes);
                thread::park();
            }
        })
        .expect("spawn Rc graph thread");
}

fn allocate_raw_regions() {
    RAW_ALLOCS.get_or_init(|| {
        (0..RAW_ALLOC_COUNT)
            .map(|index| {
                let ptr = unsafe { malloc(RAW_ALLOC_SIZE) };
                assert!(!ptr.is_null(), "malloc fixture block");
                unsafe { *(ptr as *mut u8) = index as u8 };
                ptr as usize
            })
            .collect()
    });
    MMAPS.get_or_init(|| {
        [65_536usize, 131_072, 262_144, 524_288]
            .iter()
            .map(|&size| {
                let ptr = unsafe {
                    mmap(
                        std::ptr::null_mut(),
                        size,
                        PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS,
                        -1,
                        0,
                    )
                };
                assert_ne!(ptr, usize::MAX as *mut c_void, "mmap fixture region");
                unsafe { *(ptr as *mut u8) = 0xA5 };
                (ptr as usize, size)
            })
            .collect()
    });
}

fn tree_requested_bytes(node: &TreeNode) -> usize {
    let mut total = size_of::<TreeNode>() + node.label.capacity();
    if let Some(left) = node.left.as_ref() {
        total += tree_requested_bytes(left);
    }
    if let Some(right) = node.right.as_ref() {
        total += tree_requested_bytes(right);
    }
    total
}

fn known_requested_bytes(fixture: &Fixture) -> usize {
    let mut total = RAW_ALLOC_COUNT * RAW_ALLOC_SIZE;
    for person in &fixture.persons {
        total += size_of::<Person>() + person.name.capacity() + person.email.capacity();
        total += person.tags.capacity() * size_of::<String>();
        total += person.tags.iter().map(String::capacity).sum::<usize>();
    }
    for entity in &fixture.entities {
        total += size_of::<GameEntity>() + entity.kind.capacity();
        total += entity.inventory.capacity() * size_of::<String>();
        total += entity.inventory.iter().map(String::capacity).sum::<usize>();
        total += entity.attributes.keys().map(String::capacity).sum::<usize>();
    }
    total += fixture
        .trees
        .iter()
        .map(|tree| tree_requested_bytes(tree))
        .sum::<usize>();
    for values in &fixture.vectors {
        total += size_of::<Vec<u64>>() + values.capacity() * size_of::<u64>();
    }
    for value in &fixture.strings {
        total += size_of::<String>() + value.capacity();
    }
    for value in &fixture.byte_buffers {
        total += size_of::<Vec<u8>>() + value.capacity();
    }
    for record in &fixture.language_records {
        total += size_of::<LanguageRecord>();
        if let Some(payload) = record.optional.as_ref() {
            total += size_of::<Payload>() + payload.label.capacity() + payload.bytes.capacity();
        }
        if let Ok(values) = record.result.as_ref() {
            total += values.capacity() * size_of::<u64>();
        }
        total += record.pair.0.capacity();
    }
    total
}

fn record_samples(fixture: &Fixture) {
    truth_hex("static_FIXTURE", std::ptr::addr_of!(FIXTURE) as usize);
    truth_hex("person_first", &*fixture.persons[0] as *const Person as usize);
    truth_hex(
        "person_last",
        &**fixture.persons.last().unwrap() as *const Person as usize,
    );
    truth_hex(
        "entity_first",
        &*fixture.entities[0] as *const GameEntity as usize,
    );
    truth_hex("tree_first", &*fixture.trees[0] as *const TreeNode as usize);
    truth_hex("vector_first_backing", fixture.vectors[0].as_ptr() as usize);
    truth_hex(
        "hash_map_first",
        &*fixture.hash_maps[0] as *const HashMap<String, u64> as usize,
    );
    truth_hex(
        "string_short_first_backing",
        fixture.strings[0].as_ptr() as usize,
    );
    truth_hex(
        "string_long_first_backing",
        fixture.strings[SHORT_STRING_COUNT + MEDIUM_STRING_COUNT].as_ptr() as usize,
    );
    truth_hex(
        "language_record_first",
        &*fixture.language_records[0] as *const LanguageRecord as usize,
    );
    truth_hex("arc_first", Arc::as_ptr(&fixture.arc_nodes[0]) as usize);
    let speaker_ptr = &*fixture.speakers[0] as *const dyn Speaker as *const ();
    truth_hex("speaker_first", speaker_ptr as usize);

    let futures = FUTURES.get().unwrap().lock().unwrap();
    let future_ptr = &*futures[0] as *const dyn Future<Output = u64> as *const ();
    truth_hex("future_first", future_ptr as usize);
    let raw = RAW_ALLOCS.get().unwrap();
    truth_hex("raw_malloc_first", raw[0]);
    let maps = MMAPS.get().unwrap();
    truth_hex("mmap_first", maps[0].0);
}

fn write_ground_truth(fixture: &Fixture) {
    let mut samples = TRUTH
        .get_or_init(|| Mutex::new(Vec::new()))
        .lock()
        .unwrap()
        .clone();
    samples.sort_by(|left, right| left.0.cmp(&right.0));
    let file = std::fs::File::create("rust-scale-ground-truth.json")
        .expect("create Rust scale ground truth");
    let mut out = BufWriter::new(file);
    writeln!(out, "{{").unwrap();
    writeln!(out, "  \"schema\": \"maze.rust-scale-ground-truth/v1\",").unwrap();
    writeln!(out, "  \"fixture\": \"20260810-complex-types-scale-live\",").unwrap();
    writeln!(out, "  \"pid\": {},", std::process::id()).unwrap();
    writeln!(out, "  \"counts\": {{").unwrap();
    let counts = [
        ("persons", PERSON_COUNT),
        ("entities", ENTITY_COUNT),
        ("tree_roots", TREE_ROOT_COUNT),
        ("tree_nodes", TREE_NODE_COUNT),
        ("vectors", VECTOR_COUNT),
        ("hash_maps", HASH_MAP_COUNT),
        ("hash_sets", HASH_SET_COUNT),
        ("btree_maps", BTREE_MAP_COUNT),
        ("btree_sets", BTREE_SET_COUNT),
        ("vec_deques", DEQUE_COUNT),
        ("linked_lists", LINKED_LIST_COUNT),
        ("binary_heaps", BINARY_HEAP_COUNT),
        ("short_strings", SHORT_STRING_COUNT),
        ("medium_strings", MEDIUM_STRING_COUNT),
        ("long_strings", LONG_STRING_COUNT),
        ("byte_buffers", BYTE_BUFFER_COUNT),
        ("language_records", LANGUAGE_RECORD_COUNT),
        ("dyn_speakers", SPEAKER_COUNT),
        ("arc_nodes", ARC_NODE_COUNT),
        ("rc_nodes", RC_NODE_COUNT),
        ("pending_futures", FUTURE_COUNT),
        ("tls_threads", TLS_THREAD_COUNT),
        ("tls_records", TLS_THREAD_COUNT * TLS_RECORDS_PER_THREAD),
        ("raw_malloc_blocks", RAW_ALLOC_COUNT),
        ("mmap_regions", 4),
    ];
    for (index, (name, count)) in counts.iter().enumerate() {
        let suffix = if index + 1 == counts.len() { "" } else { "," };
        writeln!(out, "    \"{}\": {}{}", name, count, suffix).unwrap();
    }
    writeln!(out, "  }},").unwrap();
    writeln!(out, "  \"type_sizes\": {{").unwrap();
    writeln!(out, "    \"Person\": {},", size_of::<Person>()).unwrap();
    writeln!(out, "    \"GameEntity\": {},", size_of::<GameEntity>()).unwrap();
    writeln!(out, "    \"TreeNode\": {},", size_of::<TreeNode>()).unwrap();
    writeln!(out, "    \"Payload\": {},", size_of::<Payload>()).unwrap();
    writeln!(out, "    \"LanguageRecord\": {},", size_of::<LanguageRecord>()).unwrap();
    writeln!(out, "    \"TlsRecord\": {}", size_of::<TlsRecord>()).unwrap();
    writeln!(out, "  }},").unwrap();
    writeln!(out, "  \"expectations\": {{").unwrap();
    writeln!(out, "    \"independent_allocations_min\": 10000,").unwrap();
    writeln!(
        out,
        "    \"known_requested_bytes_min\": {}",
        known_requested_bytes(fixture)
    )
    .unwrap();
    writeln!(out, "  }},").unwrap();
    writeln!(out, "  \"samples\": {{").unwrap();
    for (index, (name, value)) in samples.iter().enumerate() {
        let suffix = if index + 1 == samples.len() { "" } else { "," };
        writeln!(out, "    \"{}\": \"{}\"{}", name, value, suffix).unwrap();
    }
    writeln!(out, "  }}").unwrap();
    writeln!(out, "}}").unwrap();
    out.flush().unwrap();
}

fn main() {
    let fixture = FIXTURE.get_or_init(build_fixture);
    FUTURES.get_or_init(build_futures);
    allocate_raw_regions();
    spawn_tls_workers();
    spawn_rc_graph();
    while READY_THREADS.load(Ordering::SeqCst) != EXPECTED_READY_THREADS {
        thread::sleep(Duration::from_millis(10));
    }
    record_samples(fixture);
    write_ground_truth(fixture);

    println!("============================================================");
    println!("Rust scaled complex-types fixture ready");
    println!("PID: {}", std::process::id());
    println!("Person boxes: {}", fixture.persons.len());
    println!("Entity boxes: {}", fixture.entities.len());
    println!("Tree nodes: {}", TREE_NODE_COUNT);
    println!("Container batches: {}", VECTOR_COUNT + HASH_MAP_COUNT + HASH_SET_COUNT);
    println!("Expected independent allocations: > 10000");
    println!("Known requested bytes: {}", known_requested_bytes(fixture));
    println!(">>> READY FOR GCORE {} <<<", std::process::id());
    println!("============================================================");

    loop {
        black_box(fixture);
        thread::sleep(Duration::from_secs(3_600));
    }
}

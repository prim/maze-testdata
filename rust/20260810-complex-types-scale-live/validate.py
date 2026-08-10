#!/usr/bin/env python3
"""Validate the high-cardinality Rust complex-types fixture."""

import json
import os
import sys


EXPECTED_COUNTS = {
    "persons": 1000,
    "entities": 300,
    "tree_roots": 200,
    "tree_nodes": 600,
    "vectors": 500,
    "hash_maps": 300,
    "hash_sets": 240,
    "btree_maps": 120,
    "btree_sets": 120,
    "vec_deques": 300,
    "linked_lists": 120,
    "binary_heaps": 200,
    "short_strings": 1000,
    "medium_strings": 500,
    "long_strings": 200,
    "byte_buffers": 400,
    "language_records": 500,
    "dyn_speakers": 300,
    "arc_nodes": 200,
    "rc_nodes": 128,
    "pending_futures": 200,
    "tls_threads": 4,
    "tls_records": 512,
    "raw_malloc_blocks": 64,
    "mmap_regions": 4,
}


def flatten_edges(edges):
    pending = list(reversed(edges or []))
    while pending:
        edge = pending.pop()
        if not isinstance(edge, dict):
            continue
        yield edge
        children = edge.get("children")
        if isinstance(children, list):
            pending.extend(reversed(children))


def malloced_bytes(data):
    mallocer = data.get("overview", {}).get("memoryPool", {}).get("mallocer", {})
    value = mallocer.get("malloced") if isinstance(mallocer, dict) else None
    return value if isinstance(value, (int, float)) else None


def physical_block_count(data):
    items = data.get("items")
    if not isinstance(items, list):
        return None
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        amount = item.get("amount", 0)
        if isinstance(amount, int) and amount > 0:
            total += amount
    return total


def find_vec_len(edges, marker):
    matches = []
    for edge in edges:
        if edge.get("kind") != "vec":
            continue
        if marker not in edge.get("type_name", ""):
            continue
        length = edge.get("len")
        if isinstance(length, int):
            matches.append(length)
    return max(matches) if matches else None


def validate(data, truth):
    assert truth.get("schema") == "maze.rust-scale-ground-truth/v1"
    assert truth.get("counts") == EXPECTED_COUNTS, (
        "fixture counts changed without updating the contract"
    )

    expectations = truth.get("expectations", {})
    minimum_blocks = expectations.get("independent_allocations_min")
    minimum_bytes = expectations.get("known_requested_bytes_min")
    assert isinstance(minimum_blocks, int) and minimum_blocks >= 10000
    assert isinstance(minimum_bytes, int) and minimum_bytes > 0

    rust = data.get("rust")
    assert isinstance(rust, dict), "missing rust result block"
    capability = rust.get("capability", {})
    assert rust.get("detected") is True, "Rust capability was not detected"
    assert capability.get("rust_profile") == "locked", capability
    assert capability.get("rust_dwarf_available") is True, capability
    assert capability.get("allocator_profile") == "glibc-ptmalloc", capability
    assert rust.get("toolchain") == "1.97.1", rust.get("toolchain")

    blocks = physical_block_count(data)
    assert blocks is not None, "missing top-level items for physical allocation count"
    assert blocks >= minimum_blocks, "physical blocks %d < fixture lower bound %d" % (
        blocks,
        minimum_blocks,
    )
    malloced = malloced_bytes(data)
    assert malloced is not None, "missing ptmalloc malloced byte count"
    assert malloced >= minimum_bytes, "malloced %d < known requested lower bound %d" % (
        malloced,
        minimum_bytes,
    )

    heap_edges = rust.get("heap_edges")
    assert isinstance(heap_edges, list) and heap_edges, "missing typed Rust heap edges"
    edges = list(flatten_edges(heap_edges))

    expected_vecs = {
        "Box<maze_rust_complex_scale::Person": EXPECTED_COUNTS["persons"],
        "Box<maze_rust_complex_scale::GameEntity": EXPECTED_COUNTS["entities"],
        "Box<maze_rust_complex_scale::TreeNode": EXPECTED_COUNTS["tree_roots"],
        "Box<alloc::vec::Vec<u64": EXPECTED_COUNTS["vectors"],
        "Box<std::collections::hash::map::HashMap": EXPECTED_COUNTS["hash_maps"],
        "Box<std::collections::hash::set::HashSet": EXPECTED_COUNTS["hash_sets"],
        "Box<alloc::collections::btree::map::BTreeMap": EXPECTED_COUNTS["btree_maps"],
        "Box<alloc::collections::btree::set::BTreeSet": EXPECTED_COUNTS["btree_sets"],
        "Box<alloc::collections::vec_deque::VecDeque": EXPECTED_COUNTS["vec_deques"],
        "Box<alloc::collections::linked_list::LinkedList": EXPECTED_COUNTS["linked_lists"],
        "Box<alloc::collections::binary_heap::BinaryHeap": EXPECTED_COUNTS["binary_heaps"],
        "Box<alloc::string::String": (
            EXPECTED_COUNTS["short_strings"]
            + EXPECTED_COUNTS["medium_strings"]
            + EXPECTED_COUNTS["long_strings"]
        ),
        "Box<alloc::vec::Vec<u8": EXPECTED_COUNTS["byte_buffers"],
        "Box<maze_rust_complex_scale::LanguageRecord": EXPECTED_COUNTS[
            "language_records"
        ],
        "Box<dyn maze_rust_complex_scale::Speaker": EXPECTED_COUNTS["dyn_speakers"],
        "Arc<maze_rust_complex_scale::SharedNode": EXPECTED_COUNTS["arc_nodes"],
        "Rc<maze_rust_complex_scale::RcNode": EXPECTED_COUNTS["rc_nodes"],
        "dyn core::future::future::Future": EXPECTED_COUNTS["pending_futures"],
    }
    for marker, expected in expected_vecs.items():
        actual = find_vec_len(edges, marker)
        assert actual == expected, "%s len=%r, want %d" % (marker, actual, expected)

    kinds = {edge.get("kind") for edge in edges}
    for kind in (
        "arc",
        "array",
        "box",
        "btree_map",
        "dyn_trait",
        "enum",
        "generator",
        "hash_map",
        "hash_set",
        "option",
        "rc",
        "string",
        "struct",
        "vec",
        "vec_deque",
        "weak",
    ):
        assert kind in kinds, "typed Rust walk did not publish kind %s" % kind

    owned = sum(1 for edge in edges if edge.get("owned_unique"))
    assert owned >= 2000, "only %d proven owned Rust allocations" % owned
    assert rust.get("heap_truncated") is True, (
        "large fixture must disclose bounded traversal"
    )

    print(
        "PASS: %d physical blocks, %d typed edges, %d owned allocations"
        % (blocks, len(edges), owned)
    )
    print("PASS: all high-cardinality container batch lengths match ground truth")
    return True


def main(argv):
    if len(argv) not in (2, 3):
        print(
            "usage: validate.py <maze-result.json> [rust-scale-ground-truth.json]",
            file=sys.stderr,
        )
        return 2
    result_path = argv[1]
    truth_path = argv[2] if len(argv) == 3 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "rust-scale-ground-truth.json",
    )
    with open(result_path, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    with open(truth_path, "r", encoding="utf-8") as stream:
        truth = json.load(stream)
    validate(data, truth)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

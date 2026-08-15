#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os

# Maze Elixir 1.18.4 / OTP 27.3.4.1 fixture validator.
#
# The fixture runs a real Elixir 1.18.4 process on the reproduced OTP 27.3.4.1
# beam.smp (Build ID f94f08a81260ba544812ca2d62f479a794dc7c77). It must select
# the embedded v28 layout without MAZE_ERLANG_LAYOUT, publish flavor=elixir
# 1.18.4 from authoritative module-literal evidence, and reach the full v28
# contract: every BEAM domain complete, an exact global term graph, and
# allocator ownership reconciled to the captured core's exact archived libc.
#
# The fixture writes a machine-readable ground truth (ground-truth.txt next to
# this validator, generated at capture time under tmp/elixir-fixture) which is
# reconciled here against the summary evidence Maze exposes in maze-result.json.
# Small graph terms (bignum/struct/map/list/tuple/closure/sub-binary) live
# inside the persistent-term map and are verified through Local API search /
# object queries in the README/dev-log reconciliation; the summary JSON can only
# carry the bounded key/value texts and shared-binary inventory.

EXPECTED_BUILD_ID = "f94f08a81260ba544812ca2d62f479a794dc7c77"
EXPECTED_ELIXIR_VERSION = "1.18.4"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


REQUIRED_TRUTH_KEYS = [
    "elixir_version", "build_info_otp", "erlang_otp", "erts", "bignum",
    "binary_size", "small_slice16_size", "small_slice16_referenced_size",
    "sub_binary100_size", "sub_binary100_referenced_size",
    "struct_name", "struct_value", "closure_result", "atom", "ets_rows",
    "process_count", "atom_count", "elixir_system_loaded", "elixir_kernel_loaded",
    "worker_pid", "supervisor_pid", "fixture_pid", "worker_mailbox_size",
    "worker_link_count", "fixture_mailbox_size", "fixture_monitor_count",
    "fixture_timer_set",
]


def load_ground_truth():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "ground-truth.txt"),
        "tmp/elixir-fixture/ground-truth.txt",
    ]
    for path in candidates:
        if os.path.isfile(path):
            values = {}
            with open(path) as source:
                for raw in source:
                    line = raw.strip()
                    if "=" in line:
                        key, _, value = line.partition("=")
                        values[key.strip()] = value.strip()
            if not values:
                raise AssertionError("ground-truth file is empty: %s" % path)
            missing = [key for key in REQUIRED_TRUTH_KEYS if key not in values]
            if missing:
                raise AssertionError("ground-truth file %s missing keys: %s" % (path, missing))
            return values
    raise AssertionError("no persisted fixture ground-truth file found (expected ground-truth.txt or tmp)")


def evidence_has(runtime, needle):
    for item in runtime.get("flavor_evidence") or []:
        if item == needle:
            return True
    return False


def pid_short(pid):
    # "#PID<0.112.0>" -> "<0.112.0>"
    if pid and pid.startswith("#PID<") and pid.endswith(">"):
        return pid[len("#PID"):]
    return pid


def validate(data):
    runtime = data.get("erlang") or {}
    layout = runtime.get("layout") or {}
    features = layout.get("features") or {}
    truth = load_ground_truth()

    # --- Runtime identity / embedded layout ---
    require(runtime.get("detected") is True, "BEAM runtime was not detected")
    require(runtime.get("metadata_ready") is True, "ERTS metadata is not ready")
    require(runtime.get("native_analyzed") is True, "native memory was not analyzed")
    require(runtime.get("support_level") == "L4", "expected Erlang L4 support")
    require(runtime.get("analysis_mode") == "global-term-graph", "wrong analysis mode")
    require(runtime.get("build_id") == EXPECTED_BUILD_ID, "unexpected beam.smp Build ID")
    require(runtime.get("otp_release") == "27", "unexpected OTP release")
    require(runtime.get("erts_version") == "15.2.7", "unexpected ERTS version")
    require(
        runtime.get("manifest_path", "").startswith("embedded:otp-27.3.4.1"),
        "OTP 27 layout was not selected from the Maze binary",
    )
    require(EXPECTED_BUILD_ID in runtime.get("manifest_path", ""), "wrong embedded manifest Build ID")
    require(layout.get("schema") == "maze-erlang-layout-v28", "unexpected layout schema")
    require(layout.get("producer") == "maze-erlang-dwarf-v29", "unexpected layout producer")
    require(features.get("native_context_roots") is True, "native roots feature missing")

    # --- Elixir flavor identity from authoritative module-literal evidence ---
    require(runtime.get("flavor") == "elixir", "Elixir flavor was not published")
    require(runtime.get("flavor_version") == EXPECTED_ELIXIR_VERSION, "wrong Elixir version")
    require(runtime.get("flavor_status") == "verified", "Elixir flavor not verified")
    require(not runtime.get("flavor_diagnostic"), "unexpected flavor diagnostic")
    require(evidence_has(runtime, "module-literal:Elixir.System@curr"), "missing Elixir.System module-literal evidence")
    require(evidence_has(runtime, "module-literal:Elixir.Kernel@curr"), "missing Elixir.Kernel module-literal evidence")
    require(
        evidence_has(runtime, "literal:Elixir.System:version=%s" % EXPECTED_ELIXIR_VERSION),
        "missing Elixir.System version-literal evidence",
    )

    # --- Graph completeness (v28 exact contract) ---
    require(runtime.get("graph_status") == "complete", "global graph is incomplete")
    require(runtime.get("term_graph_status") == "complete", "term graph is incomplete")
    require(runtime.get("term_graph_precision") == "exact", "term graph precision must be exact")
    nodes = runtime.get("term_node_count", 0)
    edges = runtime.get("term_edge_count", 0)
    roots = runtime.get("term_root_record_count", 0)
    require(nodes >= 150000, "too few recovered term nodes: %s" % nodes)
    require(edges >= 200000, "too few recovered term edges: %s" % edges)
    require(roots >= 100000, "too few authorized root records: %s" % roots)
    require(runtime.get("term_unsupported_count", 0) == 0, "unsupported terms must be zero")
    require(runtime.get("term_reachable_node_upper_bound") == nodes, "upper reachability mismatch")
    require(runtime.get("term_definitely_reachable_node_count") == nodes, "exact graph must be definitely reachable")

    # --- All v28 domains must be complete ---
    # Every *_status field (atom, process, message, signal, scheduler, ETS,
    # module literal, persistent/global/lambda literal, port, timer, link/
    # monitor, distribution, NIF, allocator, off-heap, term root and
    # reachability) must be complete; flavor_status is the identity status and
    # is "verified" instead.
    non_complete = []
    for key, value in runtime.items():
        if key.endswith("_status") and isinstance(value, str):
            if key == "flavor_status":
                continue
            if value != "complete":
                non_complete.append("%s=%r" % (key, value))
    require(not non_complete, "incomplete BEAM domain statuses: %s" % ", ".join(non_complete))

    require(runtime.get("process_count", 0) >= 40, "process inventory unexpectedly small")
    require(runtime.get("atom_count", 0) >= 18000, "atom inventory unexpectedly small")
    require(runtime.get("ets_table_count", 0) >= 10, "ETS inventory unexpectedly small")
    require(runtime.get("shared_binary_count", 0) >= 100, "shared Binary inventory unexpectedly small")
    require(runtime.get("persistent_term_count", 0) >= 20, "persistent-term inventory unexpectedly small")
    require(runtime.get("allocator_carrier_count", 0) >= 20, "allocator carriers missing")

    # --- Allocator ownership must reconcile against the exact archived libc ---
    known_size = data.get("known_size", 0)
    allocator_covered = runtime.get("allocator_native_covered_bytes", 0)
    require(known_size > 50 * 1024 * 1024, "BEAM semantic memory was excluded from known_size")
    require(
        known_size == allocator_covered,
        "known_size does not match authoritative BEAM allocator coverage",
    )

    # --- Fixture ground truth reconciliation (exact object binding) ---
    # Identity / version / ERTS must match the persisted capture-time truth.
    require(truth["elixir_version"] == EXPECTED_ELIXIR_VERSION, "ground truth Elixir version mismatch")
    require(truth["build_info_otp"] == "27" and truth["erlang_otp"] == "27", "ground truth OTP release mismatch")
    require(truth["erts"] == "15.2.7", "ground truth ERTS mismatch")
    require(truth["elixir_system_loaded"] == "true", "ground truth Elixir.System not loaded")
    require(truth["elixir_kernel_loaded"] == "true", "ground truth Elixir.Kernel not loaded")

    atom_names = [atom.get("name") for atom in runtime.get("atoms") or []]
    for want in ["MazeFixture", "MazeWorker", "MazeSupervisor", "maze_elixir_ready",
                 "elixir_maze_atom", "elixir_fixture_sentinel", "maze_ets", "maze"]:
        require(want in atom_names, "known atom %r missing from atom table" % want)

    # Exact ETS table: name, row count and owner process must match ground truth.
    fixture_pid = pid_short(truth["fixture_pid"])
    maze_ets = None
    for table in runtime.get("ets_tables") or []:
        if table.get("name_text") == "maze_ets":
            maze_ets = table
    require(maze_ets is not None, "named ETS table maze_ets missing (name_text)")
    require(maze_ets.get("object_count") == int(truth["ets_rows"]),
            "maze_ets rows=%r, want %s" % (maze_ets.get("object_count"), truth["ets_rows"]))
    require(int(truth["ets_rows"]) == 3, "ground truth maze_ets rows is not 3")
    require(maze_ets.get("owner_pid") == fixture_pid,
            "maze_ets owner_pid=%r, want fixture %r" % (maze_ets.get("owner_pid"), fixture_pid))

    # Exact worker process: PID, suspended mailbox length, link count and
    # target-monitor evidence (the fixture monitors it).
    worker_pid = pid_short(truth["worker_pid"])
    worker = None
    for process in runtime.get("processes") or []:
        if process.get("pid") == worker_pid:
            worker = process
    require(worker is not None, "worker process %r missing" % worker_pid)
    require(worker.get("message_queue_length") == int(truth["worker_mailbox_size"]),
            "worker mailbox=%r, want %s" % (worker.get("message_queue_length"), truth["worker_mailbox_size"]))
    require(int(truth["worker_mailbox_size"]) == 3, "ground truth worker mailbox is not 3")
    require(worker.get("link_count") == int(truth["worker_link_count"]),
            "worker link_count=%r, want %s" % (worker.get("link_count"), truth["worker_link_count"]))
    require(worker.get("monitor_target_count") == 1,
            "worker must be a monitor target, got monitor_target_count=%r" % worker.get("monitor_target_count"))

    # Exact fixture (capturing) process: 2 queued mailbox messages, 1 outgoing
    # monitor (it monitors the worker) and a live timer.
    fixture_pid = pid_short(truth["fixture_pid"])
    fixture = None
    for process in runtime.get("processes") or []:
        if process.get("pid") == fixture_pid:
            fixture = process
    require(fixture is not None, "fixture process %r missing" % fixture_pid)
    require(fixture.get("message_queue_length") == int(truth["fixture_mailbox_size"]),
            "fixture mailbox=%r, want %s" % (fixture.get("message_queue_length"), truth["fixture_mailbox_size"]))
    require(int(truth["fixture_mailbox_size"]) == 2, "ground truth fixture mailbox is not 2")
    require(fixture.get("monitor_origin_count") == 1,
            "fixture must originate one monitor, got monitor_origin_count=%r" % fixture.get("monitor_origin_count"))
    require(bool(fixture.get("timer")), "fixture process must hold a live timer")
    require(truth["fixture_monitor_count"] == "1", "ground truth fixture monitor count is not 1")
    require(truth["fixture_timer_set"] == "true", "ground truth fixture timer not set")
    require(runtime.get("timer_count", 0) >= 10, "timer inventory unexpectedly small")

    # Supervisor process must exist (link_count >= 1).
    supervisor_pid = pid_short(truth["supervisor_pid"])
    require(any(process.get("pid") == supervisor_pid for process in runtime.get("processes") or []),
            "supervisor process %r missing" % supervisor_pid)

    # Ground-truth constants must themselves hold.
    require(truth["bignum"] == "123456789012345678901234567890", "ground truth bignum mismatch")
    require(truth["struct_name"] == "maze" and truth["struct_value"] == "42", "ground truth struct mismatch")
    require(truth["closure_result"] == "123456789012345678901234567933", "ground truth closure result mismatch")
    require(truth["atom"] == "elixir_fixture_sentinel", "ground truth sentinel atom mismatch")

    # Process count binds exactly; atom count grew slightly between the
    # pre-READY ground truth and the captured core, so assert the captured count
    # is >= truth with a small documented bounded delta.
    require(runtime.get("process_count") == int(truth["process_count"]),
            "process_count=%r, want ground truth %s" % (runtime.get("process_count"), truth["process_count"]))
    truth_atoms = int(truth["atom_count"])
    require(runtime.get("atom_count", 0) >= truth_atoms, "atom_count below capture-time ground truth")
    require(runtime.get("atom_count", 0) - truth_atoms <= 64,
            "atom_count grew more than the bounded 64-atom delta (%r vs %d)" % (runtime.get("atom_count"), truth_atoms))

    # The 8000-byte shared Binary must appear exactly once and be referenced by
    # the suspended worker and a module/persistent-term literal area.
    shared_binaries = runtime.get("shared_binaries") or []
    big_binaries = [binary for binary in shared_binaries if binary.get("payload_bytes") == 8000]
    require(len(big_binaries) == 1, "expected exactly one 8000-byte shared Binary, got %d" % len(big_binaries))
    big_binary = big_binaries[0]
    require(big_binary.get("bin_ref_count", 0) >= 1, "8000-byte Binary has no BinRef")
    require(worker_pid in (big_binary.get("referrer_processes") or []),
            "8000-byte Binary is not referenced by the worker process")
    require(bool(big_binary.get("referrer_literal_areas")) or bool(big_binary.get("referrer_literals")),
            "8000-byte Binary is not referenced by a literal area")

    # Binary / slice ground-truth constants. OTP 27 binary_part/3
    # (erts_bif_binary.c -> erts_build_sub_bitstring) materializes slices <=
    # ERL_ONHEAP_BITS_LIMIT (64 bytes) as a HEAP_BITSTRING, so the 16-byte slice
    # is a detached heap binary in the core (creation-time referenced size 128 =
    # 16 bytes in bits). The 100-byte slice stays a genuine sub-bits view;
    # referenced_byte_size=8000 proves it references the 8000-byte refc Binary.
    require(truth["binary_size"] == "8000", "ground truth binary size is not 8000")
    require(truth["small_slice16_size"] == "16", "ground truth 16B small-slice size mismatch")
    require(truth["small_slice16_referenced_size"] == "128",
            "ground truth 16B small-slice referenced size must record the detached heap-bitstring allocation (128 bits)")
    require(truth["sub_binary100_size"] == "100", "ground truth 100B sub-binary size mismatch")
    require(truth["sub_binary100_referenced_size"] == "8000",
            "ground truth 100B sub-binary referenced size is not 8000")

    # The persistent_term key must be the exact fixture key.
    require(any(area.get("key_text") == "{maze, persistent}" for area in runtime.get("persistent_term_areas") or []),
            "persistent_term exact key {maze, persistent} missing")

    # --- Module literal registry must carry curr Elixir.System and Kernel ---
    curr_modules = set()
    for area in runtime.get("module_literal_areas") or []:
        for reference in area.get("references") or []:
            if reference.get("instance") == "curr":
                curr_modules.add(reference.get("module_name"))
    require("Elixir.System" in curr_modules, "curr Elixir.System module literal missing")
    require("Elixir.Kernel" in curr_modules, "curr Elixir.Kernel module literal missing")

    print(
        "Elixir %s / OTP 27 fixture passed: build=%s nodes=%d edges=%d roots=%d known=%d flavor=%s"
        % (EXPECTED_ELIXIR_VERSION, EXPECTED_BUILD_ID, nodes, edges, roots, known_size, runtime.get("flavor_version"))
    )
    return True

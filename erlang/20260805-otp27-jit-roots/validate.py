#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function


EXPECTED_BUILD_ID = "c3db37cbc86ec25b96b6e69b4b52ea22e7c20bc1"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate(data):
    runtime = data.get("erlang") or {}
    layout = runtime.get("layout") or {}
    features = layout.get("features") or {}

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
    require(layout.get("schema") == "maze-erlang-layout-v28", "unexpected layout schema")
    require(layout.get("producer") == "maze-erlang-dwarf-v29", "unexpected layout producer")
    require(features.get("native_context_roots") is True, "native roots feature missing")

    require(runtime.get("graph_status") == "complete", "global graph is incomplete")
    require(runtime.get("term_graph_status") == "complete", "term graph is incomplete")
    require(runtime.get("term_graph_precision") == "conservative", "wrong graph precision")
    nodes = runtime.get("term_node_count", 0)
    edges = runtime.get("term_edge_count", 0)
    roots = runtime.get("term_root_record_count", 0)
    require(nodes >= 40000, "too few recovered term nodes: %s" % nodes)
    require(edges >= 60000, "too few recovered term edges: %s" % edges)
    require(roots >= 25000, "too few authorized root records: %s" % roots)
    require(runtime.get("term_exact_root_record_count", 0) > 20000, "exact roots missing")
    require(runtime.get("term_conservative_root_record_count", 0) > 0, "native roots missing")
    require(runtime.get("term_reachable_node_upper_bound") == nodes, "upper reachability mismatch")
    require(runtime.get("term_definitely_reachable_node_count") == nodes, "ordinary-JIT graph should be definitely reachable")

    require(runtime.get("scheduler_inventory_status") == "complete", "scheduler inventory incomplete")
    require(runtime.get("scheduler_root_status") == "complete", "scheduler roots incomplete")
    require(runtime.get("scheduler_root_precision") == "conservative", "scheduler roots must expose conservative precision")
    require(runtime.get("active_scheduler_count", 0) >= 1, "ordinary JIT scheduler was not active")
    require(runtime.get("active_nif_scheduler_count", 0) == 0, "unexpected active NIF scheduler")
    require(
        runtime.get("scheduler_execution_extent_count") == runtime.get("active_scheduler_count"),
        "active JIT execution extents are incomplete",
    )

    for field in [
        "atom_table_status",
        "process_scan_status",
        "message_queue_scan_status",
        "signal_queue_scan_status",
        "ets_inventory_status",
        "ets_object_scan_status",
        "module_literal_scan_status",
        "persistent_term_scan_status",
        "global_literal_scan_status",
        "lambda_literal_scan_status",
        "port_inventory_status",
        "timer_inventory_status",
        "link_monitor_inventory_status",
        "distribution_inventory_status",
        "nif_resource_inventory_status",
        "allocator_inventory_status",
        "allocator_carrier_scan_status",
        "allocator_ownership_status",
        "off_heap_scan_status",
    ]:
        require(runtime.get(field) == "complete", "%s is not complete" % field)

    require(runtime.get("process_count", 0) >= 40, "process inventory unexpectedly small")
    require(runtime.get("atom_count", 0) >= 9000, "atom inventory unexpectedly small")
    require(runtime.get("ets_table_count", 0) >= 10, "ETS inventory unexpectedly small")
    require(runtime.get("nif_resource_count", 0) >= 1, "NIF resource inventory missing")
    require(runtime.get("allocator_carrier_count", 0) >= 20, "allocator carriers missing")

    known_size = data.get("known_size", 0)
    allocator_covered = runtime.get("allocator_native_covered_bytes", 0)
    require(known_size > 50 * 1024 * 1024, "BEAM semantic memory was excluded from known_size")
    require(
        known_size == allocator_covered,
        "known_size does not match authoritative BEAM allocator coverage",
    )

    print(
        "OTP 27 JIT fixture passed: nodes=%d edges=%d roots=%d known=%d manifest=%s"
        % (nodes, edges, roots, known_size, runtime.get("manifest_path"))
    )
    return True

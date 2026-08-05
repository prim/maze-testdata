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
    require(layout.get("features", {}).get("tagless_nif_discovery") is True, "tagless NIF discovery feature missing")

    require(runtime.get("graph_status") == "complete", "global graph is incomplete")
    require(runtime.get("term_graph_status") == "complete", "term graph is incomplete")
    require(runtime.get("term_graph_precision") == "conservative", "wrong graph precision")
    nodes = runtime.get("term_node_count", 0)
    edges = runtime.get("term_edge_count", 0)
    roots = runtime.get("term_root_record_count", 0)
    definite = runtime.get("term_definitely_reachable_node_count", 0)
    require(nodes >= 250000, "too few recovered term nodes: %s" % nodes)
    require(edges >= 450000, "too few recovered term edges: %s" % edges)
    require(roots >= 190000, "too few authorized root records: %s" % roots)
    require(runtime.get("term_exact_root_record_count", 0) >= 190000, "exact roots missing")
    require(runtime.get("term_conservative_root_record_count", 0) >= 8, "native conservative roots missing")
    require(runtime.get("term_reachable_node_upper_bound") == nodes, "upper reachability mismatch")
    require(definite == nodes - 3, "expected three conservative candidate-only nodes")

    require(runtime.get("scheduler_inventory_status") == "complete", "scheduler inventory incomplete")
    require(runtime.get("scheduler_root_status") == "complete", "scheduler roots incomplete")
    require(runtime.get("scheduler_root_precision") == "conservative", "scheduler precision mismatch")
    require(runtime.get("active_scheduler_count") == 3, "expected three active schedulers")
    require(runtime.get("active_nif_scheduler_count") == 3, "expected three active NIF schedulers")
    require(runtime.get("scheduler_execution_extent_count") == 3, "NIF execution extents incomplete")
    require(runtime.get("scheduler_register_scanned_words") == 3, "published X arity mismatch")
    require(runtime.get("scheduler_register_pointer_count") == 3, "published X roots mismatch")
    require(runtime.get("scheduler_native_register_pointer_count") == 2, "native GPR roots mismatch")
    require(runtime.get("scheduler_native_stack_pointer_count") == 6, "native C-stack roots mismatch")
    require(runtime.get("scheduler_native_register_candidate_count", 0) > 2, "GPR candidates missing")
    require(runtime.get("scheduler_native_stack_candidate_count", 0) > 6, "C-stack candidates missing")

    require(runtime.get("nif_resource_inventory_status") == "complete", "NIF resource inventory incomplete")
    require(runtime.get("nif_resource_root_scan_status") == "complete", "NIF roots incomplete")
    require(runtime.get("nif_resource_type_count", 0) >= 7, "NIF resource types missing")
    require(runtime.get("nif_resource_count") == 4, "NIF resource count mismatch")
    require(runtime.get("nif_resource_monitor_count") == 1, "NIF resource monitor reconciliation mismatch")
    require(runtime.get("nif_environment_count") == 4, "NIF environment count mismatch")
    require(runtime.get("active_nif_environment_count") == 3, "active NIF environment count mismatch")
    require(runtime.get("nif_environment_fragment_count", 0) >= 1600, "NIF fragments missing")
    require(runtime.get("nif_environment_fragment_bytes", 0) >= 2500000, "NIF fragment bytes missing")
    require(runtime.get("nif_environment_temporary_object_count") == 4, "temporary NIF objects mismatch")
    require(runtime.get("nif_environment_off_heap_header_count", 0) >= 5, "NIF off-heap roots missing")
    require(runtime.get("native_allocation_tag_count", 0) >= 130, "native allocation tags missing")

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
        "allocator_inventory_status",
        "allocator_carrier_scan_status",
        "allocator_ownership_status",
        "off_heap_scan_status",
    ]:
        require(runtime.get(field) == "complete", "%s is not complete" % field)

    known_size = data.get("known_size", 0)
    allocator_covered = runtime.get("allocator_native_covered_bytes", 0)
    require(known_size > 50 * 1024 * 1024, "BEAM semantic memory was excluded from known_size")
    require(
        known_size == allocator_covered,
        "known_size does not match authoritative BEAM allocator coverage",
    )

    print(
        "OTP 27 active-NIF fixture passed: nodes=%d edges=%d roots=%d definite=%d known=%d manifest=%s"
        % (nodes, edges, roots, definite, known_size, runtime.get("manifest_path"))
    )
    return True

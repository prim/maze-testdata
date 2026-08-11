#!/usr/bin/env python3
from __future__ import print_function

import os
import re


EXPECTED_TYPES = {
    "C# GraphNode": 64,
    "C# SharedChild": 1,
    "C# FixtureValue": 32,
    "C# StringHolder": 24,
    "C# ArrayHolder": 1,
    "C# LargeObjectHolder": 3,
    "C# PinnedObjectHolder": 4,
    "C# GenericBox<System.Int32>": 11,
    "C# NestedContainer+NestedNode": 7,
    "C# FinalizableObject": 13,
    "C# BlockingFinalizer": 1,
    "C# FinalizerQueueRoot": 1,
    "C# DependentKey": 1,
    "C# DependentValue": 1,
    "C# HandleRootHolder": 1,
    "C# ThreadRootHolder": 1,
    "C# FixtureException": 1,
    "C# AsyncStatePayload": 1,
    "C# NativeAllocationHolder": 1,
    "C# MultiRootHolder": 2,
    "C# MultiRootPayload": 1,
    "C# CollectiblePayload": 2,
    "C# MonitorFixtureLock": 1,
    "C# FixtureState": 1,
}


def read_required_file(name):
    path = os.environ.get(name, "")
    if not path:
        raise AssertionError("%s is not set by testdata/run_test.py" % name)
    with open(path, "r") as source:
        return source.read()


def validate_case(
    data,
    expect_server,
    expected_runtime_major=10,
    expect_single_file=False,
    expected_publish_kind="framework-dependent",
    expect_ready_to_run=False,
    expect_channels=False,
):
    dotnet = data.get("dotnet") or {}
    summary = data.get("summary") or {}
    items = data.get("items") or []
    indexed = {}
    for item in items:
        indexed.setdefault(item.get("type", ""), []).append(item)

    assert dotnet.get("mode") == "full", dotnet
    assert dotnet.get("capture_backend") == "createdump-full", dotnet
    assert dotnet.get("publish_kind") == expected_publish_kind, dotnet
    assert bool(dotnet.get("ready_to_run")) is expect_ready_to_run, dotnet
    assert dotnet.get("helper_version") == "maze-clr/1.29", dotnet
    assert dotnet.get("helper_elapsed_millis", 0) > 0, dotnet
    assert dotnet.get("helper_peak_rss_bytes", 0) > 0, dotnet
    assert dotnet.get("import_elapsed_millis", 0) > 0, dotnet
    assert dotnet.get("snapshot_bytes", 0) > 0, dotnet
    assert dotnet.get("runtime_count") == 1, dotnet
    assert dotnet.get("object_count", 0) > 0, dotnet
    assert dotnet.get("reference_count", 0) > 0, dotnet
    assert dotnet.get("root_count", 0) > 0, dotnet
    assert dotnet.get("detail_count", 0) > dotnet.get("object_count", 0), dotnet
    assert dotnet.get("values_included") is True, dotnet
    assert dotnet.get("detail_truncated") is False, dotnet
    assert dotnet.get("detail_dropped") == 0, dotnet
    assert dotnet.get("detail_errors") == 0, dotnet
    assert dotnet.get("string_object_count", 0) > 24, dotnet
    assert dotnet.get("string_indexed_count") == dotnet.get("string_object_count"), dotnet
    assert dotnet.get("string_index_complete") is True, dotnet
    assert dotnet.get("container_object_count", 0) > 0, dotnet
    assert dotnet.get("container_indexed_count") == dotnet.get("container_object_count"), dotnet
    assert dotnet.get("container_index_complete") is True, dotnet
    assert dotnet.get("field_indexed_count", 0) > dotnet.get("object_count", 0), dotnet
    assert 0 < dotnet.get("field_object_count", 0) <= dotnet.get("object_count", 0), dotnet
    assert dotnet.get("field_truncated_objects") == 0, dotnet
    assert dotnet.get("field_completeness_known") is True, dotnet
    assert dotnet.get("field_index_complete") is True, dotnet
    assert dotnet.get("static_indexed_count", 0) > 0, dotnet
    assert dotnet.get("static_initialized_count", 0) > 0, dotnet
    assert dotnet.get("static_uninitialized_count", 0) > 0, dotnet
    assert dotnet.get("static_initialized_count") + dotnet.get(
        "static_uninitialized_count"
    ) == dotnet.get("static_indexed_count"), dotnet
    assert 0 <= dotnet.get("static_unsupported_count", -1) <= dotnet.get(
        "static_indexed_count"
    ), dotnet
    assert dotnet.get("static_index_complete") is True, dotnet
    assert 0 < len(dotnet.get("static_samples") or []) <= 256, dotnet
    assert dotnet.get("shallow_bytes", 0) > 300000, dotnet
    assert dotnet.get("gc_committed_bytes", 0) > 0, dotnet
    assert dotnet.get("gc_reserved_bytes", 0) >= dotnet.get("gc_committed_bytes", 0), dotnet
    assert 0 < dotnet.get("reachable_object_count", 0) <= dotnet.get("object_count", 0), dotnet
    assert 0 < dotnet.get("reachable_bytes", 0) <= dotnet.get("shallow_bytes", 0), dotnet
    assert dotnet.get("dominator_object_count") == dotnet.get("reachable_object_count"), dotnet
    assert dotnet.get("root_path_limit") == 4, dotnet
    assert dotnet.get("root_path_depth") == 128, dotnet

    runtimes = dotnet.get("runtimes") or []
    runtime = runtimes[0]
    assert runtime.get("product_version", "").startswith("%d." % expected_runtime_major), runtime
    assert bool(runtime.get("is_single_file")) is expect_single_file, runtime
    assert bool(runtime.get("server_gc")) is expect_server, runtime
    if expect_server:
        assert runtime.get("logical_heaps", 0) >= 2, runtime
    else:
        assert runtime.get("logical_heaps") == 1, runtime

    assert dotnet.get("module_metadata_complete") is True, dotnet
    modules = dotnet.get("modules") or []
    assert dotnet.get("module_count") == len(modules) > 0, dotnet
    assert runtime.get("modules") == len(modules), (runtime, modules)
    module_basenames = set()
    mvid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    for module in modules:
        assert module.get("runtime_id") == 0, module
        assert module.get("address", 0) > 0, module
        assert module.get("name"), module
        assert module.get("is_pe_file") is True, module
        assert module.get("size", 0) > 0, module
        assert module.get("metadata_address", 0) > 0, module
        assert module.get("metadata_length", 0) > 0, module
        assert mvid_pattern.match(module.get("mvid", "")), module
        if module.get("file_bytes", 0) or module.get("file_sha256"):
            assert module.get("file_bytes", 0) > 0, module
            assert re.match(r"^[0-9a-f]{64}$", module.get("file_sha256", "")), module
        else:
            assert expect_single_file, module
        module_basenames.add(os.path.basename(module.get("name", "")))
    assert "System.Private.CoreLib.dll" in module_basenames, module_basenames
    assert "MazeDotnetFixture.dll" in module_basenames, module_basenames

    for name, expected in sorted(EXPECTED_TYPES.items()):
        matching = indexed.get(name) or []
        assert matching, "missing managed type: %s" % name
        amount = sum(item.get("amount", 0) for item in matching)
        assert amount == expected, "%s amount=%r expected=%d" % (
            name,
            amount,
            expected,
        )
        print("PASS %3d %s" % (expected, name))
    assert "C# WeakTarget" not in indexed, "weak-only target survived as a strong root"

    generations = dotnet.get("object_generations") or {}
    assert generations.get("large", 0) >= 3, generations
    assert generations.get("pinned", 0) >= 4, generations

    segment_heaps = {
        int(index)
        for index, count in (dotnet.get("segment_logical_heaps") or {}).items()
        if count > 0
    }
    if expect_server:
        assert len(segment_heaps) >= 2, segment_heaps
        assert min(segment_heaps) == 0, segment_heaps
        assert max(segment_heaps) < runtime.get("logical_heaps", 0), (segment_heaps, runtime)
    else:
        assert segment_heaps == {0}, segment_heaps

    reference_kinds = dotnet.get("reference_kinds") or {}
    assert reference_kinds.get("field", 0) > 0, reference_kinds
    assert reference_kinds.get("array_element", 0) > 0, reference_kinds
    assert reference_kinds.get("dependent_handle", 0) >= 1, reference_kinds

    root_kinds = dotnet.get("root_kinds") or {}
    required_root_kinds = ["finalizer_queue", "strong_handle", "stack", "thread_static", "static"]
    if not expect_server:
        required_root_kinds.append("pinned_handle")
    for root_kind in required_root_kinds:
        assert root_kinds.get(root_kind, 0) >= 1, "missing root kind %s: %r" % (root_kind, root_kinds)

    special_kinds = dotnet.get("special_kinds") or {}
    for kind in [
        "app_domain",
        "assembly_load_context",
        "async",
        "async_awaiter",
        "exception",
        "exception_inner",
        "monitor",
        "task",
        "task_continuation",
        "thread",
        "value_task_continuation",
        "value_task_source",
    ]:
        assert special_kinds.get(kind, 0) >= 1, "missing special view %s: %r" % (kind, special_kinds)

    task_chains = dotnet.get("task_chains") or []
    fixture_task_chain = next(
        (
            chain
            for chain in task_chains
            if any("HoldAsyncState" in node.get("type_name", "") for node in (chain.get("nodes") or []))
            and any(
                "Task<System.Boolean>" in node.get("type_name", "")
                for node in (chain.get("nodes") or [])
            )
        ),
        None,
    )
    assert fixture_task_chain is not None, task_chains
    assert fixture_task_chain.get("truncated") is not True, fixture_task_chain

    async_waits = dotnet.get("async_waits") or []
    fixture_wait = next(
        (
            wait
            for wait in async_waits
            if "HoldAsyncState" in wait.get("state_machine_type", "")
            and "Task<System.Boolean>" in wait.get("awaited_type", "")
        ),
        None,
    )
    assert fixture_wait is not None, async_waits
    assert fixture_wait.get("state") == "state=0", fixture_wait
    assert "WaitingForActivation" in fixture_wait.get("status", ""), fixture_wait

    value_task_wait = next(
        (
            wait
            for wait in async_waits
            if "HoldValueTaskState" in wait.get("state_machine_type", "")
            and wait.get("awaited_type") == "FixtureValueTaskSource"
            and wait.get("token_matches") is True
        ),
        None,
    )
    assert value_task_wait is not None, async_waits
    assert value_task_wait.get("awaitable_kind") == "value_task_source", value_task_wait
    assert value_task_wait.get("source_status") == "Pending", value_task_wait
    assert value_task_wait.get("token") == value_task_wait.get("source_version"), value_task_wait
    assert value_task_wait.get("token_matches") is True, value_task_wait
    assert value_task_wait.get("continue_on_captured_context") is True, value_task_wait
    assert value_task_wait.get("continuation", 0) > 0, value_task_wait
    assert value_task_wait.get("continuation_state") == value_task_wait.get("state_machine"), value_task_wait

    stale_value_task_wait = next(
        (
            wait
            for wait in async_waits
            if "HoldValueTaskState" in wait.get("state_machine_type", "")
            and wait.get("awaited_type") == "FixtureValueTaskSource"
            and wait.get("token_matches") is False
        ),
        None,
    )
    assert stale_value_task_wait is not None, async_waits
    assert stale_value_task_wait.get("awaitable_kind") == "value_task_source", stale_value_task_wait
    assert stale_value_task_wait.get("source_status") == "Pending", stale_value_task_wait
    assert stale_value_task_wait.get("token") == 0, stale_value_task_wait
    assert stale_value_task_wait.get("source_version") == 1, stale_value_task_wait
    assert stale_value_task_wait.get("continue_on_captured_context") is True, stale_value_task_wait
    assert stale_value_task_wait.get("continuation", 0) == 0, stale_value_task_wait
    assert stale_value_task_wait.get("continuation_state", 0) == 0, stale_value_task_wait

    value_task_sources = dotnet.get("value_task_sources") or []
    fixture_value_task_source = next(
        (
            source
            for source in value_task_sources
            if source.get("source_type") == "FixtureValueTaskSource"
            and source.get("source") == value_task_wait.get("awaited")
        ),
        None,
    )
    assert fixture_value_task_source is not None, value_task_sources
    assert fixture_value_task_source.get("known_layout") is True, fixture_value_task_source
    assert fixture_value_task_source.get("status") == "Pending", fixture_value_task_source
    assert fixture_value_task_source.get("completed") is False, fixture_value_task_source
    assert fixture_value_task_source.get("run_continuations_asynchronously") is True, fixture_value_task_source
    assert fixture_value_task_source.get("version") == value_task_wait.get("token"), (
        fixture_value_task_source,
        value_task_wait,
    )
    assert fixture_value_task_source.get("continuation", 0) > 0, fixture_value_task_source
    assert fixture_value_task_source.get("continuation_state") == value_task_wait.get("state_machine"), (
        fixture_value_task_source,
        value_task_wait,
    )
    reused_value_task_source = next(
        (
            source
            for source in value_task_sources
            if source.get("source_type") == "FixtureValueTaskSource"
            and source.get("source") == stale_value_task_wait.get("awaited")
        ),
        None,
    )
    assert reused_value_task_source is not None, value_task_sources
    assert reused_value_task_source.get("known_layout") is True, reused_value_task_source
    assert reused_value_task_source.get("status") == "Pending", reused_value_task_source
    assert reused_value_task_source.get("version") == 1, reused_value_task_source
    assert reused_value_task_source.get("completed") is False, reused_value_task_source
    assert reused_value_task_source.get("continuation", 0) == 0, reused_value_task_source
    assert reused_value_task_source.get("continuation_state", 0) == 0, reused_value_task_source
    assert len(
        [source for source in value_task_sources if source.get("source_type") == "FixtureValueTaskSource"]
    ) >= 5, value_task_sources
    value_task_sources_by_status = {
        source.get("status"): source
        for source in value_task_sources
        if source.get("source_type") == "FixtureValueTaskSource"
        and source.get("version") == 0
    }
    assert {"Pending", "Succeeded", "Faulted", "Canceled"}.issubset(value_task_sources_by_status), (
        value_task_sources_by_status
    )
    for status, source in value_task_sources_by_status.items():
        assert source.get("known_layout") is True, source
        assert source.get("version") == 0, source
        assert source.get("run_continuations_asynchronously") is True, source
        assert source.get("completed") is (status != "Pending"), source
    assert value_task_sources_by_status["Faulted"].get("error_type") == "System.InvalidOperationException", (
        value_task_sources_by_status["Faulted"]
    )
    assert value_task_sources_by_status["Canceled"].get("error_type") == "System.OperationCanceledException", (
        value_task_sources_by_status["Canceled"]
    )

    async_stacks = dotnet.get("async_stacks") or []
    fixture_async_stack = next(
        (
            stack
            for stack in async_stacks
            if any(
                "HoldAsyncState" in frame.get("type_name", "")
                for frame in (stack.get("frames") or [])
            )
        ),
        None,
    )
    assert fixture_async_stack is not None, async_stacks
    fixture_async_frame = next(
        frame
        for frame in fixture_async_stack.get("frames") or []
        if "HoldAsyncState" in frame.get("type_name", "")
    )
    assert any(
        "Task<System.Boolean>" in wait.get("awaited_type", "")
        for wait in (fixture_async_frame.get("waits") or [])
    ), fixture_async_frame
    value_task_async_frame = next(
        frame
        for stack in async_stacks
        for frame in (stack.get("frames") or [])
        if "HoldValueTaskState" in frame.get("type_name", "")
    )
    assert any(
        wait.get("awaitable_kind") == "value_task_source"
        and wait.get("token_matches") is True
        for wait in (value_task_async_frame.get("waits") or [])
    ), value_task_async_frame
    assert any(
        wait.get("awaitable_kind") == "value_task_source"
        and wait.get("token_matches") is False
        for stack in async_stacks
        for frame in (stack.get("frames") or [])
        if "HoldValueTaskState" in frame.get("type_name", "")
        for wait in (frame.get("waits") or [])
    ), async_stacks

    monitors = dotnet.get("monitors") or []
    fixture_monitor = next(
        (monitor for monitor in monitors if monitor.get("type_name") == "MonitorFixtureLock"),
        None,
    )
    assert fixture_monitor is not None, monitors
    assert fixture_monitor.get("held") is True, fixture_monitor
    # .NET 11's System.Threading.Lock-backed Monitor path is visible in the
    # physical waiter stack, but preview6 DAC reports MonitorHeld=1 and
    # AdditionalThreadCount=0. ClrMD consequently cannot prove the waiter
    # count. Keep the object/thread evidence separate instead of inventing a
    # waiter-to-lock edge from a fixture name.
    if expected_runtime_major <= 10:
        assert fixture_monitor.get("waiting_thread_count", 0) >= 1, fixture_monitor
    assert fixture_monitor.get("holder_name") == "maze-dotnet-monitor-owner", fixture_monitor
    assert fixture_monitor.get("holder_thread", 0) > 0, fixture_monitor
    assert fixture_monitor.get("holder_managed_thread", 0) > 0, fixture_monitor
    assert fixture_monitor.get("holder_os_thread", 0) > 0, fixture_monitor
    assert fixture_monitor.get("recursion", 0) >= 1, fixture_monitor

    exception_chains = dotnet.get("exception_chains") or []
    aggregate_chain = next(
        (
            chain
            for chain in exception_chains
            if any(
                node.get("type_name") == "System.AggregateException"
                for node in (chain.get("nodes") or [])
            )
        ),
        None,
    )
    assert aggregate_chain is not None, exception_chains
    aggregate_children = {
        node.get("type_name")
        for node in (aggregate_chain.get("nodes") or [])
        if node.get("parent") == aggregate_chain.get("root")
    }
    assert "System.InvalidOperationException" in aggregate_children, aggregate_chain
    assert "System.ArgumentException" in aggregate_children, aggregate_chain

    threads = dotnet.get("threads") or []
    fixture_threads = [thread for thread in threads if thread.get("name") == "maze-dotnet-fixture-root"]
    assert fixture_threads, threads
    fixture_thread_stack = fixture_threads[0].get("summary", "")
    assert "System.Threading.ManualResetEventSlim.Wait" in fixture_thread_stack, fixture_threads[0]
    assert "Program" in fixture_thread_stack and "Main" in fixture_thread_stack, fixture_threads[0]

    monitor_waiters = [
        thread for thread in threads if thread.get("name") == "maze-dotnet-monitor-waiter"
    ]
    assert monitor_waiters, threads
    monitor_waiter_stack = monitor_waiters[0].get("summary", "")
    assert (
        "System.Threading.Monitor." in monitor_waiter_stack
        and "Enter" in monitor_waiter_stack
    ), monitor_waiters[0]
    if expected_runtime_major >= 11:
        assert "System.Threading.Lock" in monitor_waiter_stack, monitor_waiters[0]

    specials = dotnet.get("specials") or []
    assert any(
        special.get("kind") == "exception"
        and special.get("name") == "FixtureException"
        and "fixture exception" in special.get("summary", "")
        for special in specials
    ), specials
    assert any(
        special.get("kind") == "task" and "WaitingForActivation" in special.get("summary", "")
        for special in specials
    ), specials
    assert any(
        special.get("kind") == "async" and "state=0" in special.get("summary", "")
        for special in specials
    ), specials
    assert any(
        special.get("kind") == "assembly_load_context"
        and special.get("name") == "maze-fixture-collectible"
        for special in specials
    ), specials

    retainers = dotnet.get("top_retainers") or []
    fixture_retainer = next((item for item in retainers if item.get("type_name") == "FixtureState"), None)
    assert fixture_retainer is not None, retainers
    assert fixture_retainer.get("retained_bytes", 0) > fixture_retainer.get("shallow_bytes", 0), fixture_retainer

    samples = dotnet.get("object_samples") or []
    string_holders = [sample for sample in samples if sample.get("type_name") == "StringHolder"]
    assert string_holders, samples
    string_values = [
        field.get("value")
        for sample in string_holders
        for field in (sample.get("fields") or [])
        if field.get("name") == "<Value>k__BackingField"
    ]
    assert "maze-string-00" in string_values, string_values

    graph_nodes = [sample for sample in samples if sample.get("type_name") == "GraphNode"]
    assert graph_nodes, samples
    assert any(
        field.get("name") == "<Id>k__BackingField" and field.get("value") == "0"
        for field in (graph_nodes[0].get("fields") or [])
    ), graph_nodes[0]
    graph_path = graph_nodes[0].get("root_path", "")
    assert (
        "thread managed=" in graph_path
        and "AppDomain" in graph_path
        and "FixtureState" in graph_path
    ), graph_path

    collectible_payloads = [sample for sample in samples if sample.get("type_name") == "CollectiblePayload"]
    assert collectible_payloads, samples
    collectible_paths = [sample.get("root_path", "") for sample in collectible_payloads]
    assert any('ALC "maze-fixture-collectible"' in path for path in collectible_paths) or any(
        special.get("kind") == "assembly_load_context"
        and special.get("name") == "maze-fixture-collectible"
        for special in (dotnet.get("specials") or [])
    ), collectible_paths

    thread_root_holders = [sample for sample in samples if sample.get("type_name") == "ThreadRootHolder"]
    assert thread_root_holders, samples
    thread_root_path = thread_root_holders[0].get("root_path", "")
    assert 'display="maze-dotnet-fixture-root"' in thread_root_path, thread_root_path

    multi_root_payloads = [sample for sample in samples if sample.get("type_name") == "MultiRootPayload"]
    assert multi_root_payloads, samples
    multi_root_payload = multi_root_payloads[0]
    multi_root_paths = multi_root_payload.get("root_paths") or []
    assert len(multi_root_paths) >= 2, multi_root_payload
    assert multi_root_payload.get("root_path") == multi_root_paths[0], multi_root_payload
    assert any("FixtureRoots.MultiRootLeft" in path for path in multi_root_paths), multi_root_paths
    assert any("FixtureRoots.MultiRootRight" in path for path in multi_root_paths), multi_root_paths
    assert all("<Payload>k__BackingField" in path for path in multi_root_paths[:2]), multi_root_paths
    assert multi_root_payload.get("root_paths_truncated") is not True, multi_root_payload

    container_summaries = [sample.get("summary", "") for sample in samples]
    assert any("Count=" in summary and "Capacity=" in summary for summary in container_summaries), container_summaries
    if expect_channels:
        assert any(
            "Count=6 Capacity=unbounded State=Open Shape=Unbounded" in summary
            and "Backing=ConcurrentQueue FrontToBack" in summary
            and summary.count("maze-channel-duplicate") == 2
            for summary in container_summaries
        ), container_summaries
        assert any(
            "Count=3 Capacity=unbounded State=Open Shape=UnboundedSingleReader" in summary
            and "Backing=SPSCQueue FrontToBack [222, 333, 444]" in summary
            for summary in container_summaries
        ), container_summaries
        assert any(
            "Count=6 Capacity=8 State=Open Shape=Bounded Mode=Wait" in summary
            and "Backing=Deque FrontToBack" in summary
            and summary.count("maze-bounded-channel-duplicate") == 2
            for summary in container_summaries
        ), container_summaries
        assert any(
            "Count=2 Capacity=3 State=Draining Shape=Bounded" in summary
            and "Backing=Deque FrontToBack [1111, 2222]" in summary
            for summary in container_summaries
        ), container_summaries
        assert any(
            "Count=0 Capacity=unbounded State=Completed Shape=Unbounded" in summary
            for summary in container_summaries
        ), container_summaries
        assert any(
            "Count=5 Capacity=4 State=Open Shape=Bounded" in summary
            and summary.endswith("<partial>")
            for summary in container_summaries
        ), container_summaries
        if expected_runtime_major >= 9:
            assert any(
                "Count=1 Capacity=1 State=Open Shape=Bounded" in summary
                and "BlockedWriters=true" in summary
                and "PendingWritePayloads=<omitted> <partial>" in summary
                for summary in container_summaries
            ), container_summaries
            assert any(
                "Count=0 Capacity=unbounded State=Open Shape=Unbounded" in summary
                and "BlockedReaders=true" in summary
                for summary in container_summaries
            ), container_summaries
        if expected_runtime_major >= 10:
            assert any(
                "Count=0 Capacity=0 State=Open Shape=Rendezvous Mode=Wait" in summary
                and "Backing=None" in summary
                for summary in container_summaries
            ), container_summaries

    assert data.get("known_size") == dotnet.get("shallow_bytes"), (
        data.get("known_size"),
        dotnet.get("shallow_bytes"),
    )
    assert summary.get("allocator_total", 0) > 0, summary
    native = [
        item
        for item in items
        if item.get("type", "").startswith("malloc(")
        and 120000 <= item.get("avg_size", 0) <= 130000
    ]
    assert native, "native fixture allocation was not reported separately"

    maze_log = read_required_file("MAZE_TEST_MAZE_LOG")
    maze_output = read_required_file("MAZE_TEST_OUTPUT_LOG")
    assert "coreclr-gc" in maze_log, "GC committed mmap owner was not published"
    assert "CoreCLR:" in maze_output, "text output omitted CoreCLR summary"
    assert "CountGoroutineError: 0" in maze_output, "analysis reported goroutine errors"
    print("PASS roots, refs, Task/ValueTask/exception chains, LOH, POH, native separation and coreclr-gc ownership")
    return True

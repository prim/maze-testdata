#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from validate_managed_heap import validate_case


def validate(data):
    validate_case(data, expect_server=False, expect_channels=True)
    dotnet = data.get("dotnet") or {}
    static_samples = dotnet.get("static_samples") or []

    def find_static(owner, field, storage, value=None):
        return next(
            (
                item
                for item in static_samples
                if item.get("owner_type") == owner
                and item.get("field_name") == field
                and item.get("storage_kind") == storage
                and (value is None or item.get("value") == value)
            ),
            None,
        )

    static_count = find_static("StaticValueRoots", "Count", "static", "314159")
    assert static_count is not None, static_samples
    assert static_count.get("initialized") is True, static_count
    assert static_count.get("read_supported") is True, static_count
    assert static_count.get("value_kind") == "primitive", static_count
    assert static_count.get("value_exact") is True, static_count
    assert "AppDomain" in static_count.get("context", ""), static_count

    static_label = find_static(
        "StaticValueRoots", "Label", "static", "maze-static-business-value"
    )
    assert static_label is not None, static_samples
    assert static_label.get("value_kind") == "string", static_label
    assert static_label.get("value_exact") is True, static_label
    assert static_label.get("target_type") == "System.String", static_label
    assert static_label.get("target_retained_size", 0) >= static_label.get(
        "target_shallow_size", 0
    ) > 0, static_label
    assert static_label.get("target_reachable") is True, static_label

    static_guid = find_static(
        "StaticValueRoots",
        "CorrelationId",
        "static",
        "13572468-2468-1357-aaaa-bbbbccccdddd",
    )
    assert static_guid is not None, static_samples
    assert static_guid.get("value_kind") == "value_type", static_guid
    assert static_guid.get("value_exact") is True, static_guid

    static_amount = find_static(
        "StaticValueRoots", "Amount", "static", "987654321.012300"
    )
    assert static_amount is not None, static_samples
    assert static_amount.get("value_kind") == "value_type", static_amount
    assert static_amount.get("value_exact") is True, static_amount

    static_occurred_at = find_static(
        "StaticValueRoots",
        "OccurredAt",
        "static",
        "2026-08-03T12:34:56.0007890Z",
    )
    assert static_occurred_at is not None, static_samples
    assert static_occurred_at.get("value_kind") == "value_type", static_occurred_at
    assert static_occurred_at.get("value_exact") is True, static_occurred_at

    static_lifecycle = find_static(
        "StaticValueRoots", "Lifecycle", "static", "Ready (7)"
    )
    assert static_lifecycle is not None, static_samples
    assert static_lifecycle.get("value_kind") == "value_type", static_lifecycle
    assert static_lifecycle.get("value_exact") is True, static_lifecycle

    thread_count = find_static(
        "ThreadValueRoots", "Count", "thread_static", "161803"
    )
    assert thread_count is not None, static_samples
    assert thread_count.get("display_name") == "maze-dotnet-fixture-root", thread_count
    assert 'display="maze-dotnet-fixture-root"' in thread_count.get(
        "context", ""
    ), thread_count
    assert thread_count.get("value_exact") is True, thread_count

    thread_label = find_static(
        "ThreadValueRoots",
        "Label",
        "thread_static",
        "maze-thread-static-business-value",
    )
    assert thread_label is not None, static_samples
    assert thread_label.get("display_name") == "maze-dotnet-fixture-root", thread_label
    assert thread_label.get("target_type") == "System.String", thread_label
    assert thread_label.get("target_retained_size", 0) >= thread_label.get(
        "target_shallow_size", 0
    ) > 0, thread_label

    untouched = [
        item
        for item in static_samples
        if item.get("owner_type") == "UntouchedStaticValues"
    ]
    assert {item.get("field_name") for item in untouched} == {"Count", "Label"}, untouched
    assert all(item.get("initialized") is False for item in untouched), untouched
    assert all(item.get("read_supported") is True for item in untouched), untouched
    assert all(item.get("value_kind") == "uninitialized" for item in untouched), untouched

    static_reference = find_static("StaticValueRoots", "Reference", "static")
    thread_reference = next(
        (
            item
            for item in static_samples
            if item.get("owner_type") == "ThreadValueRoots"
            and item.get("field_name") == "Reference"
            and item.get("storage_kind") == "thread_static"
            and item.get("initialized") is True
        ),
        None,
    )
    assert static_reference is not None and thread_reference is not None, static_samples
    assert static_reference.get("target_type") == "SharedChild", static_reference
    assert static_reference.get("target_address") == thread_reference.get(
        "target_address"
    ), (static_reference, thread_reference)
    assert static_reference.get("target_retained_size", 0) > 0, static_reference
    assert static_reference.get("target_reachable") is True, static_reference

    samples = dotnet.get("object_samples") or []
    business_values = next(
        (sample for sample in samples if sample.get("type_name") == "BusinessValueFixtures"),
        None,
    )
    assert business_values is not None, samples
    business_fields = {
        field.get("name"): field.get("value")
        for field in (business_values.get("fields") or [])
    }
    expected_business_fields = {
        "<Lifecycle>k__BackingField": "{FixtureLifecycle} Ready (7)",
        "<UnmappedLifecycle>k__BackingField": "{FixtureLifecycle} 123",
        "<Permissions>k__BackingField": "{FixturePermissions} ReadWrite (3)",
        "<UtcWhen>k__BackingField": "{System.DateTime} 2024-05-06T07:08:09.1234567Z",
        "<UnspecifiedWhen>k__BackingField": (
            "{System.DateTime} 2030-12-31T23:59:58.9876543 [Unspecified]"
        ),
        "<OffsetWhen>k__BackingField": (
            "{System.DateTimeOffset} 2025-06-07T08:09:10.3217654+05:30"
        ),
        "<Duration>k__BackingField": "{System.TimeSpan} 2.03:04:05.6789012",
        "<CorrelationId>k__BackingField": (
            "{System.Guid} 01234567-89ab-cdef-0123-456789abcdef"
        ),
        "<Amount>k__BackingField": "{System.Decimal} -1234567890.012300",
        "<PresentCount>k__BackingField": "{System.Nullable<System.Int32>} 4242",
        "<MissingCount>k__BackingField": "{System.Nullable<System.Int32>} null",
        "<OptionalWhen>k__BackingField": (
            "{System.Nullable<System.DateTime>} 2024-05-06T07:08:09.1234567Z"
        ),
        "<BusinessDate>k__BackingField": "{System.DateOnly} 2024-05-06",
        "<BusinessTime>k__BackingField": "{System.TimeOnly} 07:08:09.1234567",
    }
    for field_name, expected_value in expected_business_fields.items():
        assert business_fields.get(field_name) == expected_value, (
            field_name,
            business_fields.get(field_name),
            business_values,
        )

    value_type_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.List<System.DateTimeOffset>"
        ),
        None,
    )
    assert value_type_list is not None, samples
    assert value_type_list.get("summary") == (
        "Count=2 Capacity=2 [2020-01-02T03:04:05.6007000-04:00, "
        "2025-06-07T08:09:10.3217654+05:30]"
    ), value_type_list

    value_type_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.Dictionary<System.Guid, System.Decimal>"
        ),
        None,
    )
    assert value_type_dictionary is not None, samples
    value_type_dictionary_summary = value_type_dictionary.get("summary", "")
    assert "01234567-89ab-cdef-0123-456789abcdef: -1234567890.012300" in (
        value_type_dictionary_summary
    ), value_type_dictionary
    assert "fedcba98-7654-3210-fedc-ba9876543210: 42.500" in (
        value_type_dictionary_summary
    ), value_type_dictionary

    boxed_business_values = {
        sample.get("type_name"): sample.get("summary")
        for sample in samples
        if "BoxedBusinessValues" in sample.get("root_path", "")
    }
    # Boxed sample selection is deliberately one representative per type and
    # may choose another valid Guid/Decimal/DateTime object. Their exact
    # business formatting remains asserted above through ordinary fields,
    # containers, and the deterministic StaticValueRoots records.
    assert boxed_business_values.get("FixtureLifecycle") == "Ready (7)", boxed_business_values

    lifecycle_array = next(
        (sample for sample in samples if sample.get("type_name") == "FixtureLifecycle[]"),
        None,
    )
    assert lifecycle_array is not None, samples
    assert lifecycle_array.get("summary") == (
        "rank=1 dimensions=3 element=FixtureLifecycle "
        "[Unknown (0), Ready (7), Failed (-1)]"
    ), lifecycle_array

    concurrent = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentDictionary<System.String, System.Object>"
        ),
        None,
    )
    assert concurrent is not None, samples
    summary = concurrent.get("summary", "")
    assert "Count=4 Capacity=" in summary, summary
    assert "maze-concurrent-string" in summary, summary
    assert "maze-concurrent-reference" in summary, summary
    assert "maze-concurrent-null" in summary, summary
    assert "maze-concurrent-new-value" in summary, summary
    assert "maze-concurrent-removed" not in summary, summary
    assert "maze-concurrent-old-value" not in summary, summary
    assert concurrent.get("retained_bytes", 0) > concurrent.get("shallow_bytes", 0), concurrent
    paths = concurrent.get("root_paths") or []
    assert len(paths) >= 2, concurrent
    assert any("thread managed=" in path for path in paths), paths
    assert any("AppDomain" in path and "FixtureRoots.State" in path for path in paths), paths
    assert all("BusinessConcurrentDictionary" in path for path in paths[:2]), paths

    count_partial = next(
        (
            sample
            for sample in samples
            if "maze-concurrent-count-partial" in sample.get("summary", "")
        ),
        None,
    )
    assert count_partial is not None, samples
    assert "<partial>" in count_partial.get("summary", ""), count_partial

    cycle_partial = next(
        (
            sample
            for sample in samples
            if "maze-concurrent-cycle-partial" in sample.get("summary", "")
        ),
        None,
    )
    assert cycle_partial is not None, samples
    assert "<partial>" in cycle_partial.get("summary", ""), cycle_partial

    business_concurrent_queue = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentQueue<System.Object>"
        ),
        None,
    )
    assert business_concurrent_queue is not None, samples
    business_concurrent_queue_summary = business_concurrent_queue.get("summary", "")
    assert "Count=4 FrontToBack" in business_concurrent_queue_summary, business_concurrent_queue_summary
    for value in [
        "maze-concurrent-queue-first",
        "GraphNode",
        "null",
        "maze-concurrent-queue-last",
    ]:
        assert value in business_concurrent_queue_summary, (value, business_concurrent_queue_summary)
    assert "maze-concurrent-queue-discard" not in business_concurrent_queue_summary, (
        business_concurrent_queue_summary
    )
    assert "maze-concurrent-queue-removed" not in business_concurrent_queue_summary, (
        business_concurrent_queue_summary
    )
    assert business_concurrent_queue_summary.index(
        "maze-concurrent-queue-first"
    ) < business_concurrent_queue_summary.index("GraphNode"), business_concurrent_queue_summary
    assert business_concurrent_queue_summary.index("GraphNode") < business_concurrent_queue_summary.index(
        "null"
    ), business_concurrent_queue_summary
    assert business_concurrent_queue_summary.index("null") < business_concurrent_queue_summary.index(
        "maze-concurrent-queue-last"
    ), business_concurrent_queue_summary
    concurrent_queue_paths = business_concurrent_queue.get("root_paths") or []
    assert len(concurrent_queue_paths) >= 2, business_concurrent_queue
    assert all("BusinessConcurrentQueue" in path for path in concurrent_queue_paths[:2]), concurrent_queue_paths

    primitive_concurrent_queue = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentQueue<System.Int32>"
        ),
        None,
    )
    assert primitive_concurrent_queue is not None, samples
    assert primitive_concurrent_queue.get("summary") == "Count=3 FrontToBack [222, 333, 444]", (
        primitive_concurrent_queue
    )

    cycle_concurrent_queue = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentQueue<System.Int64>"
        ),
        None,
    )
    assert cycle_concurrent_queue is not None, samples
    assert "<partial>" in cycle_concurrent_queue.get("summary", ""), cycle_concurrent_queue

    business_concurrent_stack = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentStack<System.Object>"
        ),
        None,
    )
    assert business_concurrent_stack is not None, samples
    business_concurrent_stack_summary = business_concurrent_stack.get("summary", "")
    assert "Count=4 TopToBottom" in business_concurrent_stack_summary, business_concurrent_stack_summary
    for value in [
        "maze-concurrent-stack-top",
        "null",
        "GraphNode",
        "maze-concurrent-stack-bottom",
    ]:
        assert value in business_concurrent_stack_summary, (value, business_concurrent_stack_summary)
    assert "maze-concurrent-stack-removed" not in business_concurrent_stack_summary, (
        business_concurrent_stack_summary
    )
    assert business_concurrent_stack_summary.index(
        "maze-concurrent-stack-top"
    ) < business_concurrent_stack_summary.index("null"), business_concurrent_stack_summary
    assert business_concurrent_stack_summary.index("null") < business_concurrent_stack_summary.index(
        "GraphNode"
    ), business_concurrent_stack_summary
    assert business_concurrent_stack_summary.index("GraphNode") < business_concurrent_stack_summary.index(
        "maze-concurrent-stack-bottom"
    ), business_concurrent_stack_summary

    primitive_concurrent_stack = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentStack<System.Int32>"
        ),
        None,
    )
    assert primitive_concurrent_stack is not None, samples
    assert primitive_concurrent_stack.get("summary") == "Count=3 TopToBottom [333, 222, 111]", (
        primitive_concurrent_stack
    )

    cycle_concurrent_stack = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentStack<System.Int64>"
        ),
        None,
    )
    assert cycle_concurrent_stack is not None, samples
    assert "1702" in cycle_concurrent_stack.get("summary", ""), cycle_concurrent_stack
    assert "<partial>" in cycle_concurrent_stack.get("summary", ""), cycle_concurrent_stack

    business_concurrent_bag = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentBag<System.Object>"
        ),
        None,
    )
    assert business_concurrent_bag is not None, samples
    business_concurrent_bag_summary = business_concurrent_bag.get("summary", "")
    assert "Count=6 SnapshotOrder" in business_concurrent_bag_summary, business_concurrent_bag_summary
    for value in [
        "maze-concurrent-bag-first",
        "GraphNode",
        "null",
        "maze-concurrent-bag-last",
    ]:
        assert value in business_concurrent_bag_summary, (value, business_concurrent_bag_summary)
    assert "maze-concurrent-bag-removed" not in business_concurrent_bag_summary, (
        business_concurrent_bag_summary
    )
    assert business_concurrent_bag_summary.count("maze-concurrent-bag-duplicate") == 2, (
        business_concurrent_bag_summary
    )
    concurrent_bag_paths = business_concurrent_bag.get("root_paths") or []
    assert len(concurrent_bag_paths) >= 2, business_concurrent_bag
    assert all("BusinessConcurrentBag" in path for path in concurrent_bag_paths[:2]), concurrent_bag_paths

    primitive_concurrent_bag = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentBag<System.Int32>"
        ),
        None,
    )
    assert primitive_concurrent_bag is not None, samples
    assert primitive_concurrent_bag.get("summary") == "Count=3 SnapshotOrder [444, 222, 111]", (
        primitive_concurrent_bag
    )

    cycle_concurrent_bag = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentBag<System.Int64>"
        ),
        None,
    )
    assert cycle_concurrent_bag is not None, samples
    assert "1703" in cycle_concurrent_bag.get("summary", ""), cycle_concurrent_bag
    assert "<partial>" in cycle_concurrent_bag.get("summary", ""), cycle_concurrent_bag

    count_partial_concurrent_bag = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentBag<System.Int16>"
        ),
        None,
    )
    assert count_partial_concurrent_bag is not None, samples
    assert "<partial>" in count_partial_concurrent_bag.get("summary", ""), count_partial_concurrent_bag

    operation_partial_concurrent_bag = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.ConcurrentBag<System.Byte>"
        ),
        None,
    )
    assert operation_partial_concurrent_bag is not None, samples
    assert "<partial>" in operation_partial_concurrent_bag.get("summary", ""), (
        operation_partial_concurrent_bag
    )

    business_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<System.String>"
        ),
        None,
    )
    assert business_blocking is not None, samples
    business_blocking_summary = business_blocking.get("summary", "")
    for value in [
        "Count=6 Capacity=8 State=AddingOpen",
        "Disposed=false",
        "ProducerCanceled=false",
        "ConsumerCanceled=false",
        "Backing=ConcurrentQueue FrontToBack",
        "maze-blocking-first",
        "maze-blocking-middle",
        "null",
        "maze-blocking-last",
    ]:
        assert value in business_blocking_summary, (value, business_blocking_summary)
    assert "maze-blocking-removed" not in business_blocking_summary, business_blocking_summary
    assert business_blocking_summary.count("maze-blocking-duplicate") == 2, business_blocking_summary
    assert "<partial>" not in business_blocking_summary, business_blocking_summary
    blocking_paths = business_blocking.get("root_paths") or []
    assert len(blocking_paths) >= 2, business_blocking
    assert all("BusinessBlockingCollection" in path for path in blocking_paths[:2]), blocking_paths

    completed_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<System.UInt32>"
        ),
        None,
    )
    assert completed_blocking is not None, samples
    completed_blocking_summary = completed_blocking.get("summary", "")
    assert "Count=3 Capacity=unbounded State=AddingCompleted" in completed_blocking_summary, (
        completed_blocking_summary
    )
    assert "ProducerCanceled=true ConsumerCanceled=false" in completed_blocking_summary, (
        completed_blocking_summary
    )
    assert "Backing=ConcurrentStack TopToBottom [444, 222, 111]" in completed_blocking_summary, (
        completed_blocking_summary
    )
    assert "<partial>" not in completed_blocking_summary, completed_blocking_summary

    completed_empty_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<System.UInt64>"
        ),
        None,
    )
    assert completed_empty_blocking is not None, samples
    completed_empty_summary = completed_empty_blocking.get("summary", "")
    assert "Count=0 Capacity=unbounded State=Completed" in completed_empty_summary, completed_empty_summary
    assert "ProducerCanceled=true ConsumerCanceled=true" in completed_empty_summary, completed_empty_summary
    assert "Backing=ConcurrentBag SnapshotOrder" in completed_empty_summary, completed_empty_summary
    assert "<partial>" not in completed_empty_summary, completed_empty_summary

    custom_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<CustomBlockingValue>"
        ),
        None,
    )
    assert custom_blocking is not None, samples
    custom_blocking_summary = custom_blocking.get("summary", "")
    assert "Count=1 Capacity=unbounded State=AddingOpen" in custom_blocking_summary, custom_blocking_summary
    assert "FixtureProducerConsumerCollection<CustomBlockingValue>" in custom_blocking_summary, custom_blocking_summary
    assert "<unsupported backing>" in custom_blocking_summary, custom_blocking_summary
    assert "<partial>" in custom_blocking_summary, custom_blocking_summary

    count_partial_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<System.Int16>"
        ),
        None,
    )
    assert count_partial_blocking is not None, samples
    assert "Count=3 Capacity=5" in count_partial_blocking.get("summary", ""), count_partial_blocking
    assert "<partial>" in count_partial_blocking.get("summary", ""), count_partial_blocking

    completing_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<System.Byte>"
        ),
        None,
    )
    assert completing_blocking is not None, samples
    completing_blocking_summary = completing_blocking.get("summary", "")
    assert "State=Completing" in completing_blocking_summary, completing_blocking_summary
    assert "ActiveAdders=1" in completing_blocking_summary, completing_blocking_summary
    assert "<partial>" in completing_blocking_summary, completing_blocking_summary

    disposed_blocking = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Concurrent.BlockingCollection<System.UInt16>"
        ),
        None,
    )
    assert disposed_blocking is not None, samples
    disposed_blocking_summary = disposed_blocking.get("summary", "")
    assert "Count=2 Capacity=4 State=AddingOpen Disposed=true" in disposed_blocking_summary, (
        disposed_blocking_summary
    )
    assert "Backing=ConcurrentQueue FrontToBack [1111, 2222]" in disposed_blocking_summary, (
        disposed_blocking_summary
    )
    assert "<partial>" not in disposed_blocking_summary, disposed_blocking_summary

    business_linked = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Generic.LinkedList<System.Object>"
        ),
        None,
    )
    assert business_linked is not None, samples
    linked_summary = business_linked.get("summary", "")
    assert "Count=4" in linked_summary, linked_summary
    assert "maze-linked-first" in linked_summary, linked_summary
    assert "GraphNode" in linked_summary and "null" in linked_summary, linked_summary
    assert "maze-linked-last" in linked_summary, linked_summary
    assert "maze-linked-removed" not in linked_summary, linked_summary
    assert linked_summary.index("maze-linked-first") < linked_summary.index("GraphNode"), linked_summary
    assert linked_summary.index("GraphNode") < linked_summary.index("null"), linked_summary
    assert linked_summary.index("null") < linked_summary.index("maze-linked-last"), linked_summary

    primitive_linked = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Generic.LinkedList<System.Int32>"
        ),
        None,
    )
    assert primitive_linked is not None, samples
    assert primitive_linked.get("summary") == "Count=3 [1111, 3333, 4444]", primitive_linked

    linked_partial = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Generic.LinkedList<System.String>"
        ),
        None,
    )
    assert linked_partial is not None, samples
    assert "Count=3" in linked_partial.get("summary", ""), linked_partial
    assert "<partial>" in linked_partial.get("summary", ""), linked_partial

    business_sorted = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.SortedList<System.String, System.Object>"
        ),
        None,
    )
    assert business_sorted is not None, samples
    sorted_summary = business_sorted.get("summary", "")
    assert "Count=4 Capacity=" in sorted_summary, sorted_summary
    for value in [
        "maze-sorted-alpha",
        "maze-sorted-value",
        "maze-sorted-graph",
        "GraphNode",
        "maze-sorted-null",
        "null",
        "maze-sorted-updated",
        "maze-sorted-new-value",
    ]:
        assert value in sorted_summary, (value, sorted_summary)
    assert "maze-sorted-removed" not in sorted_summary, sorted_summary
    assert "maze-sorted-old-value" not in sorted_summary, sorted_summary
    assert sorted_summary.index("maze-sorted-alpha") < sorted_summary.index("maze-sorted-graph"), sorted_summary
    assert sorted_summary.index("maze-sorted-graph") < sorted_summary.index("maze-sorted-null"), sorted_summary
    assert sorted_summary.index("maze-sorted-null") < sorted_summary.index("maze-sorted-updated"), sorted_summary

    primitive_sorted = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.SortedList<System.Int32, System.Int32>"
        ),
        None,
    )
    assert primitive_sorted is not None, samples
    primitive_sorted_summary = primitive_sorted.get("summary", "")
    assert "Count=2 Capacity=" in primitive_sorted_summary, primitive_sorted_summary
    assert "101: 1001" in primitive_sorted_summary, primitive_sorted_summary
    assert "303: 3003" in primitive_sorted_summary, primitive_sorted_summary
    assert "202" not in primitive_sorted_summary and "2002" not in primitive_sorted_summary, primitive_sorted_summary

    sorted_partial = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.SortedList<System.String, System.String>"
        ),
        None,
    )
    assert sorted_partial is not None, samples
    assert "Count=5 Capacity=4" in sorted_partial.get("summary", ""), sorted_partial
    assert "<partial>" in sorted_partial.get("summary", ""), sorted_partial

    business_priority = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.PriorityQueue<System.Object, System.Int32>"
        ),
        None,
    )
    assert business_priority is not None, samples
    priority_summary = business_priority.get("summary", "")
    assert "Count=4 Capacity=8 Unordered" in priority_summary, priority_summary
    for value in [
        "maze-priority-urgent",
        "maze-priority-later",
        "GraphNode",
        "null",
        " @ 1",
        " @ 10",
        " @ 20",
        " @ 30",
    ]:
        assert value in priority_summary, (value, priority_summary)
    assert "maze-priority-removed" not in priority_summary, priority_summary
    assert priority_summary.index("maze-priority-urgent") < priority_summary.index("maze-priority-later"), (
        priority_summary
    )

    primitive_priority = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.PriorityQueue<System.Int32, System.Int32>"
        ),
        None,
    )
    assert primitive_priority is not None, samples
    primitive_priority_summary = primitive_priority.get("summary", "")
    assert "Count=2 Capacity=4 Unordered" in primitive_priority_summary, primitive_priority_summary
    assert "4004 @ 40" in primitive_priority_summary, primitive_priority_summary
    assert "7007 @ 70" in primitive_priority_summary, primitive_priority_summary
    assert "1001" not in primitive_priority_summary, primitive_priority_summary

    priority_partial = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Generic.PriorityQueue<System.String, System.Int32>"
        ),
        None,
    )
    assert priority_partial is not None, samples
    assert "Count=5 Capacity=4 Unordered" in priority_partial.get("summary", ""), priority_partial
    assert "<partial>" in priority_partial.get("summary", ""), priority_partial

    business_read_only_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.ObjectModel.ReadOnlyCollection<System.Object>"
        ),
        None,
    )
    assert business_read_only_list is not None, samples
    read_only_list_summary = business_read_only_list.get("summary", "")
    assert "Count=4 Backing=System.Collections.Generic.List<System.Object>" in read_only_list_summary, (
        read_only_list_summary
    )
    assert "maze-readonly-list-first" in read_only_list_summary, read_only_list_summary
    assert "GraphNode" in read_only_list_summary and "null" in read_only_list_summary, read_only_list_summary
    assert "maze-readonly-list-last" in read_only_list_summary, read_only_list_summary
    assert "maze-readonly-list-removed" not in read_only_list_summary, read_only_list_summary

    array_read_only_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.ObjectModel.ReadOnlyCollection<System.Int32>"
        ),
        None,
    )
    assert array_read_only_list is not None, samples
    assert array_read_only_list.get("summary") == (
        "Count=3 Backing=System.Int32[] [1212, 3434, 5656]"
    ), array_read_only_list

    custom_read_only_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.ObjectModel.ReadOnlyCollection<System.String>"
        ),
        None,
    )
    assert custom_read_only_list is not None, samples
    assert "Backing=FixtureList<System.String>" in custom_read_only_list.get("summary", ""), custom_read_only_list
    assert "<partial>" in custom_read_only_list.get("summary", ""), custom_read_only_list

    business_read_only_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.ObjectModel.ReadOnlyDictionary<System.String, System.Object>"
        ),
        None,
    )
    assert business_read_only_dictionary is not None, samples
    read_only_dictionary_summary = business_read_only_dictionary.get("summary", "")
    assert "Count=4 Capacity=7 Backing=System.Collections.Generic.Dictionary" in read_only_dictionary_summary, (
        read_only_dictionary_summary
    )
    assert "maze-readonly-dictionary-alpha" in read_only_dictionary_summary, read_only_dictionary_summary
    assert "maze-readonly-dictionary-new-value" in read_only_dictionary_summary, read_only_dictionary_summary
    assert "maze-readonly-dictionary-removed" not in read_only_dictionary_summary, read_only_dictionary_summary
    assert "maze-readonly-dictionary-old-value" not in read_only_dictionary_summary, read_only_dictionary_summary

    sorted_read_only_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.ObjectModel.ReadOnlyDictionary<System.Int32, System.Int32>"
        ),
        None,
    )
    assert sorted_read_only_dictionary is not None, samples
    sorted_read_only_summary = sorted_read_only_dictionary.get("summary", "")
    assert "Count=2 Capacity=4" in sorted_read_only_summary, sorted_read_only_summary
    assert "707: 7007" in sorted_read_only_summary and "909: 9009" in sorted_read_only_summary, (
        sorted_read_only_summary
    )
    assert "808" not in sorted_read_only_summary and "8008" not in sorted_read_only_summary, (
        sorted_read_only_summary
    )

    custom_read_only_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.ObjectModel.ReadOnlyDictionary<System.String, System.String>"
        ),
        None,
    )
    assert custom_read_only_dictionary is not None, samples
    assert "Backing=FixtureDictionary<System.String, System.String>" in custom_read_only_dictionary.get(
        "summary", ""
    ), custom_read_only_dictionary
    assert "<partial>" in custom_read_only_dictionary.get("summary", ""), custom_read_only_dictionary

    immutable_array = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableArray<System.Object>"
        ),
        None,
    )
    assert immutable_array is not None, samples
    immutable_array_summary = immutable_array.get("summary", "")
    assert immutable_array_summary.startswith("Count=4 ["), immutable_array_summary
    assert "maze-immutable-array-first" in immutable_array_summary, immutable_array_summary
    assert "GraphNode" in immutable_array_summary and "null" in immutable_array_summary, immutable_array_summary
    assert "maze-immutable-array-last" in immutable_array_summary, immutable_array_summary

    default_immutable_array = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableArray<System.String>"
        ),
        None,
    )
    assert default_immutable_array is not None, samples
    assert default_immutable_array.get("summary") == (
        "Count=<unavailable> Array=<uninitialized> <partial>"
    ), default_immutable_array

    immutable_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableList<System.Object>"
        ),
        None,
    )
    assert immutable_list is not None, samples
    immutable_list_summary = immutable_list.get("summary", "")
    assert "Count=6 InOrder" in immutable_list_summary, immutable_list_summary
    for value in [
        "maze-immutable-list-first",
        "GraphNode",
        "null",
        "maze-immutable-list-shared",
        "maze-immutable-list-last",
    ]:
        assert value in immutable_list_summary, (value, immutable_list_summary)
    assert "maze-immutable-list-removed" not in immutable_list_summary, immutable_list_summary
    assert immutable_list_summary.index("maze-immutable-list-first") < immutable_list_summary.index("GraphNode"), (
        immutable_list_summary
    )
    assert immutable_list_summary.index("null") < immutable_list_summary.index("maze-immutable-list-last"), (
        immutable_list_summary
    )

    primitive_immutable_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableList<System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_list is not None, samples
    assert primitive_immutable_list.get("summary") == "Count=3 InOrder [111, 333, 444]", primitive_immutable_list

    partial_immutable_list = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableList<System.String>"
        ),
        None,
    )
    assert partial_immutable_list is not None, samples
    assert "Count=3 InOrder" in partial_immutable_list.get("summary", ""), partial_immutable_list
    assert "<partial>" in partial_immutable_list.get("summary", ""), partial_immutable_list

    immutable_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableDictionary<System.String, System.Object>"
        ),
        None,
    )
    assert immutable_dictionary is not None, samples
    immutable_dictionary_summary = immutable_dictionary.get("summary", "")
    assert "Count=5 HashOrder" in immutable_dictionary_summary, immutable_dictionary_summary
    for value in [
        "maze-immutable-dictionary-alpha",
        "maze-immutable-dictionary-value",
        "maze-immutable-dictionary-graph",
        "GraphNode",
        "maze-immutable-dictionary-null",
        "null",
        "maze-immutable-dictionary-shared",
        "maze-immutable-dictionary-new-value",
    ]:
        assert value in immutable_dictionary_summary, (value, immutable_dictionary_summary)
    assert "maze-immutable-dictionary-removed" not in immutable_dictionary_summary, immutable_dictionary_summary
    assert "maze-immutable-dictionary-old-value" not in immutable_dictionary_summary, immutable_dictionary_summary

    primitive_immutable_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableDictionary<System.Int32, System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_dictionary is not None, samples
    assert primitive_immutable_dictionary.get("summary") == "Count=2 HashOrder {101: 1001, 303: 3003}", (
        primitive_immutable_dictionary
    )

    partial_immutable_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableDictionary<System.String, System.String>"
        ),
        None,
    )
    assert partial_immutable_dictionary is not None, samples
    assert "Count=2 HashOrder" in partial_immutable_dictionary.get("summary", ""), partial_immutable_dictionary
    assert "<partial>" in partial_immutable_dictionary.get("summary", ""), partial_immutable_dictionary

    immutable_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableHashSet<System.Object>"
        ),
        None,
    )
    assert immutable_set is not None, samples
    immutable_set_summary = immutable_set.get("summary", "")
    assert "Count=6 HashOrder" in immutable_set_summary, immutable_set_summary
    for value in [
        "maze-immutable-set-first",
        "GraphNode",
        "null",
        "maze-immutable-set-shared",
        "maze-immutable-set-last",
    ]:
        assert value in immutable_set_summary, (value, immutable_set_summary)
    assert "maze-immutable-set-removed" not in immutable_set_summary, immutable_set_summary

    primitive_immutable_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableHashSet<System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_set is not None, samples
    assert primitive_immutable_set.get("summary") == "Count=3 HashOrder {1111, 3333, 4444}", (
        primitive_immutable_set
    )

    partial_immutable_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableHashSet<System.String>"
        ),
        None,
    )
    assert partial_immutable_set is not None, samples
    assert "Count=2 HashOrder" in partial_immutable_set.get("summary", ""), partial_immutable_set
    assert "<partial>" in partial_immutable_set.get("summary", ""), partial_immutable_set

    immutable_queue = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableQueue<System.Object>"
        ),
        None,
    )
    assert immutable_queue is not None, samples
    immutable_queue_summary = immutable_queue.get("summary", "")
    assert "Count=4 FrontToBack" in immutable_queue_summary, immutable_queue_summary
    assert "maze-immutable-queue-first" in immutable_queue_summary, immutable_queue_summary
    assert "GraphNode" in immutable_queue_summary and "null" in immutable_queue_summary, immutable_queue_summary
    assert "maze-immutable-queue-last" in immutable_queue_summary, immutable_queue_summary
    assert "maze-immutable-queue-removed" not in immutable_queue_summary, immutable_queue_summary
    assert immutable_queue_summary.index("maze-immutable-queue-first") < immutable_queue_summary.index("GraphNode"), (
        immutable_queue_summary
    )
    assert immutable_queue_summary.index("null") < immutable_queue_summary.index("maze-immutable-queue-last"), (
        immutable_queue_summary
    )

    primitive_immutable_queue = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableQueue<System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_queue is not None, samples
    assert primitive_immutable_queue.get("summary") == "Count=3 FrontToBack [222, 333, 444]", (
        primitive_immutable_queue
    )

    immutable_stack = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableStack<System.Object>"
        ),
        None,
    )
    assert immutable_stack is not None, samples
    immutable_stack_summary = immutable_stack.get("summary", "")
    assert "Count=4 TopToBottom" in immutable_stack_summary, immutable_stack_summary
    assert "maze-immutable-stack-top" in immutable_stack_summary, immutable_stack_summary
    assert "null" in immutable_stack_summary and "GraphNode" in immutable_stack_summary, immutable_stack_summary
    assert "maze-immutable-stack-bottom" in immutable_stack_summary, immutable_stack_summary
    assert immutable_stack_summary.index("maze-immutable-stack-top") < immutable_stack_summary.index("null"), (
        immutable_stack_summary
    )
    assert immutable_stack_summary.index("GraphNode") < immutable_stack_summary.index(
        "maze-immutable-stack-bottom"
    ), immutable_stack_summary

    primitive_immutable_stack = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableStack<System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_stack is not None, samples
    assert primitive_immutable_stack.get("summary") == "Count=3 TopToBottom [333, 222, 111]", (
        primitive_immutable_stack
    )

    immutable_sorted_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedDictionary<System.String, System.Object>"
        ),
        None,
    )
    assert immutable_sorted_dictionary is not None, samples
    immutable_sorted_dictionary_summary = immutable_sorted_dictionary.get("summary", "")
    assert "Count=5 ComparerOrder" in immutable_sorted_dictionary_summary, immutable_sorted_dictionary_summary
    for value in [
        "maze-immutable-sorted-dictionary-alpha",
        "maze-immutable-sorted-dictionary-value",
        "maze-immutable-sorted-dictionary-graph",
        "GraphNode",
        "maze-immutable-sorted-dictionary-null",
        "null",
        "maze-immutable-sorted-dictionary-shared",
        "maze-immutable-sorted-dictionary-updated",
        "maze-immutable-sorted-dictionary-new-value",
    ]:
        assert value in immutable_sorted_dictionary_summary, (value, immutable_sorted_dictionary_summary)
    assert "maze-immutable-sorted-dictionary-removed" not in immutable_sorted_dictionary_summary, (
        immutable_sorted_dictionary_summary
    )
    assert "maze-immutable-sorted-dictionary-old-value" not in immutable_sorted_dictionary_summary, (
        immutable_sorted_dictionary_summary
    )
    assert immutable_sorted_dictionary_summary.index(
        "maze-immutable-sorted-dictionary-alpha"
    ) < immutable_sorted_dictionary_summary.index("maze-immutable-sorted-dictionary-graph"), (
        immutable_sorted_dictionary_summary
    )
    assert immutable_sorted_dictionary_summary.index(
        "maze-immutable-sorted-dictionary-graph"
    ) < immutable_sorted_dictionary_summary.index("maze-immutable-sorted-dictionary-null"), (
        immutable_sorted_dictionary_summary
    )

    primitive_immutable_sorted_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedDictionary<System.Int32, System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_sorted_dictionary is not None, samples
    assert primitive_immutable_sorted_dictionary.get("summary") == (
        "Count=2 ComparerOrder {101: 1001, 303: 3003}"
    ), primitive_immutable_sorted_dictionary

    partial_immutable_sorted_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedDictionary<System.String, System.String>"
        ),
        None,
    )
    assert partial_immutable_sorted_dictionary is not None, samples
    assert "Count=2 ComparerOrder" in partial_immutable_sorted_dictionary.get("summary", ""), (
        partial_immutable_sorted_dictionary
    )
    assert "<partial>" in partial_immutable_sorted_dictionary.get("summary", ""), (
        partial_immutable_sorted_dictionary
    )

    cycle_immutable_sorted_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedDictionary<System.Int64, System.String>"
        ),
        None,
    )
    assert cycle_immutable_sorted_dictionary is not None, samples
    assert "maze-immutable-sorted-dictionary-cycle-partial" in cycle_immutable_sorted_dictionary.get(
        "summary", ""
    ), cycle_immutable_sorted_dictionary
    assert "<partial>" in cycle_immutable_sorted_dictionary.get("summary", ""), (
        cycle_immutable_sorted_dictionary
    )

    immutable_sorted_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableSortedSet<System.Object>"
        ),
        None,
    )
    assert immutable_sorted_set is not None, samples
    immutable_sorted_set_summary = immutable_sorted_set.get("summary", "")
    assert "Count=6 ComparerOrder" in immutable_sorted_set_summary, immutable_sorted_set_summary
    for value in [
        "null",
        "maze-immutable-sorted-set-first",
        "maze-immutable-sorted-set-last",
        "maze-immutable-sorted-set-shared",
        "GraphNode",
    ]:
        assert value in immutable_sorted_set_summary, (value, immutable_sorted_set_summary)
    assert "maze-immutable-sorted-set-removed" not in immutable_sorted_set_summary, immutable_sorted_set_summary
    assert immutable_sorted_set_summary.index("null") < immutable_sorted_set_summary.index(
        "maze-immutable-sorted-set-first"
    ), immutable_sorted_set_summary
    assert immutable_sorted_set_summary.index(
        "maze-immutable-sorted-set-first"
    ) < immutable_sorted_set_summary.index("GraphNode"), immutable_sorted_set_summary

    primitive_immutable_sorted_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableSortedSet<System.Int32>"
        ),
        None,
    )
    assert primitive_immutable_sorted_set is not None, samples
    assert primitive_immutable_sorted_set.get("summary") == (
        "Count=3 ComparerOrder {1111, 3333, 4444}"
    ), primitive_immutable_sorted_set

    partial_immutable_sorted_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableSortedSet<System.String>"
        ),
        None,
    )
    assert partial_immutable_sorted_set is not None, samples
    assert "Count=2 ComparerOrder" in partial_immutable_sorted_set.get("summary", ""), (
        partial_immutable_sorted_set
    )
    assert "<partial>" in partial_immutable_sorted_set.get("summary", ""), partial_immutable_sorted_set

    cycle_immutable_sorted_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Immutable.ImmutableSortedSet<System.Int64>"
        ),
        None,
    )
    assert cycle_immutable_sorted_set is not None, samples
    assert "Count=1 ComparerOrder" in cycle_immutable_sorted_set.get("summary", ""), (
        cycle_immutable_sorted_set
    )
    assert "<partial>" in cycle_immutable_sorted_set.get("summary", ""), cycle_immutable_sorted_set

    immutable_array_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableArray<System.Object>+Builder"
        ),
        None,
    )
    assert immutable_array_builder is not None, samples
    immutable_array_builder_summary = immutable_array_builder.get("summary", "")
    assert "Count=4 Capacity=8" in immutable_array_builder_summary, immutable_array_builder_summary
    for value in [
        "maze-immutable-array-builder-first",
        "GraphNode",
        "null",
        "maze-immutable-array-builder-last",
    ]:
        assert value in immutable_array_builder_summary, (value, immutable_array_builder_summary)
    assert immutable_array_builder_summary.index(
        "maze-immutable-array-builder-first"
    ) < immutable_array_builder_summary.index("GraphNode"), immutable_array_builder_summary
    assert immutable_array_builder_summary.index("null") < immutable_array_builder_summary.index(
        "maze-immutable-array-builder-last"
    ), immutable_array_builder_summary

    partial_immutable_array_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableArray<System.String>+Builder"
        ),
        None,
    )
    assert partial_immutable_array_builder is not None, samples
    assert partial_immutable_array_builder.get("summary") == (
        "Count=2 Capacity=<unavailable> <partial>"
    ), partial_immutable_array_builder

    immutable_list_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableList<System.Object>+Builder"
        ),
        None,
    )
    assert immutable_list_builder is not None, samples
    immutable_list_builder_summary = immutable_list_builder.get("summary", "")
    assert "Count=4 InOrder" in immutable_list_builder_summary, immutable_list_builder_summary
    for value in [
        "maze-immutable-list-builder-first",
        "GraphNode",
        "null",
        "maze-immutable-list-builder-last",
    ]:
        assert value in immutable_list_builder_summary, (value, immutable_list_builder_summary)
    assert immutable_list_builder_summary.index(
        "maze-immutable-list-builder-first"
    ) < immutable_list_builder_summary.index("GraphNode"), immutable_list_builder_summary
    assert immutable_list_builder_summary.index("null") < immutable_list_builder_summary.index(
        "maze-immutable-list-builder-last"
    ), immutable_list_builder_summary

    immutable_dictionary_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableDictionary<System.String, System.Object>+Builder"
        ),
        None,
    )
    assert immutable_dictionary_builder is not None, samples
    immutable_dictionary_builder_summary = immutable_dictionary_builder.get("summary", "")
    assert "Count=4 HashOrder" in immutable_dictionary_builder_summary, immutable_dictionary_builder_summary
    for value in [
        "maze-immutable-dictionary-builder-alpha",
        "maze-immutable-dictionary-builder-value",
        "maze-immutable-dictionary-builder-graph",
        "GraphNode",
        "maze-immutable-dictionary-builder-null",
        "null",
        "maze-immutable-dictionary-builder-updated",
        "maze-immutable-dictionary-builder-new-value",
    ]:
        assert value in immutable_dictionary_builder_summary, (value, immutable_dictionary_builder_summary)
    assert "<partial>" not in immutable_dictionary_builder_summary, immutable_dictionary_builder_summary
    assert "maze-immutable-dictionary-builder-removed" not in immutable_dictionary_builder_summary, (
        immutable_dictionary_builder_summary
    )
    assert "maze-immutable-dictionary-builder-old-value" not in immutable_dictionary_builder_summary, (
        immutable_dictionary_builder_summary
    )

    partial_immutable_dictionary_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableDictionary<System.Int64, System.String>+Builder"
        ),
        None,
    )
    assert partial_immutable_dictionary_builder is not None, samples
    assert "Count=2 HashOrder" in partial_immutable_dictionary_builder.get("summary", ""), (
        partial_immutable_dictionary_builder
    )
    assert "<partial>" in partial_immutable_dictionary_builder.get("summary", ""), (
        partial_immutable_dictionary_builder
    )

    immutable_set_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableHashSet<System.Object>+Builder"
        ),
        None,
    )
    assert immutable_set_builder is not None, samples
    immutable_set_builder_summary = immutable_set_builder.get("summary", "")
    assert "Count=4 HashOrder" in immutable_set_builder_summary, immutable_set_builder_summary
    for value in [
        "null",
        "maze-immutable-set-builder-first",
        "GraphNode",
        "maze-immutable-set-builder-last",
    ]:
        assert value in immutable_set_builder_summary, (value, immutable_set_builder_summary)
    assert "maze-immutable-set-builder-removed" not in immutable_set_builder_summary, immutable_set_builder_summary

    immutable_sorted_dictionary_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedDictionary<System.String, System.Object>+Builder"
        ),
        None,
    )
    assert immutable_sorted_dictionary_builder is not None, samples
    immutable_sorted_dictionary_builder_summary = immutable_sorted_dictionary_builder.get("summary", "")
    assert "Count=4 ComparerOrder" in immutable_sorted_dictionary_builder_summary, (
        immutable_sorted_dictionary_builder_summary
    )
    for value in [
        "maze-immutable-sorted-dictionary-builder-alpha",
        "maze-immutable-sorted-dictionary-builder-value",
        "maze-immutable-sorted-dictionary-builder-graph",
        "GraphNode",
        "maze-immutable-sorted-dictionary-builder-null",
        "null",
        "maze-immutable-sorted-dictionary-builder-updated",
        "maze-immutable-sorted-dictionary-builder-new-value",
    ]:
        assert value in immutable_sorted_dictionary_builder_summary, (
            value,
            immutable_sorted_dictionary_builder_summary,
        )
    assert "maze-immutable-sorted-dictionary-builder-removed" not in immutable_sorted_dictionary_builder_summary, (
        immutable_sorted_dictionary_builder_summary
    )
    assert "maze-immutable-sorted-dictionary-builder-old-value" not in (
        immutable_sorted_dictionary_builder_summary
    ), immutable_sorted_dictionary_builder_summary
    assert immutable_sorted_dictionary_builder_summary.index(
        "maze-immutable-sorted-dictionary-builder-alpha"
    ) < immutable_sorted_dictionary_builder_summary.index(
        "maze-immutable-sorted-dictionary-builder-graph"
    ), immutable_sorted_dictionary_builder_summary
    assert immutable_sorted_dictionary_builder_summary.index(
        "maze-immutable-sorted-dictionary-builder-graph"
    ) < immutable_sorted_dictionary_builder_summary.index(
        "maze-immutable-sorted-dictionary-builder-null"
    ), immutable_sorted_dictionary_builder_summary

    immutable_sorted_set_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedSet<System.Object>+Builder"
        ),
        None,
    )
    assert immutable_sorted_set_builder is not None, samples
    immutable_sorted_set_builder_summary = immutable_sorted_set_builder.get("summary", "")
    assert "Count=4 ComparerOrder" in immutable_sorted_set_builder_summary, immutable_sorted_set_builder_summary
    for value in [
        "null",
        "maze-immutable-sorted-set-builder-first",
        "maze-immutable-sorted-set-builder-last",
        "GraphNode",
    ]:
        assert value in immutable_sorted_set_builder_summary, (value, immutable_sorted_set_builder_summary)
    assert "maze-immutable-sorted-set-builder-removed" not in immutable_sorted_set_builder_summary, (
        immutable_sorted_set_builder_summary
    )
    assert immutable_sorted_set_builder_summary.index("null") < immutable_sorted_set_builder_summary.index(
        "maze-immutable-sorted-set-builder-first"
    ), immutable_sorted_set_builder_summary
    assert immutable_sorted_set_builder_summary.index(
        "maze-immutable-sorted-set-builder-first"
    ) < immutable_sorted_set_builder_summary.index(
        "maze-immutable-sorted-set-builder-last"
    ), immutable_sorted_set_builder_summary

    cycle_immutable_sorted_set_builder = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Immutable.ImmutableSortedSet<System.Int64>+Builder"
        ),
        None,
    )
    assert cycle_immutable_sorted_set_builder is not None, samples
    assert "Count=1 ComparerOrder {1701}" in cycle_immutable_sorted_set_builder.get("summary", ""), (
        cycle_immutable_sorted_set_builder
    )
    assert "<partial>" in cycle_immutable_sorted_set_builder.get("summary", ""), (
        cycle_immutable_sorted_set_builder
    )

    frozen_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name", "").startswith(
                "System.Collections.Frozen.OrdinalStringFrozenDictionary_"
            )
            and sample.get("type_name", "").endswith("<System.Object>")
        ),
        None,
    )
    assert frozen_dictionary is not None, samples
    frozen_dictionary_summary = frozen_dictionary.get("summary", "")
    assert "Count=29 FrozenOrder" in frozen_dictionary_summary, frozen_dictionary_summary
    for value in [
        "maze-frozen-dictionary-graph",
        "GraphNode",
        "maze-frozen-dictionary-null",
        "null",
        "maze-frozen-dictionary-shared",
        "maze-frozen-dictionary-updated",
        "maze-frozen-dictionary-new-value",
    ]:
        assert value in frozen_dictionary_summary, (value, frozen_dictionary_summary)
    assert "maze-frozen-dictionary-removed" not in frozen_dictionary_summary, frozen_dictionary_summary
    assert "maze-frozen-dictionary-old-value" not in frozen_dictionary_summary, frozen_dictionary_summary
    assert "<partial>" not in frozen_dictionary_summary, frozen_dictionary_summary

    frozen_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Frozen.DefaultFrozenSet<System.Object>"
        ),
        None,
    )
    assert frozen_set is not None, samples
    frozen_set_summary = frozen_set.get("summary", "")
    assert "Count=25 FrozenOrder" in frozen_set_summary, frozen_set_summary
    assert "null" in frozen_set_summary, frozen_set_summary
    assert "maze-frozen-set-filler-19" in frozen_set_summary, frozen_set_summary
    assert "maze-frozen-set-removed" not in frozen_set_summary, frozen_set_summary
    assert "<partial>" not in frozen_set_summary, frozen_set_summary

    ordinal_frozen_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name", "").startswith("System.Collections.Frozen.OrdinalStringFrozenSet_")
        ),
        None,
    )
    assert ordinal_frozen_set is not None, samples
    assert "Count=24 FrozenOrder" in ordinal_frozen_set.get("summary", ""), ordinal_frozen_set
    assert "maze-frozen-ordinal-set" in ordinal_frozen_set.get("summary", ""), ordinal_frozen_set
    assert "<partial>" not in ordinal_frozen_set.get("summary", ""), ordinal_frozen_set

    int32_frozen_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Frozen.Int32FrozenDictionary<System.Int32>"
        ),
        None,
    )
    assert int32_frozen_dictionary is not None, samples
    int32_frozen_dictionary_summary = int32_frozen_dictionary.get("summary", "")
    assert "Count=20 FrozenOrder" in int32_frozen_dictionary_summary, int32_frozen_dictionary_summary
    assert "101: 1001" in int32_frozen_dictionary_summary, int32_frozen_dictionary_summary
    assert "<partial>" not in int32_frozen_dictionary_summary, int32_frozen_dictionary_summary

    int32_frozen_set = next(
        (sample for sample in samples if sample.get("type_name") == "System.Collections.Frozen.Int32FrozenSet"),
        None,
    )
    assert int32_frozen_set is not None, samples
    assert "Count=20 FrozenOrder" in int32_frozen_set.get("summary", ""), int32_frozen_set
    assert "1111" in int32_frozen_set.get("summary", ""), int32_frozen_set
    assert "<partial>" not in int32_frozen_set.get("summary", ""), int32_frozen_set

    dense_full_frozen_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name", "").startswith(
                "System.Collections.Frozen.DenseIntegralFrozenDictionary+WithFullValues<"
            )
        ),
        None,
    )
    assert dense_full_frozen_dictionary is not None, samples
    assert dense_full_frozen_dictionary.get("summary") == (
        'Count=3 FrozenOrder {0: "maze-frozen-dense-full-zero", '
        '1: "maze-frozen-dense-full-one", 2: "maze-frozen-dense-full-two"}'
    ), dense_full_frozen_dictionary

    dense_optional_frozen_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name", "").startswith(
                "System.Collections.Frozen.DenseIntegralFrozenDictionary+WithOptionalValues<"
            )
        ),
        None,
    )
    assert dense_optional_frozen_dictionary is not None, samples
    assert dense_optional_frozen_dictionary.get("summary") == (
        'Count=3 FrozenOrder {-3: "maze-frozen-dense-optional-minus-three", '
        '0: "maze-frozen-dense-optional-zero", 2: "maze-frozen-dense-optional-two"}'
    ), dense_optional_frozen_dictionary

    partial_frozen_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Frozen.SmallValueTypeComparableFrozenDictionary<System.Guid, System.String>"
        ),
        None,
    )
    assert partial_frozen_dictionary is not None, samples
    assert "Count=2 FrozenOrder" in partial_frozen_dictionary.get("summary", ""), partial_frozen_dictionary
    assert "<partial>" in partial_frozen_dictionary.get("summary", ""), partial_frozen_dictionary

    partial_frozen_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Frozen.SmallValueTypeComparableFrozenSet<System.Int64>"
        ),
        None,
    )
    assert partial_frozen_set is not None, samples
    assert partial_frozen_set.get("summary") == "Count=<unavailable> FrozenOrder <partial>", (
        partial_frozen_set
    )

    empty_frozen_dictionary = next(
        (
            sample
            for sample in samples
            if sample.get("type_name")
            == "System.Collections.Frozen.EmptyFrozenDictionary<System.String, System.String>"
        ),
        None,
    )
    assert empty_frozen_dictionary is not None, samples
    assert empty_frozen_dictionary.get("summary") == "Count=0 FrozenOrder", empty_frozen_dictionary

    empty_frozen_set = next(
        (
            sample
            for sample in samples
            if sample.get("type_name") == "System.Collections.Frozen.EmptyFrozenSet<System.String>"
        ),
        None,
    )
    assert empty_frozen_set is not None, samples
    assert empty_frozen_set.get("summary") == "Count=0 FrozenOrder", empty_frozen_set
    return True

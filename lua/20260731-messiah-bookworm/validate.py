#!/usr/bin/env python3
"""Validate the real H72 Lua/Messiah fixture analysis."""

from __future__ import print_function

import json
import os
import re
import sys


EXPECTED_ITEMS = {
    "<FixturePlayerEntity instance> [Messiah async::logic::entity]": 96,
    "<FixtureNpcEntity instance> [Messiah async::logic::entity]": 64,
    "<FixturePlayerProperties instance> [Messiah async::logic::area_map]": 96,
    "<FixtureNpcProperties instance> [Messiah async::logic::area_map]": 64,
    "<CustomMapType .state instance> [Messiah async::logic::area_map]": 96,
    "<CustomListType .events instance> [Messiah async::logic::area_list]": 96,
    "<CustomMapType .stats.labels instance> [Messiah async::logic::area_map]": 160,
    "<CustomListType .stats.history instance> [Messiah async::logic::area_list]": 160,
    "<CustomMapType .inventory.%d.attributes instance> [Messiah async::logic::area_map]": 192,
    "<CustomMapType .loot.%d.attributes instance> [Messiah async::logic::area_map]": 64,
    "<CustomFloatListType .position instance> [Messiah async::logic::area_list]": 96,
    "<CustomFloatListType .patrol instance> [Messiah async::logic::area_list]": 64,
    "<CustomMapType .blackboard instance> [Messiah async::logic::area_map]": 64,
    "<CustomListType .decisions instance> [Messiah async::logic::area_list]": 64,
    "<ProbeListPropertyRoot instance> [Messiah async::logic::area_map]": 1,
    "<ProbeListWithProps instance> [Messiah async::logic::area_list]": 2,
    "<area_prop_index instance> [Messiah async::logic::area_prop_index_obj]": 6,
}

# Updated after generating the committed fixture from fixture.lua.
EXPECTED_BINDINGS = {
    "async::logic::area_list": 1357,
    "async::logic::area_map": 1800,
    "async::logic::area_prop_index_obj": 6,
    "async::logic::entity": 160,
}
EXPECTED_TOTAL_BINDINGS = 3323


def read_required_file(env_name):
    path = os.environ.get(env_name, "")
    if not path:
        raise AssertionError("%s is not set by testdata/run_test.py" % env_name)
    with open(path, "r") as source:
        return source.read()


def item_by_type(items):
    return {item.get("type", ""): item for item in items}


def validate(data):
    print("=" * 60)
    print("Lua Messiah Bookworm Validation")
    print("=" * 60)

    summary = data.get("summary", {})
    items = data.get("items", [])
    assert summary.get("allocator") == "jemalloc", summary
    assert summary.get("unknown") == 0, "Unknown bytes: %r" % summary.get("unknown")

    indexed = item_by_type(items)
    for name, expected_amount in sorted(EXPECTED_ITEMS.items()):
        item = indexed.get(name)
        assert item is not None, "missing result item: %s" % name
        assert item.get("amount") == expected_amount, "%s amount=%r expected=%d" % (
            name,
            item.get("amount"),
            expected_amount,
        )
        print("PASS %4d %s" % (expected_amount, name))

    for item in items:
        name = item.get("type", "")
        assert "ProbeListWithProps .label" not in name
        assert "ProbeListWithProps .count" not in name

    maze_log = read_required_file("MAZE_TEST_MAZE_LOG")
    maze_output = read_required_file("MAZE_TEST_OUTPUT_LOG")
    for native_type, expected_count in sorted(EXPECTED_BINDINGS.items()):
        pattern = re.compile(
            r"MessiahLuaBindingCount type=%s count=(\d+) shallow_fallback=(\d+)"
            % re.escape(native_type)
        )
        match = pattern.search(maze_log)
        assert match, "missing binding count for %s" % native_type
        assert int(match.group(1)) == expected_count, match.group(0)
        assert int(match.group(2)) == 0, match.group(0)

    total = re.search(
        r"MessiahLuaBindingCount total=(\d+) types=(\d+) shallow_fallback=(\d+)",
        maze_log,
    )
    assert total, "missing total Messiah binding count"
    assert int(total.group(1)) == EXPECTED_TOTAL_BINDINGS, total.group(0)
    assert int(total.group(2)) == 4, total.group(0)
    assert int(total.group(3)) == 0, total.group(0)
    assert "MessiahLuaDeepFallback" not in maze_log
    assert "diff(alloc-mpm)=0B" in maze_log
    assert "CountGoroutineError: 0" in maze_output

    print("PASS binding counts, zero fallback, zero unknown, zero diff")
    print("All validations passed!")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: validate.py maze-result.json")
        sys.exit(2)
    with open(sys.argv[1], "r") as source:
        result = validate(json.load(source))
    sys.exit(0 if result else 1)

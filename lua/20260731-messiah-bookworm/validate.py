#!/usr/bin/env python3
"""Validate the real H72 Lua/Messiah fixture analysis."""

from __future__ import print_function

import json
import os
import re
import sys


EXPECTED_ITEMS = {
    "<FixturePlayerEntity instance> [Messiah async::logic::entity]": (96, 15360),
    "<FixtureNpcEntity instance> [Messiah async::logic::entity]": (64, 10240),
    "<FixtureOnlineEntity instance> [Messiah async::logic::entity]": (16, 2560),
    "<FixtureComplexEntity instance> [Messiah async::logic::entity]": (12, 1920),
    "<FixtureOnlineArea instance> [Messiah async::logic::area]": (16, 68096),
    "<FixtureWorldSpace instance> [Messiah async::logic::space_wrapper]": (1, 128),
    "<FixturePlayerProperties instance> [Messiah async::logic::area_map]": (96, 67584),
    "<FixtureNpcProperties instance> [Messiah async::logic::area_map]": (64, 43008),
    "<FixtureOnlineProperties instance> [Messiah async::logic::area_map]": (16, 10752),
    "<FixtureOnlineNested instance> [Messiah async::logic::area_map]": (17, 7616),
    "<FixtureOnlineNumbers instance> [Messiah async::logic::area_list]": (17, 5680),
    "<FixtureComplexProperties instance> [Messiah async::logic::area_map]": (12, 10752),
    "<FixtureComplexLeaf instance> [Messiah async::logic::area_map]": (288, 175104),
    "<FixtureComplexLeafList instance> [Messiah async::logic::area_list]": (13, 5488),
    "<FixtureComplexLeafMap instance> [Messiah async::logic::area_map]": (13, 15424),
    "<FixtureComplexListMatrix instance> [Messiah async::logic::area_list]": (13, 4720),
    "<FixtureComplexTreeRoot instance> [Messiah async::logic::area_map]": (13, 7488),
    "<FixtureComplexTreeBranch instance> [Messiah async::logic::area_map]": (26, 14976),
    "<FixtureComplexTreeLeaf instance> [Messiah async::logic::area_map]": (50, 27200),
    "<FixtureY2Entity instance> [Messiah async::logic::entity]": (12, 1920),
    "<FixtureY2Properties instance> [Messiah async::logic::area_map]": (12, 9984),
    "<FixtureY2Stat instance> [Messiah async::logic::area_map]": (61, 34160),
    "<FixtureY2ObjNest instance> [Messiah async::logic::area_map]": (25, 14000),
    "<FixtureY2IntMap instance> [Messiah async::logic::area_map]": (49, 21952),
    "<FixtureY2IntList instance> [Messiah async::logic::area_list]": (99, 35472),
    "<FixtureY2ObjDict instance> [Messiah async::logic::area_map]": (13, 5824),
    "<FixtureY2DictDict instance> [Messiah async::logic::area_map]": (13, 5824),
    "<FixtureY2ListDict instance> [Messiah async::logic::area_map]": (13, 5824),
    "<FixtureY2ObjList instance> [Messiah async::logic::area_list]": (13, 4144),
    "<FixtureY2DictList instance> [Messiah async::logic::area_list]": (13, 4144),
    "<FixtureY2ListList instance> [Messiah async::logic::area_list]": (13, 4144),
    "<FixtureY2Equip instance> [Messiah async::logic::area_map]": (48, 28416),
    "<FixtureY2EquipDict instance> [Messiah async::logic::area_map]": (13, 6976),
    "<FixtureY2FormationItem instance> [Messiah async::logic::area_map]": (144, 85248),
    "<FixtureY2Formation instance> [Messiah async::logic::area_map]": (37, 20032),
    "<FixtureY2FormationInfo instance> [Messiah async::logic::area_map]": (36, 20160),
    "<FixtureY2FormationDict instance> [Messiah async::logic::area_map]": (13, 5824),
    "<FixtureY2DerivedRecord instance> [Messiah async::logic::area_map]": (36, 21312),
    "<FixtureY2DerivedRecordList instance> [Messiah async::logic::area_list]": (13, 4720),
    "<CustomMapType .metadata instance> [Messiah async::logic::area_map]": (16, 7168),
    "<CustomMapType .state instance> [Messiah async::logic::area_map]": (96, 43008),
    "<CustomListType .events instance> [Messiah async::logic::area_list]": (96, 32256),
    "<CustomMapType .stats.labels instance> [Messiah async::logic::area_map]": (160, 71680),
    "<CustomListType .stats.history instance> [Messiah async::logic::area_list]": (160, 53760),
    "<CustomMapType .inventory.%d.attributes instance> [Messiah async::logic::area_map]": (192, 86016),
    "<CustomMapType .loot.%d.attributes instance> [Messiah async::logic::area_map]": (64, 28672),
    "<CustomMapType .equips.equip-1.attributes instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .equips.equip-2.attributes instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .equips.equip-3.attributes instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .equips.equip-4.attributes instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .extensions instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .extensions.audit instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomFloatListType .position instance> [Messiah async::logic::area_list]": (96, 35328),
    "<CustomFloatListType .patrol instance> [Messiah async::logic::area_list]": (64, 21504),
    "<CustomMapType .blackboard instance> [Messiah async::logic::area_map]": (64, 28672),
    "<CustomListType .decisions instance> [Messiah async::logic::area_list]": (64, 21504),
    "<CustomMapType .empty_map instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .single_map instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .mixed_map instance> [Messiah async::logic::area_map]": (12, 6528),
    "<CustomMapType .nested_map instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .nested_map.level1 instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .nested_map.level1.level2 instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .nested_map.level1.level2.level3 instance> [Messiah async::logic::area_map]": (12, 5376),
    "<CustomMapType .growth_map instance> [Messiah async::logic::area_map]": (12, 90240),
    "<CustomListType .empty_list instance> [Messiah async::logic::area_list]": (12, 3648),
    "<CustomListType .single_list instance> [Messiah async::logic::area_list]": (12, 3840),
    "<CustomListType .mixed_list instance> [Messiah async::logic::area_list]": (12, 4416),
    "<CustomListType .nested_lists instance> [Messiah async::logic::area_list]": (12, 4416),
    "<CustomListType .nested_lists.%d instance> [Messiah async::logic::area_list]": (36, 13248),
    "<CustomListType .growth_list instance> [Messiah async::logic::area_list]": (12, 52800),
    "<CustomMapType .leaves.%d.metadata instance> [Messiah async::logic::area_map]": (96, 43008),
    "<CustomMapType .leaf_lookup.map-leaf-16.metadata instance> [Messiah async::logic::area_map]": (12, 5376),
    "<ProbeListPropertyRoot instance> [Messiah async::logic::area_map]": (1, 528),
    "<ProbeListWithProps instance> [Messiah async::logic::area_list]": (2, 624),
    "<area_prop_index instance> [Messiah async::logic::area_prop_index_obj]": (20, 4160),
}

# Updated after generating the committed fixture from fixture.lua.
EXPECTED_BINDINGS = {
    "async::logic::area": 16,
    "async::logic::area_list": 1977,
    "async::logic::area_map": 3229,
    "async::logic::area_prop_index_obj": 20,
    "async::logic::entity": 200,
    "async::logic::space_wrapper": 1,
}
EXPECTED_TOTAL_BINDINGS = 5443


def read_required_file(env_name):
    path = os.environ.get(env_name, "")
    if not path:
        raise AssertionError("%s is not set by testdata/run_test.py" % env_name)
    with open(path, "r") as source:
        return source.read()


def item_by_type(items):
    indexed = {}
    for item in items:
        indexed.setdefault(item.get("type", ""), []).append(item)
    return indexed


def validate(data):
    print("=" * 60)
    print("Lua Messiah Bookworm Validation")
    print("=" * 60)

    summary = data.get("summary", {})
    items = data.get("items", [])
    assert summary.get("allocator") == "jemalloc", summary
    assert summary.get("unknown") == 0, "Unknown bytes: %r" % summary.get("unknown")

    indexed = item_by_type(items)
    for name, expected in sorted(EXPECTED_ITEMS.items()):
        matches = indexed.get(name, [])
        assert matches, "missing result item: %s" % name
        assert len(matches) == 1, "duplicate result items for %s: %d" % (name, len(matches))
        item = matches[0]
        expected_amount, expected_size = expected
        assert item.get("amount") == expected_amount, "%s amount=%r expected=%d" % (
            name,
            item.get("amount"),
            expected_amount,
        )
        assert item.get("total_size") == expected_size, "%s total_size=%r expected=%d" % (
            name,
            item.get("total_size"),
            expected_size,
        )
        print("PASS %4d %8dB %s" % (expected_amount, expected_size, name))

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
    assert int(total.group(2)) == 6, total.group(0)
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

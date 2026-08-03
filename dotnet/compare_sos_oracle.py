#!/usr/bin/env python3
from __future__ import print_function

import argparse
from collections import Counter
import json
import re
import subprocess


STAT_LINE = re.compile(r"^\s*[0-9a-fA-F]+\s+([0-9,]+)\s+([0-9,]+)\s+(.+?)\s*$")
COMMITTED_LINE = re.compile(r"GC Committed Heap Size:.*\(([0-9]+)\) bytes")
HANDLE_COUNT_LINE = re.compile(r"^\s*(Strong|Pinned|Dependent) Handles:\s+([0-9,]+)\s*$")
DEPENDENT_ROW = re.compile(
    r"^\s*[0-9a-fA-F]+\s+Dependent\s+[0-9a-fA-F]+\s+[0-9,]+\s+([0-9a-fA-F]+)\s+"
)


def read_json(path):
    with open(path, "r") as source:
        return json.load(source)


def run_sos(dotnet_dump, dump_path):
    command = [
        dotnet_dump,
        "analyze",
        dump_path,
        "-c",
        "dumpheap -stat",
        "-c",
        "eeheap -gc",
        "-c",
        "gchandles",
        "-c",
        "exit",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError("dotnet-dump failed with exit %d:\n%s" % (result.returncode, result.stdout))
    return result.stdout


def parse_sos(output):
    type_stats = []
    in_heap_stats = False
    object_count = None
    shallow_bytes = None
    committed_bytes = None
    handle_counts = {}
    dependent_targets = 0

    for line in output.splitlines():
        if "MT Count TotalSize Class Name" in line and object_count is None:
            in_heap_stats = True
            continue
        if in_heap_stats:
            total = re.match(r"^Total\s+([0-9,]+) objects,\s+([0-9,]+) bytes", line)
            if total:
                object_count = int(total.group(1).replace(",", ""))
                shallow_bytes = int(total.group(2).replace(",", ""))
                in_heap_stats = False
                continue
            match = STAT_LINE.match(line)
            if match:
                type_stats.append((
                    match.group(3),
                    int(match.group(1).replace(",", "")),
                    int(match.group(2).replace(",", "")),
                ))

        committed = COMMITTED_LINE.search(line)
        if committed:
            committed_bytes = int(committed.group(1))
        handle_count = HANDLE_COUNT_LINE.match(line)
        if handle_count:
            handle_counts[handle_count.group(1).lower()] = int(handle_count.group(2).replace(",", ""))
        dependent = DEPENDENT_ROW.match(line)
        if dependent and int(dependent.group(1), 16) != 0:
            dependent_targets += 1

    if object_count is None or shallow_bytes is None or committed_bytes is None:
        raise AssertionError("SOS output omitted heap totals or GC committed bytes")
    return {
        "types": Counter(type_stats),
        "object_count": object_count,
        "shallow_bytes": shallow_bytes,
        "committed_bytes": committed_bytes,
        "handle_counts": handle_counts,
        "dependent_targets": dependent_targets,
    }


def maze_type_stats(data):
    result = []
    for item in data.get("items") or []:
        name = item.get("type", "")
        if not name.startswith("C# "):
            continue
        name = name[3:]
        if name.startswith("(free) "):
            name = name[len("(free) "):]
        result.append((name, item.get("amount"), item.get("total_size")))
    return Counter(result)


def compare(data, oracle):
    dotnet = data.get("dotnet") or {}
    failures = []
    for field, oracle_field in (
        ("object_count", "object_count"),
        ("shallow_bytes", "shallow_bytes"),
        ("gc_committed_bytes", "committed_bytes"),
    ):
        if dotnet.get(field) != oracle[oracle_field]:
            failures.append("%s Maze=%r SOS=%r" % (field, dotnet.get(field), oracle[oracle_field]))

    actual_types = maze_type_stats(data)
    if actual_types != oracle["types"]:
        missing = list((oracle["types"] - actual_types).elements())[:10]
        extra = list((actual_types - oracle["types"]).elements())[:10]
        failures.append("managed type stats differ; missing=%r extra=%r" % (missing, extra))

    root_kinds = dotnet.get("root_kinds") or {}
    for maze_kind, sos_kind in (("strong_handle", "strong"), ("pinned_handle", "pinned")):
        if root_kinds.get(maze_kind, 0) != oracle["handle_counts"].get(sos_kind, 0):
            failures.append(
                "%s Maze=%r SOS=%r"
                % (maze_kind, root_kinds.get(maze_kind, 0), oracle["handle_counts"].get(sos_kind, 0))
            )
    dependent_edges = (dotnet.get("reference_kinds") or {}).get("dependent_handle", 0)
    if dependent_edges != oracle["dependent_targets"]:
        failures.append(
            "dependent_handle Maze=%r SOS non-null-target=%r"
            % (dependent_edges, oracle["dependent_targets"])
        )
    if failures:
        raise AssertionError("SOS oracle mismatch:\n- " + "\n- ".join(failures))


def main():
    parser = argparse.ArgumentParser(description="Compare Maze managed results with official SOS commands")
    parser.add_argument("--dotnet-dump", required=True)
    parser.add_argument("--dump", required=True)
    parser.add_argument("--maze-result", required=True)
    args = parser.parse_args()

    oracle = parse_sos(run_sos(args.dotnet_dump, args.dump))
    compare(read_json(args.maze_result), oracle)
    print(
        "PASS SOS oracle: %d objects, %d bytes, %d type rows, %d committed bytes"
        % (
            oracle["object_count"],
            oracle["shallow_bytes"],
            sum(oracle["types"].values()),
            oracle["committed_bytes"],
        )
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import print_function

import json
import os
import sys


def load(path):
    with open(path, "r") as source:
        return json.load(source)


def normalized_module(module):
    return {
        "runtime_id": module.get("runtime_id"),
        "name": os.path.basename(module.get("name", "")),
        "assembly_name": os.path.basename(module.get("assembly_name", "")),
        "is_dynamic": module.get("is_dynamic"),
        "is_pe_file": module.get("is_pe_file"),
        "layout": module.get("layout"),
        "size": module.get("size"),
        "metadata_length": module.get("metadata_length"),
        "mvid": module.get("mvid"),
        "file_bytes": module.get("file_bytes"),
        "file_sha256": module.get("file_sha256"),
    }


def normalized_runtime(runtime):
    return {
        "id": runtime.get("id"),
        "version": runtime.get("version"),
        "build_id": runtime.get("build_id"),
        "dac_build_id": runtime.get("dac_build_id"),
        "product_version": runtime.get("product_version"),
        "product_commit": runtime.get("product_commit"),
        "server_gc": runtime.get("server_gc"),
        "logical_heaps": runtime.get("logical_heaps"),
        "segments": runtime.get("segments"),
        "modules": runtime.get("modules"),
    }


def normalize(data):
    dotnet = data.get("dotnet") or {}
    managed_items = [
        {
            "type": item.get("type"),
            "amount": item.get("amount"),
            "total_size": item.get("total_size"),
            "avg_size": item.get("avg_size"),
        }
        for item in data.get("items") or []
        if item.get("type", "").startswith("C# ")
    ]
    managed_items.sort(key=lambda item: (
        item["type"],
        item["amount"],
        item["total_size"],
        item["avg_size"],
    ))
    modules = [normalized_module(module) for module in dotnet.get("modules") or []]
    modules.sort(key=lambda module: (
        module["runtime_id"],
        module["name"],
        module["assembly_name"],
        module["mvid"],
        module["layout"],
    ))
    runtimes = [normalized_runtime(runtime) for runtime in dotnet.get("runtimes") or []]
    runtimes.sort(key=lambda runtime: runtime["id"])
    return {
        "mode": dotnet.get("mode"),
        "runtime_count": dotnet.get("runtime_count"),
        "module_metadata_complete": dotnet.get("module_metadata_complete"),
        "module_count": dotnet.get("module_count"),
        "type_count": dotnet.get("type_count"),
        "segment_count": dotnet.get("segment_count"),
        "object_count": dotnet.get("object_count"),
        "reference_count": dotnet.get("reference_count"),
        "root_count": dotnet.get("root_count"),
        "shallow_bytes": dotnet.get("shallow_bytes"),
        "gc_committed_bytes": dotnet.get("gc_committed_bytes"),
        "gc_reserved_bytes": dotnet.get("gc_reserved_bytes"),
        "segment_kinds": dotnet.get("segment_kinds") or {},
        "segment_logical_heaps": dotnet.get("segment_logical_heaps") or {},
        "object_generations": dotnet.get("object_generations") or {},
        "reference_kinds": dotnet.get("reference_kinds") or {},
        "root_kinds": dotnet.get("root_kinds") or {},
        "runtimes": runtimes,
        "modules": modules,
        "managed_items": managed_items,
    }


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: compare_normalized.py <first-maze-result.json> <second-maze-result.json>")
    first = normalize(load(argv[1]))
    second = normalize(load(argv[2]))
    if first != second:
        first_path = argv[1] + ".normalized.json"
        second_path = argv[2] + ".normalized.json"
        with open(first_path, "w") as destination:
            json.dump(first, destination, indent=2, sort_keys=True)
        with open(second_path, "w") as destination:
            json.dump(second, destination, indent=2, sort_keys=True)
        raise AssertionError(
            "normalized managed results differ; inspect %s and %s" % (first_path, second_path)
        )
    print(
        "PASS deterministic managed result: %d objects, %d types, %d modules, %d refs, %d roots"
        % (
            first["object_count"],
            first["type_count"],
            first["module_count"],
            first["reference_count"],
            first["root_count"],
        )
    )


if __name__ == "__main__":
    main(sys.argv)

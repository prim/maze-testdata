#!/usr/bin/env python3


def validate(data):
    summary = data.get("summary", {})
    result = data.get("go", {})
    runtime = result.get("runtime", {})
    counts = result.get("counts", {})
    classes = result.get("classes", [])
    items = data.get("items", [])

    assert summary.get("allocator") == "ptmalloc", "cgo fixture did not select ptmalloc"
    assert result.get("schema") == "maze.gocore.api/v1", "unexpected Go API schema"
    assert runtime.get("goos") == "linux" and runtime.get("goarch") == "amd64", "unexpected runtime target"
    assert runtime.get("pointer_size") == 8, "unexpected pointer size"

    stats = {tuple(record["path"]): record["bytes"] for record in result.get("stats", [])}
    alloc = stats[("all", "heap", "in use spans", "alloc")]
    live = stats[("all", "heap", "in use spans", "alloc", "live")]
    garbage = stats[("all", "heap", "in use spans", "alloc", "garbage")]
    assert alloc == live + garbage, "alloc != live + garbage"
    assert sum(record["bytes"] for record in classes) == live, "class bytes != live bytes"
    assert counts.get("dominator") == 1 + counts.get("root", 0) + counts.get("object", 0), "incomplete dominator tree"

    by_name = {record["name"]: record for record in classes}
    nodes = by_name.get("main.Node")
    assert nodes is not None and nodes.get("amount") == 128 and nodes.get("bytes") == 6144, "main.Node changed"
    large = by_name.get("[8388608]uint8")
    assert large is not None and large.get("amount") == 1 and large.get("bytes") == 8388608, "Go large array missing"
    payload = by_name.get("[8192]uint8")
    assert payload is not None and payload.get("amount") == 128 and payload.get("bytes") == 1048576, "Go payload arrays missing"
    cgo_callers = by_name.get("runtime.cgoCallers")
    assert cgo_callers is not None and cgo_callers.get("amount", 0) > 0, "cgo stack metadata missing"

    native_large = [item for item in items if item.get("type") == "malloc(25169904)"]
    assert len(native_large) == 1 and native_large[0].get("amount") == 1, "24 MiB native allocation missing"
    native_small = [item for item in items if item.get("type") == "malloc(1032)"]
    assert len(native_small) == 1 and native_small[0].get("amount") == 4096, "native small allocations missing"
    assert counts.get("goroutine", 0) >= 2, "cgo-blocked goroutine missing"

    print("Go cgo fixture validated: version=%s live=%d native_large=%d native_small=%d goroutines=%d" % (
        runtime.get("go_version"), live, native_large[0]["total_size"],
        native_small[0]["amount"], counts.get("goroutine", 0),
    ))
    return True


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], "r") as stream:
        payload = json.load(stream)
    raise SystemExit(0 if validate(payload) else 1)

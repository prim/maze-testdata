#!/usr/bin/env python3


def validate_fixture(data, expected_version):
    assert "summary" in data, "missing summary"
    assert "go" in data, "missing Go analysis"
    result = data["go"]
    runtime = result.get("runtime", {})
    counts = result.get("counts", {})
    classes = result.get("classes", [])

    assert result.get("schema") == "maze.gocore.api/v1", "unexpected Go API schema"
    assert result.get("protocol_schema") == "maze.gocore.ndjson/v1", "unexpected helper schema"
    assert runtime.get("go_version") == expected_version, "unexpected Go version"
    assert runtime.get("goos") == "linux", "unexpected GOOS"
    assert runtime.get("goarch") == "amd64", "unexpected GOARCH"
    assert runtime.get("pointer_size") == 8, "unexpected pointer size"
    assert runtime.get("byte_order") == "LittleEndian", "unexpected byte order"

    stats = {tuple(record["path"]): record["bytes"] for record in result.get("stats", [])}
    alloc = stats[("all", "heap", "in use spans", "alloc")]
    live = stats[("all", "heap", "in use spans", "alloc", "live")]
    garbage = stats[("all", "heap", "in use spans", "alloc", "garbage")]
    assert alloc == live + garbage, "alloc != live + garbage"
    assert garbage >= 2 * 1024 * 1024, "unreachable Blob garbage was not retained"
    assert sum(record["bytes"] for record in classes) == live, "class bytes != live bytes"
    assert counts.get("dominator") == 1 + counts.get("root", 0) + counts.get("object", 0), "incomplete dominator tree"

    by_name = {record["name"]: record for record in classes}
    nodes = by_name.get("main.Node")
    assert nodes is not None, "main.Node class missing"
    assert nodes.get("amount") == 256, "main.Node count changed"
    assert nodes.get("bytes") == 20480, "main.Node bytes changed"

    large = by_name.get("[3145728]uint8")
    assert large is not None, "3 MiB backing array missing"
    assert large.get("amount") == 1 and large.get("bytes") == 3145728, "3 MiB backing array changed"

    payloads = [
        record for record in classes
        if record.get("type_kind") == "KindUint"
        and record.get("element_size") == 1
        and record.get("repeat") in (4096, 4097, 4098, 4099)
    ]
    assert sum(record.get("amount", 0) for record in payloads) == 256, "payload backing-array count changed"
    assert counts.get("goroutine", 0) >= 2, "parked stack-root goroutine missing"

    print("Go runtime matrix fixture validated: version=%s live=%d garbage=%d objects=%d roots=%d edges=%d" % (
        runtime.get("go_version"), live, garbage, counts.get("object", 0),
        counts.get("root", 0), counts.get("edge", 0),
    ))
    return True

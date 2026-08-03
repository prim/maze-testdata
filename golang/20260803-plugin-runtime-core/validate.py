#!/usr/bin/env python3


def validate(data):
    result = data.get("go", {})
    runtime = result.get("runtime", {})
    counts = result.get("counts", {})
    classes = result.get("classes", [])
    goroutines = result.get("goroutines", [])

    assert result.get("schema") == "maze.gocore.api/v1", "unexpected Go API schema"
    assert result.get("protocol_schema") == "maze.gocore.ndjson/v1", "unexpected helper schema"
    assert runtime.get("goos") == "linux" and runtime.get("goarch") == "amd64", "unexpected target"
    assert counts.get("dominator") == 1 + counts.get("root", 0) + counts.get("object", 0), "incomplete dominator tree"

    stats = {tuple(record["path"]): record["bytes"] for record in result.get("stats", [])}
    alloc = stats[("all", "heap", "in use spans", "alloc")]
    live = stats[("all", "heap", "in use spans", "alloc", "live")]
    garbage = stats[("all", "heap", "in use spans", "alloc", "garbage")]
    assert alloc == live + garbage, "alloc != live + garbage"
    assert sum(record["bytes"] for record in classes) == live, "class bytes != live bytes"

    plugin_nodes = [
        record for record in classes
        if record.get("name", "").endswith(".PluginNode")
        and record.get("type_kind") == "KindStruct"
        and record.get("object_size") == 80
        and record.get("element_size") == 80
        and record.get("repeat") == 1
    ]
    assert sum(record.get("amount", 0) for record in plugin_nodes) == 192, "plugin node count changed"
    assert sum(record.get("bytes", 0) for record in plugin_nodes) == 15360, "plugin node bytes changed"

    payloads = [
        record for record in classes
        if record.get("name") == "[4096]uint8"
        and record.get("element_size") == 1
        and record.get("repeat") == 4096
    ]
    assert sum(record.get("amount", 0) for record in payloads) >= 192, "plugin payload arrays missing"
    assert sum(record.get("bytes", 0) for record in payloads) >= 786432, "plugin payload bytes missing"

    large = [record for record in classes if record.get("name") == "[5242880]uint8"]
    assert len(large) == 1 and large[0].get("amount") == 1, "plugin-only 5 MiB global missing"
    assert large[0].get("bytes") == 5242880, "plugin-only large bytes changed"

    frame_functions = {
        frame.get("function", "")
        for goroutine in goroutines
        for frame in goroutine.get("frames", [])
    }
    plugin_frames = [name for name in frame_functions if name.endswith(".holdPluginRoot")]
    assert plugin_frames, "plugin moduledata frame was not recovered"

    print("Go plugin fixture validated: version=%s live=%d objects=%d roots=%d modules=main+plugin frame=%s" % (
        runtime.get("go_version"), live, counts.get("object", 0), counts.get("root", 0),
        sorted(plugin_frames)[0],
    ))
    return True


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], "r") as stream:
        payload = json.load(stream)
    raise SystemExit(0 if validate(payload) else 1)

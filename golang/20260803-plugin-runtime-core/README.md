# Go Plugin Runtime Core Fixture

This Linux/amd64 fixture loads a real Go plugin and proves that Maze walks more
than the main executable's `moduledata`. The main executable retains one plugin
graph through an interface; plugin globals exclusively retain another graph and
a 5 MiB backing array; a goroutine remains parked in a plugin-defined function.

## Generate

Requirements: Go with cgo/plugin support, a C compiler, GDB/gcore, glibc, and
Git LFS.

```bash
testdata/golang/20260803-plugin-runtime-core/generate.sh
```

The generator builds the executable and plugin with the same Go toolchain and
flags, captures the loaded plugin mapping, packages both ELF files, and records
both source and binary hashes in `manifest.json`. All temporary work stays under
`./tmp/` and generation is serial.

## Run

```bash
python3 testdata/run_test.py golang/20260803-plugin-runtime-core
```

The validator requires all 192 plugin-defined nodes, including 64 nodes only
reachable from a plugin global; the plugin-only 5 MiB array; 192 payload arrays;
and a recovered `.holdPluginRoot` frame. Together these check plugin type
metadata, plugin global GC masks, and plugin pclntab/moduledata traversal.

## Current artifact

Generated with Go 1.25.6 on Linux/amd64:

```text
archive sha256: bfe0a7c936a1c58c1bacef59c3736fcdc12894d6d273918bd84f53655f13b7d0
compressed bytes: 13,817,632
core logical bytes: 1,862,465,424
maps: exact /proc/<pid>/maps snapshot (95 mappings)
plugin mappings: r--p / r-xp / r--p / r--p / rw-p
```

The strict replay result is 789 live objects, 11,941 roots, 992 edges, 12,731
dominator vertices, and 54 goroutines. Named plugin allocations are exactly 192
`plugin/unnamed-*.PluginNode` objects (15,360 bytes), 192 `[4096]uint8`
objects (786,432 bytes), and one `[5242880]uint8` object (5 MiB).

# Go Complex Types Live Fixture

This fixture mirrors the broad object mix in
`python/20260729-complex-types-313/complex_types.py` while using Go-native
representations and runtime features.

It keeps 17,800 Python-comparable logical values alive:

- empty/single/ten-element, mixed-interface, and nested slices;
- fixed-layout tuple structs;
- people, game entities, parent-linked trees, players, and configs;
- map-backed sets and fixed-array set values;
- short/medium/large byte slices and fixed byte arrays;
- simple, nested, wide, pointer-valued, concurrent, and counter maps;
- short, medium, long, and Unicode strings;
- signed/unsigned, floating-point, complex, and boolean numeric boxes;
- `container/list`, points, and rectangles.

It adds 1,000 Go-specific logical objects covering interfaces, two concrete
implementations, instantiated generic `Box`/`Pair` types, buffered channels,
closures, errors, embedded structs, `container/ring`, global roots, cycles,
and parked-goroutine stack roots.

## Live run

Build from the Maze repository root, writing generated files under `./tmp/`:

```bash
mkdir -p tmp/go-complex-types-live
go build -o tmp/go-complex-types-live/go-complex-types \
  testdata/golang/20260805-complex-types-live/complex_types.go
tmp/go-complex-types-live/go-complex-types
```

Wait for `>>> READY FOR GCORE <<<`, then analyze its PID with Maze. The
program prints representative addresses for `Person`, `GameEntity`,
`TreeNode`, a generic box, a map, and a channel so object details and reverse
reference graphs can be exercised directly.

# CPython 3.13 Complex Types

This test covers Maze analysis of ordinary GIL-enabled CPython 3.13.0. It is
also a false-positive guard: CPython 3.13 ships vendored mimalloc code, but the
ordinary build must continue to use ptmalloc and pymalloc at runtime.

## Coverage

- ordinary `PyObject` layout and enabled GIL
- ptmalloc plus CPython pymalloc pools
- classes, dataclasses, named tuples, lists, tuples, dictionaries, sets,
  strings, bytes, numeric objects, and `collections` types

The workload creates 17,800 top-level objects and keeps them alive until the
coredump is captured. The validator checks exact counts for stable custom
types, requires `allocator=ptmalloc`, and requires more than 50,000 pymalloc
objects.

## Recreate The Coredump

Build and select an ordinary shared CPython 3.13.0 interpreter:

```bash
env \
  PYTHON_CONFIGURE_OPTS="--with-ensurepip=no" \
  CFLAGS="-O1 -g3 -fno-omit-frame-pointer" \
  /home/nguser/.pyenv/plugins/python-build/bin/python-build \
  3.13.0 /home/nguser/.pyenv/versions/3.13.0
pyenv shell 3.13.0
```

From the Maze repository root:

```bash
python3 cmd/maze-gen-coredump.py \
  -o testdata/python/20260729-complex-types-313/ \
  "/home/nguser/.pyenv/versions/3.13.0/bin/python testdata/python/20260729-complex-types-313/complex_types.py"
```

## Run

```bash
python3 testdata/run_test.py python/20260729-complex-types-313
```

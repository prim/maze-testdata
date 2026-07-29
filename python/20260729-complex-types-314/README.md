# CPython 3.14 Complex Types

This test covers Maze analysis of ordinary GIL-enabled CPython 3.14.0. It is
also a false-positive guard: CPython 3.14 ships vendored mimalloc code, but the
ordinary build must continue to use ptmalloc and pymalloc at runtime.

The interpreter source is the official `Python-3.14.0.tar.xz` release:

```text
SHA-256 2299dae542d395ce3883aca00d3c910307cd68e0b2f7336098c8e7b7eee9f3e9
```

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

Build and select an ordinary shared CPython 3.14.0 interpreter:

```bash
env \
  PYTHON_BUILD_CACHE_PATH=/home/nguser/.pyenv/cache \
  PYTHON_CONFIGURE_OPTS="--with-ensurepip=no" \
  CFLAGS="-O1 -g3 -fno-omit-frame-pointer" \
  MAKE_OPTS="-j8" \
  /home/nguser/.pyenv/plugins/python-build/bin/python-build \
  3.14.0 /home/nguser/.pyenv/versions/3.14.0
pyenv shell 3.14.0
```

From the Maze repository root:

```bash
python3 cmd/maze-gen-coredump.py \
  -t 120 \
  -o testdata/python/20260729-complex-types-314/ \
  "/home/nguser/.pyenv/versions/3.14.0/bin/python testdata/python/20260729-complex-types-314/complex_types.py"
```

The checked-in core was generated from a shared, GIL-enabled runtime:

```text
Py_GIL_DISABLED: 0
sys._is_gil_enabled(): True
executable Build ID: 00bcdc4ce60c1cb25fee215e6257f811f6c15eb8
libpython Build ID:  6b8a9c495f8c74a3c285d1ad3834c6fbb84fcca5
core size:           21,596,596 bytes
core MD5:            1249a72c8e5453b066ddf21682dc5921
core SHA-256:        25ac57528259b1143b278698c9655a2d357188c8f2fa0c11b25a46f7a0263511
```

## Run

```bash
python3 testdata/run_test.py python/20260729-complex-types-314
```

# CPython 3.14t Complex Types

This test covers Maze analysis of CPython 3.14.0 built with `--disable-gil`
and `--with-pydebug`.

The interpreter source is the official `Python-3.14.0.tar.xz` release:

```text
SHA-256 2299dae542d395ce3883aca00d3c910307cd68e0b2f7336098c8e7b7eee9f3e9
```

## Coverage

- free-threaded `PyObject` layout (`ob_ref_local` and `ob_ref_shared`)
- CPython's embedded mimalloc allocator
- CPython debug allocator headers and the PyMem domain
- classes, dataclasses, named tuples, lists, tuples, dictionaries, sets,
  strings, bytes, numeric objects, and `collections` types

The workload creates 17,800 top-level objects and keeps them alive until the
coredump is captured. The validator checks exact counts for the stable custom
types, requires the allocator to be `mimalloc`, and requires `unknown` memory
to be zero.

## Recreate The Coredump

Build and select a shared CPython 3.14.0 free-threaded debug interpreter:

```bash
env \
  PYTHON_BUILD_CACHE_PATH=/home/nguser/.pyenv/cache \
  PYTHON_CONFIGURE_OPTS="--disable-gil --with-pydebug --with-ensurepip=no" \
  CFLAGS="-O1 -g3 -fno-omit-frame-pointer" \
  MAKE_OPTS="-j8" \
  /home/nguser/.pyenv/plugins/python-build/bin/python-build \
  3.14.0 /home/nguser/.pyenv/versions/3.14.0t
pyenv shell 3.14.0t
```

From the Maze repository root:

```bash
python3 cmd/maze-gen-coredump.py \
  -t 120 \
  -o testdata/python/20260729-complex-types-314t/ \
  "PYTHONMALLOC=debug /home/nguser/.pyenv/versions/3.14.0t/bin/python testdata/python/20260729-complex-types-314t/complex_types.py"
```

The checked-in core was generated from a shared free-threaded runtime:

```text
sys.abiflags:          'td'
Py_GIL_DISABLED:       1
sys._is_gil_enabled(): False
SOABI:                 cpython-314td-x86_64-linux-gnu
executable Build ID:   ed4c005509fab50ccb3d8514638e51bf82f47873
libpython Build ID:    d22ba61ca4cf69790761d38ba5f6c436b0434e9b
core size:             32,052,778 bytes
core MD5:              4845d33ccf4a95b06d18ad85eb084577
core SHA-256:          a8759a9291d93b7fd24e9e0f9bdc90377028a8eccd6d2ba5c85b9611b9186a42
```

The stable Maze contract is `allocator=mimalloc`, no unknown memory or
pymalloc pools, 60,314 mimalloc objects, and identified CPython PyMem debug
domain allocations.

## Run

```bash
python3 testdata/run_test.py python/20260729-complex-types-314t
```

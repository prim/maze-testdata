# CPython 3.13t Static Complex Types

This test covers Maze analysis of CPython 3.13.0 built with `--disable-gil`,
`--with-pydebug`, and `--disable-shared`. Unlike the shared 3.13t fixture, the
free-threaded DWARF and embedded mimalloc symbols belong to the main Python
executable.

## Coverage

- free-threaded `PyObject` layout (`ob_ref_local` and `ob_ref_shared`)
- CPython's embedded mimalloc allocator in a static Python executable
- CPython debug allocator headers and the PyMem domain
- classes, dataclasses, named tuples, lists, tuples, dictionaries, sets,
  strings, bytes, numeric objects, and `collections` types

The workload creates 17,800 top-level objects and keeps them alive until the
coredump is captured. The validator checks exact counts for stable custom
types, requires the allocator to be `mimalloc`, and requires `unknown` memory
to be zero.

## Recreate The Coredump

Build and select a static CPython 3.13.0 free-threaded debug interpreter:

```bash
env \
  PYTHON_CONFIGURE_OPTS="--disable-shared --disable-gil --with-pydebug --with-ensurepip=no" \
  CFLAGS="-O1 -g3 -fno-omit-frame-pointer" \
  /home/nguser/.pyenv/plugins/python-build/bin/python-build \
  3.13.0 /home/nguser/.pyenv/versions/3.13.0t-static
pyenv shell 3.13.0t-static
```

From the Maze repository root:

```bash
python3 cmd/maze-gen-coredump.py \
  -o testdata/python/20260729-complex-types-313t-static/ \
  "PYTHONMALLOC=debug /home/nguser/.pyenv/versions/3.13.0t-static/bin/python testdata/python/20260729-complex-types-313t-static/complex_types.py"
```

## Run

```bash
python3 testdata/run_test.py python/20260729-complex-types-313t-static
```

# CPython 3.13t Release Complex Types

This test covers Maze analysis of a CPython 3.13.0 release build configured
with `--disable-gil` only: no `--with-pydebug` and no `PYTHONMALLOC=debug`.
This is the free-threaded form used in practice (python.org, pyenv and uv
`3.13t`); `20260729-complex-types-313t` covers the debug form.

## Coverage

- free-threaded `PyObject` layout (`ob_tid`, `ob_ref_local`, `ob_ref_shared`)
- CPython's embedded mimalloc allocator
- GC objects without a `PyGC_Head` prefix (the type is still declared)
- managed-dict instances behind the two-word preheader
- heap types that are not linked into GC generation lists
- dicts whose `PyDictObject` fills its mimalloc block exactly
- classes, dataclasses, named tuples, lists, tuples, dictionaries, sets,
  strings, bytes, numeric objects, and `collections` types

The workload is the same as `20260729-complex-types-313` (GIL build), so the
validator uses the same exact counts for custom types. It also requires the
allocator to be `mimalloc`, `unknown` memory to be zero, and minimum counts
for built-in objects (`int`, `code`, `type`, descriptors, dicts), which an
object-layout regression drops as a whole.

## Recreate The Coredump

Build and select a shared CPython 3.13.0 free-threaded release interpreter.
pyenv's `3.13.0t` definition adds `--disable-gil`:

```bash
env \
  PYTHON_CONFIGURE_OPTS="--enable-shared --with-ensurepip=no" \
  CFLAGS="-O1 -g3 -fno-omit-frame-pointer" \
  ~/.pyenv/plugins/python-build/bin/python-build \
  3.13.0t ~/.pyenv/versions/3.13.0t
```

From the Maze repository root, without `PYTHONMALLOC` in the environment
(`complex_types.py` refuses debug builds, `PYTHONMALLOC=debug` and `-X dev`):

```bash
python3 cmd/maze-gen-coredump.py \
  -t 120 \
  -o testdata/python/20261013-complex-types-313t-release/ \
  "$HOME/.pyenv/versions/3.13.0t/bin/python testdata/python/20261013-complex-types-313t-release/complex_types.py"
```

The checked-in core was generated from:

```text
Python:              3.13.0 experimental free-threading build
Py_GIL_DISABLED: 1   Py_DEBUG: 0   abiflags: t
executable Build ID: eb31940721124281c6b7b343d409523aa077fbe6
libpython Build ID:  d9d8d55060705919d822269b8fe8b29bfd05982c
core size:           1,076,548,624 bytes
core MD5:            069bbe430bd2538dda0a5968102727be
core SHA-256:        e07d65bca5b192ac5c8ebb14b7c778a0064dd6918af8c215b357b53fe9d105c4
```

## Run

```bash
python3 testdata/run_test.py python/20261013-complex-types-313t-release
```

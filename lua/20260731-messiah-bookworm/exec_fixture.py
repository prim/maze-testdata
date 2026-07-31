#!/usr/bin/env python3
"""Exec the production Lua without maze-gen-coredump adding stdbuf."""

from __future__ import print_function

import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--lua", required=True)
    parser.add_argument("--script", required=True)
    args = parser.parse_args()

    runtime = os.path.abspath(args.runtime)
    lua = os.path.abspath(args.lua)
    script = os.path.abspath(args.script)
    os.environ["LD_LIBRARY_PATH"] = runtime
    os.environ["LD_PRELOAD"] = os.path.join(runtime, "libjemalloc_prof.so")
    os.environ["MESSIAH_RUNTIME_DIR"] = runtime
    os.execv(lua, [lua, script])


if __name__ == "__main__":
    main()

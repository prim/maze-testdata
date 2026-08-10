#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rustc_field(output, name):
    match = re.search(r"^%s:\s+(.*)$" % re.escape(name), output, re.MULTILINE)
    return match.group(1).strip() if match else ""


def build_id(path):
    output = subprocess.run(
        ["readelf", "-n", path], check=True, capture_output=True, text=True
    ).stdout
    match = re.search(r"Build ID:\s*([0-9a-fA-F]+)", output)
    return match.group(1).lower() if match else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--cargo-toml", required=True)
    parser.add_argument("--cargo-lock", required=True)
    parser.add_argument("--profile", choices=("dev", "release"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rustc_vv = subprocess.run(
        ["rustc", "-vV"], check=True, capture_output=True, text=True
    ).stdout
    rustc_cfg = subprocess.run(
        ["rustc", "--print", "cfg"], check=True, capture_output=True, text=True
    ).stdout
    panic_strategy = "unwind"
    match = re.search(r'^panic="([^"]+)"$', rustc_cfg, re.MULTILINE)
    if match:
        panic_strategy = match.group(1)

    manifest = {
        "schema": "maze.rust-artifacts/v1",
        "rustc_version": rustc_field(rustc_vv, "release"),
        "host_triple": rustc_field(rustc_vv, "host"),
        "target_triple": rustc_field(rustc_vv, "host"),
        "llvm_version": rustc_field(rustc_vv, "LLVM version"),
        "cargo_profile": args.profile,
        "opt_level": "0" if args.profile == "dev" else "3",
        "debug_level": "2",
        "lto": "off",
        "panic_strategy": panic_strategy,
        "allocator": "glibc-ptmalloc",
        "cargo_lock_sha256": sha256_file(args.cargo_lock),
        "executable": {
            "archive_member": os.path.basename(args.binary),
            "build_id": build_id(args.binary),
            "sha256": sha256_file(args.binary),
            "size": os.path.getsize(args.binary),
        },
    }
    temporary = args.output + ".tmp"
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.replace(temporary, args.output)


if __name__ == "__main__":
    main()

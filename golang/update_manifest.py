#!/usr/bin/env python3

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Update a durable Go core fixture manifest")
    parser.add_argument("config", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("binary", type=Path)
    parser.add_argument("tarball", type=Path)
    parser.add_argument("--extra-source", action="append", default=[], type=Path)
    parser.add_argument(
        "--extra-binary",
        action="append",
        default=[],
        metavar="NAME=PATH",
    )
    args = parser.parse_args()
    config_path = args.config.resolve()
    source = args.source.resolve()
    binary = args.binary.resolve()
    artifact = args.tarball.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    members = []
    core_size = None
    with tarfile.open(str(artifact), "r:gz") as archive:
        for member in archive.getmembers():
            members.append({"name": member.name, "size": member.size})
            if Path(member.name).name.startswith("core."):
                core_size = member.size
    if core_size is None:
        raise SystemExit("archive does not contain core.<pid>")

    build = dict(config["build"])
    build.update({
        "toolchain": subprocess.check_output(["go", "version"], text=True).strip(),
        "binary_sha256": sha256(binary),
    })
    if args.extra_binary:
        build["artifacts"] = {}
        for item in args.extra_binary:
            if "=" not in item:
                raise SystemExit("--extra-binary must be NAME=PATH: %s" % item)
            name, path_text = item.split("=", 1)
            path = Path(path_text).resolve()
            if not name or not path.is_file():
                raise SystemExit("invalid --extra-binary %s" % item)
            if name in build["artifacts"]:
                raise SystemExit("duplicate --extra-binary name %s" % name)
            build["artifacts"][name] = {
                "path": path.name,
                "sha256": sha256(path),
            }
    manifest = {
        "schema": "maze.golang.fixture/v1",
        "name": config["name"],
        "source": {"path": source.name, "sha256": sha256(source)},
        "build": build,
        "artifact": {
            "path": artifact.name,
            "sha256": sha256(artifact),
            "bytes": artifact.stat().st_size,
            "core_logical_bytes": core_size,
            "members": sorted(members, key=lambda member: member["name"]),
        },
        "expected": config["expected"],
    }
    if args.extra_source:
        sources = [source] + [path.resolve() for path in args.extra_source]
        manifest["sources"] = [
            {"path": path.name, "sha256": sha256(path)} for path in sources
        ]
    output = source.parent / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

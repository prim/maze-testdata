#!/usr/bin/env python3

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def sha256_path(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_member(archive, member):
    digest = hashlib.sha256()
    stream = archive.extractfile(member)
    if stream is None:
        raise RuntimeError("cannot read archive member %s" % member.name)
    with stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_case(case_dir, case):
    config = json.loads((case_dir / "fixture.json").read_text(encoding="utf-8"))
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    source = case_dir / manifest["source"]["path"]
    artifact = case_dir / case["artifact"]
    expected_toolchain = "go version %s linux/amd64" % case["go_version"]

    if manifest.get("schema") != "maze.golang.fixture/v1":
        raise RuntimeError("%s: unexpected manifest schema" % case_dir.name)
    if config.get("expected", {}).get("go_version") != case["go_version"]:
        raise RuntimeError("%s: config Go version mismatch" % case_dir.name)
    if manifest.get("expected", {}).get("go_version") != case["go_version"]:
        raise RuntimeError("%s: manifest Go version mismatch" % case_dir.name)
    if manifest.get("build", {}).get("toolchain") != expected_toolchain:
        raise RuntimeError("%s: toolchain mismatch" % case_dir.name)
    if manifest.get("artifact", {}).get("path") != artifact.name:
        raise RuntimeError("%s: artifact path mismatch" % case_dir.name)
    if sha256_path(source) != manifest["source"]["sha256"]:
        raise RuntimeError("%s: source hash mismatch" % case_dir.name)
    if artifact.stat().st_size != manifest["artifact"]["bytes"]:
        raise RuntimeError("%s: artifact size mismatch" % case_dir.name)
    if sha256_path(artifact) != manifest["artifact"]["sha256"]:
        raise RuntimeError("%s: artifact hash mismatch" % case_dir.name)

    with tarfile.open(str(artifact), "r:gz") as archive:
        members = sorted(
            ({"name": member.name, "size": member.size} for member in archive.getmembers()),
            key=lambda record: record["name"],
        )
        if members != manifest["artifact"]["members"]:
            raise RuntimeError("%s: archive member manifest mismatch" % case_dir.name)
        core_members = [member for member in archive.getmembers() if Path(member.name).name.startswith("core.")]
        if len(core_members) != 1 or core_members[0].size != manifest["artifact"]["core_logical_bytes"]:
            raise RuntimeError("%s: logical core size mismatch" % case_dir.name)
        binary_hash = manifest.get("build", {}).get("binary_sha256")
        binary_found = any(
            sha256_member(archive, member) == binary_hash
            for member in archive.getmembers()
            if member.isfile() and not Path(member.name).name.startswith("core.") and member.size <= 32 * 1024 * 1024
        )
        if not binary_found:
            raise RuntimeError("%s: matching executable is absent from archive" % case_dir.name)

    print("verified %-42s %s sha256=%s" % (
        case_dir.name,
        case["go_version"],
        manifest["artifact"]["sha256"],
    ))


def preserve_root_outputs(repo_root):
    temp_root = repo_root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="golang-runtime-matrix-", dir=str(temp_root)))
    state = {}
    for name in ("maze-result.json", "maze-result.txt", "maze.log"):
        path = repo_root / name
        state[name] = path.exists()
        if path.exists():
            shutil.copy2(str(path), str(backup / name))
    return backup, state


def restore_root_outputs(repo_root, backup, state):
    for name, existed in state.items():
        path = repo_root / name
        if existed:
            shutil.copy2(str(backup / name), str(path))
        elif path.exists():
            path.unlink()
    shutil.rmtree(str(backup))


def select_cases(cases, requested_versions):
    requested = set(requested_versions)
    selected = [case for case in cases if not requested or case["go_version"] in requested]
    if requested and requested != {case["go_version"] for case in selected}:
        raise ValueError("unknown --version value")
    return selected


def main():
    parser = argparse.ArgumentParser(description="Generate, verify, and replay the durable Go runtime core matrix serially")
    parser.add_argument("--generate", action="store_true", help="regenerate every core artifact before verification")
    parser.add_argument("--verify-only", action="store_true", help="verify artifacts without running Maze")
    parser.add_argument("--version", action="append", default=[], help="limit work to one or more exact Go versions")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    testdata_root = script_dir.parent
    repo_root = testdata_root.parent
    matrix = json.loads((script_dir / "runtime_matrix.json").read_text(encoding="utf-8"))
    if matrix.get("schema") != "maze.golang.runtime-matrix/v1":
        raise SystemExit("unexpected matrix schema")
    try:
        cases = select_cases(matrix["cases"], args.version)
    except ValueError as err:
        raise SystemExit(str(err))

    if args.generate:
        for case in cases:
            case_dir = script_dir / case["directory"]
            subprocess.run([str(case_dir / "generate.sh")], cwd=str(repo_root), check=True)

    for case in cases:
        verify_case(script_dir / case["directory"], case)

    if args.verify_only:
        return

    backup, state = preserve_root_outputs(repo_root)
    try:
        for case in cases:
            subprocess.run(
                [sys.executable, str(testdata_root / "run_test.py"), "golang/" + case["directory"]],
                cwd=str(repo_root),
                check=True,
            )
            if case["go_version"] == "go1.23.0":
                subprocess.run(
                    [sys.executable, str(script_dir / "run_gcprog_integration.py")],
                    cwd=str(repo_root),
                    check=True,
                )
    finally:
        restore_root_outputs(repo_root, backup, state)


if __name__ == "__main__":
    main()

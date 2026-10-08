#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_path(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    case_dir = script_dir / "20260803-runtime-core-go1.23.0"
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    artifact = case_dir / manifest["artifact"]["path"]
    if sha256_path(artifact) != manifest["artifact"]["sha256"]:
        raise SystemExit("Go 1.23 GC-program artifact hash mismatch")

    temp_parent = repo_root / "tmp"
    temp_parent.mkdir(parents=True, exist_ok=True)
    extract_dir = Path(tempfile.mkdtemp(prefix="golang-gcprog-", dir=str(temp_parent)))
    try:
        subprocess.run(
            ["tar", "--extract", "--sparse", "--gzip", "--file", str(artifact), "--directory", str(extract_dir)],
            cwd=str(repo_root),
            check=True,
        )
        cores = [path for path in extract_dir.iterdir() if path.name.startswith("core.")]
        if len(cores) != 1:
            raise RuntimeError("expected one extracted core, found %d" % len(cores))
        executable = None
        for path in extract_dir.iterdir():
            if path.is_file() and path.stat().st_size <= 32 * 1024 * 1024:
                if sha256_path(path) == manifest["build"]["binary_sha256"]:
                    executable = path
                    break
        if executable is None:
            raise RuntimeError("exact Go 1.23 executable is missing after extraction")

        test_tmp = repo_root / "tmp" / "go-test"
        test_tmp.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "MAZE_GOCORE_GCPROG_CORE": str(cores[0]),
            "MAZE_GOCORE_GCPROG_EXE": str(executable),
            "TMPDIR": str(test_tmp),
        })
        subprocess.run(
            ["go", "test", "./internal/gocore/internal/gocore", "-run", "^TestLegacyRuntimeGCProgramIntegration$", "-count=1", "-v"],
            cwd=str(repo_root),
            env=env,
            check=True,
        )
    finally:
        shutil.rmtree(str(extract_dir))


if __name__ == "__main__":
    main()

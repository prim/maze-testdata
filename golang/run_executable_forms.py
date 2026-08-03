#!/usr/bin/env python3

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from run_runtime_matrix import (
    preserve_root_outputs,
    restore_root_outputs,
    sha256_member,
    verify_case,
)


def member_with_sha256(archive, expected):
    matches = [
        member for member in archive.getmembers()
        if member.isfile() and member.size <= 32 * 1024 * 1024
        and sha256_member(archive, member) == expected
    ]
    if len(matches) != 1:
        raise RuntimeError("expected one archive member with SHA-256 %s, found %d" % (expected, len(matches)))
    return matches[0]


def extract_member(archive, member, destination):
    stream = archive.extractfile(member)
    if stream is None:
        raise RuntimeError("cannot read archive member %s" % member.name)
    with stream, destination.open("wb") as output:
        shutil.copyfileobj(stream, output)
    destination.chmod(0o755)


def elf_type(path):
    with path.open("rb") as stream:
        header = stream.read(18)
    if len(header) != 18 or header[:6] != b"\x7fELF\x02\x01":
        raise RuntimeError("%s is not a little-endian ELF64 file" % path)
    return struct.unpack_from("<H", header, 16)[0]


def has_debug_info(path):
    output = subprocess.check_output(["readelf", "-S", str(path)], text=True)
    return ".debug_info" in output


def verify_form(case_dir, case, temp_root):
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("build", {}).get("form") != case["form"]:
        raise RuntimeError("%s: executable form mismatch" % case_dir.name)
    artifact = case_dir / case["artifact"]
    work = Path(tempfile.mkdtemp(prefix="golang-executable-form-", dir=str(temp_root)))
    try:
        with tarfile.open(str(artifact), "r:gz") as archive:
            analysis_member = member_with_sha256(archive, manifest["build"]["binary_sha256"])
            analysis_path = work / "analysis-elf"
            extract_member(archive, analysis_member, analysis_path)
            if case["form"] == "pie":
                if elf_type(analysis_path) != 3 or not has_debug_info(analysis_path):
                    raise RuntimeError("PIE fixture is not an ET_DYN ELF with DWARF")
            else:
                runtime_hash = manifest.get("build", {}).get("artifacts", {}).get("runtime", {}).get("sha256")
                runtime_member = member_with_sha256(archive, runtime_hash)
                if runtime_member.name != "runtime-stripped":
                    raise RuntimeError("stripped runtime member has unexpected name %s" % runtime_member.name)
                runtime_path = work / "runtime-elf"
                extract_member(archive, runtime_member, runtime_path)
                if elf_type(analysis_path) != 2 or elf_type(runtime_path) != 2:
                    raise RuntimeError("stripped fixture does not contain ET_EXEC ELF files")
                if not has_debug_info(analysis_path) or has_debug_info(runtime_path):
                    raise RuntimeError("runtime/debug ELF DWARF split is invalid")
                runtime_id = subprocess.check_output(["go", "tool", "buildid", str(runtime_path)], text=True).strip()
                analysis_id = subprocess.check_output(["go", "tool", "buildid", str(analysis_path)], text=True).strip()
                if not runtime_id or runtime_id != analysis_id:
                    raise RuntimeError("runtime and analysis ELF Go Build IDs differ")
    finally:
        shutil.rmtree(str(work))
    print("verified executable form %-31s form=%s" % (case_dir.name, case["form"]))


def main():
    parser = argparse.ArgumentParser(description="Generate, verify, and replay durable Go executable forms serially")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    testdata_root = script_dir.parent
    repo_root = testdata_root.parent
    temp_root = repo_root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    matrix = json.loads((script_dir / "executable_forms.json").read_text(encoding="utf-8"))
    if matrix.get("schema") != "maze.golang.executable-forms/v1":
        raise SystemExit("unexpected executable forms schema")

    if args.generate:
        for case in matrix["cases"]:
            subprocess.run([str(script_dir / case["directory"] / "generate.sh")], cwd=str(repo_root), check=True)

    for case in matrix["cases"]:
        case_dir = script_dir / case["directory"]
        verify_case(case_dir, case)
        verify_form(case_dir, case, temp_root)

    if args.verify_only:
        return

    backup, state = preserve_root_outputs(repo_root)
    try:
        for case in matrix["cases"]:
            subprocess.run(
                [sys.executable, str(testdata_root / "run_test.py"), "golang/" + case["directory"]],
                cwd=str(repo_root), check=True,
            )
    finally:
        restore_root_outputs(repo_root, backup, state)


if __name__ == "__main__":
    main()

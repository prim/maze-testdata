#!/usr/bin/env python3
"""Build the pinned container and generate a fresh Messiah fixture tarball."""

from __future__ import print_function

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys


IMAGE = "maze-testdata/messiah-bookworm:20260731"


def container_path(maze_root, host_path):
    resolved = host_path.resolve()
    relative = resolved.relative_to(maze_root.resolve())
    return str(Path("/workspace") / relative)


def main():
    script = Path(__file__).resolve()
    test_dir = script.parent
    maze_root = script.parents[3]

    parser = argparse.ArgumentParser()
    parser.add_argument("--tar", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--elf-dir", type=Path, default=maze_root / "db" / "elf")
    parser.add_argument("--skip-image-build", action="store_true")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run fixture assertions in the pinned runtime without generating a core",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=maze_root / "tmp" / "h72-messiah-generated",
    )
    args = parser.parse_args()

    runtime = maze_root / "tmp" / "h72-messiah-test-runtime"
    prepare = [
        sys.executable,
        str(test_dir / "prepare_runtime.py"),
        "--output",
        str(runtime),
    ]
    if args.manifest:
        prepare.extend(["--manifest", str(args.manifest), "--elf-dir", str(args.elf_dir)])
    elif args.tar:
        prepare.extend(["--tar", str(args.tar)])
    subprocess.run(prepare, cwd=str(maze_root), check=True)

    if not args.skip_image_build:
        subprocess.run(
            ["docker", "build", "-t", IMAGE, "-f", str(test_dir / "Dockerfile"), str(test_dir)],
            cwd=str(maze_root),
            check=True,
        )

    output = args.output.resolve()
    output.relative_to(maze_root.resolve())
    output.mkdir(parents=True, exist_ok=True)
    temp_dir = maze_root / "tmp" / "h72-messiah-coredump-temp"
    home_dir = maze_root / "tmp" / "h72-messiah-container-home"
    temp_dir.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)

    runtime_in = container_path(maze_root, runtime)
    test_dir_in = container_path(maze_root, test_dir)
    output_in = container_path(maze_root, output)
    command = " ".join(
        shlex.quote(part)
        for part in [
            "python3",
            test_dir_in + "/exec_fixture.py",
            "--runtime",
            runtime_in,
            "--lua",
            runtime_in + "/lua",
            "--script",
            test_dir_in + "/fixture.lua",
        ]
    )

    if args.smoke:
        smoke_command = [
            "docker",
            "run",
            "--rm",
            "--user=%d:%d" % (os.getuid(), os.getgid()),
            "--env=HOME=" + container_path(maze_root, home_dir),
            "--env=MESSIAH_FIXTURE_SMOKE=1",
            "--volume=%s:/workspace" % maze_root.resolve(),
            "--workdir=/workspace",
            IMAGE,
            "python3",
            test_dir_in + "/exec_fixture.py",
            "--runtime",
            runtime_in,
            "--lua",
            runtime_in + "/lua",
            "--script",
            test_dir_in + "/fixture.lua",
        ]
        subprocess.run(smoke_command, cwd=str(maze_root), check=True)
        print("Fixture smoke test passed")
        return

    docker_command = [
        "docker",
        "run",
        "--rm",
        "--cap-add=SYS_PTRACE",
        "--security-opt=seccomp=unconfined",
        "--user=%d:%d" % (os.getuid(), os.getgid()),
        "--env=HOME=" + container_path(maze_root, home_dir),
        "--env=TMPDIR=" + container_path(maze_root, temp_dir),
        "--volume=%s:/workspace" % maze_root.resolve(),
        "--workdir=/workspace",
        IMAGE,
        "python3",
        "cmd/maze-gen-coredump.py",
        "--output",
        output_in,
        "--timeout",
        "120",
        command,
    ]
    subprocess.run(docker_command, cwd=str(maze_root), check=True)
    generated = sorted(output.glob("coredump-*.tar.gz"), key=lambda path: path.stat().st_mtime)
    if not generated:
        raise RuntimeError("maze-gen-coredump did not produce a tarball")
    print("Generated fixture: %s" % generated[-1])


if __name__ == "__main__":
    main()

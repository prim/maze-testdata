#!/usr/bin/env python3
"""Prove that Maze live Go analysis and replay of its exact core are equal."""

import argparse
import difflib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time


READY_SIGNAL = "READY FOR GCORE"
ANALYSIS_TIMEOUT_SECONDS = 900


class IntegrationError(RuntimeError):
    pass


def run_checked(command, *, cwd, env, output_path, timeout=ANALYSIS_TIMEOUT_SECONDS):
    result = subprocess.run(
        [str(part) for part in command],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    output_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-80:])
        raise IntegrationError(
            "command failed with exit code %d: %s\n%s"
            % (result.returncode, " ".join(str(part) for part in command), tail)
        )
    return result.stdout


def reset_work_dir(repo_root, name):
    tmp_root = (repo_root / "tmp").resolve()
    work_dir = (tmp_root / name).resolve()
    if work_dir.parent != tmp_root or work_dir.name != name:
        raise IntegrationError("refusing to reset unsafe work directory %s" % work_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    return work_dir


class RootResultGuard:
    """Preserve pre-existing root results while Maze writes its fixed filenames."""

    result_names = ("maze-result.txt", "maze-result.json")
    preserve_names = result_names + ("maze.log",)

    def __init__(self, repo_root, work_dir):
        self.repo_root = repo_root
        self.backup_dir = work_dir / "preexisting-root-results"

    def __enter__(self):
        self.backup_dir.mkdir()
        for name in self.preserve_names:
            source = self.repo_root / name
            if os.path.lexists(source):
                os.replace(source, self.backup_dir / name)
        return self

    def collect(self, destination):
        destination.mkdir(parents=True)
        for name in self.result_names:
            source = self.repo_root / name
            if not source.is_file():
                raise IntegrationError("Maze did not produce %s" % source)
            os.replace(source, destination / name)

    def __exit__(self, exc_type, exc, traceback):
        uncollected = self.backup_dir.parent / "uncollected-root-results"
        for name in self.preserve_names:
            generated = self.repo_root / name
            if os.path.lexists(generated):
                uncollected.mkdir(exist_ok=True)
                os.replace(generated, uncollected / name)
            backup = self.backup_dir / name
            if os.path.lexists(backup):
                os.replace(backup, generated)
        try:
            self.backup_dir.rmdir()
        except OSError:
            pass


def launch_fixture(binary, log_path, timeout_seconds=30):
    stream = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(binary)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )
    ready = threading.Event()

    def drain_output():
        try:
            for line in process.stdout:
                stream.write(line)
                stream.flush()
                if READY_SIGNAL in line:
                    ready.set()
        finally:
            stream.close()

    reader = threading.Thread(target=drain_output, name="go-fixture-output", daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout_seconds
    while not ready.is_set():
        if process.poll() is not None:
            reader.join(timeout=2)
            raise IntegrationError("fixture exited before readiness with %d" % process.returncode)
        if time.monotonic() >= deadline:
            raise IntegrationError("fixture did not emit %r within %d seconds" % (READY_SIGNAL, timeout_seconds))
        ready.wait(timeout=0.1)
    return process, reader


def process_is_alive(process):
    if process.poll() is not None:
        return False
    try:
        os.kill(process.pid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_fixture(process, reader):
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    reader.join(timeout=2)


def maze_command(repo_root, *arguments):
    return [repo_root / "maze", *arguments]


def collect_tarball(package_dir, pid):
    candidates = list(package_dir.glob("coredump-%d-*.tar.gz" % pid))
    if len(candidates) != 1:
        raise IntegrationError("expected one packaged tarball, found %d" % len(candidates))
    tarball = candidates[0]
    with tarfile.open(tarball, "r:gz") as archive:
        names = {member.name.lstrip("./") for member in archive.getmembers()}
    if "core.%d" % pid not in names:
        raise IntegrationError("packaged tarball has no core.%d" % pid)
    return tarball


def canonical_json(path):
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if "generated_at" not in value:
        raise IntegrationError("%s has no generated_at field" % path)
    value.pop("generated_at")
    return value


def assert_equal_files(left, right, diff_path):
    left_text = left.read_text(encoding="utf-8")
    right_text = right.read_text(encoding="utf-8")
    if left_text == right_text:
        return
    diff = "".join(
        difflib.unified_diff(
            left_text.splitlines(True),
            right_text.splitlines(True),
            fromfile=str(left),
            tofile=str(right),
        )
    )
    diff_path.write_text(diff, encoding="utf-8")
    raise IntegrationError("live/tar text differs; see %s" % diff_path)


def assert_equal_json(left_path, right_path, diff_path):
    left = canonical_json(left_path)
    right = canonical_json(right_path)
    if left == right:
        return left
    left_text = json.dumps(left, indent=2, sort_keys=True) + "\n"
    right_text = json.dumps(right, indent=2, sort_keys=True) + "\n"
    diff = "".join(
        difflib.unified_diff(
            left_text.splitlines(True),
            right_text.splitlines(True),
            fromfile=str(left_path),
            tofile=str(right_path),
        )
    )
    diff_path.write_text(diff, encoding="utf-8")
    raise IntegrationError("live/tar JSON differs; see %s" % diff_path)


def validate_result(python, validator, result, repo_root, env, log_path):
    run_checked(
        [python, validator, result],
        cwd=repo_root,
        env=env,
        output_path=log_path,
        timeout=60,
    )


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", choices=("pure", "cgo"), default="pure")
    return parser.parse_args()


def main():
    args = parse_arguments()
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    fixture_config = {
        "pure": {
            "case": "20260803-runtime-core",
            "cgo_enabled": "0",
            "work_dir": "golang-live-tar",
        },
        "cgo": {
            "case": "20260803-cgo-runtime-core",
            "cgo_enabled": "1",
            "work_dir": "golang-cgo-live-tar",
        },
    }[args.fixture]
    case_dir = script_path.parent / fixture_config["case"]
    work_dir = reset_work_dir(repo_root, fixture_config["work_dir"])
    go_tmp = repo_root / "tmp" / "go-test"
    go_tmp.mkdir(parents=True, exist_ok=True)
    live_prepare = work_dir / "live-prepare"
    live_result = work_dir / "live-result"
    tar_result = work_dir / "tar-result"
    package_dir = work_dir / "package"
    tar_tmp = work_dir / "tar-tmp"
    for directory in (live_prepare, package_dir, tar_tmp):
        directory.mkdir(parents=True)

    python = Path(sys.executable).resolve()
    binary = work_dir / "fixture"
    env = os.environ.copy()
    env["TMPDIR"] = str(tar_tmp)
    build_env = env.copy()
    build_env["CGO_ENABLED"] = fixture_config["cgo_enabled"]
    build_env["TMPDIR"] = str(go_tmp)

    for required in (repo_root / "maze", repo_root / ".maze", repo_root / ".maze-go-core"):
        if not required.is_file():
            raise IntegrationError("missing %s; run ./maze --build first" % required)

    run_checked(
        [
            "go",
            "build",
            "-trimpath",
            "-buildvcs=false",
            "-o",
            binary,
            case_dir / "fixture.go",
        ],
        cwd=repo_root,
        env=build_env,
        output_path=work_dir / "build.log",
        timeout=180,
    )

    fixture = None
    reader = None
    with RootResultGuard(repo_root, work_dir) as results:
        try:
            fixture, reader = launch_fixture(binary, work_dir / "fixture.log")
            pid = fixture.pid
            maps_snapshot = work_dir / "maps.snapshot"
            shutil.copyfile("/proc/%d/maps" % pid, maps_snapshot)
            run_checked(
                maze_command(
                    repo_root,
                    "--pid",
                    str(pid),
                    "--logdir",
                    str(live_prepare),
                    "--text",
                    "--json-output",
                    "--limit",
                    "500",
                    "--no-cpp",
                ),
                cwd=repo_root,
                env=env,
                output_path=work_dir / "live-maze.log",
            )
            results.collect(live_result)
            if not process_is_alive(fixture):
                raise IntegrationError("fixture did not survive Maze live GDB detach")

            core_path = live_prepare / ("core.%d" % pid)
            if not core_path.is_file() or core_path.stat().st_size == 0:
                raise IntegrationError("live analysis did not retain %s" % core_path)

            run_checked(
                [
                    python,
                    repo_root / "cmd" / "maze-tar-coredump.py",
                    "--maps",
                    maps_snapshot,
                    core_path,
                ],
                cwd=package_dir,
                env=env,
                output_path=work_dir / "package.log",
                timeout=300,
            )
            if not process_is_alive(fixture):
                raise IntegrationError("fixture exited while packaging its captured core")
            tarball = collect_tarball(package_dir, pid)
        finally:
            if fixture is not None:
                stop_fixture(fixture, reader)

        run_checked(
            maze_command(
                repo_root,
                "--tar",
                str(tarball),
                "--text",
                "--json-output",
                "--limit",
                "500",
                "--no-cpp",
            ),
            cwd=repo_root,
            env=env,
            output_path=work_dir / "tar-maze.log",
        )
        results.collect(tar_result)

    assert_equal_files(
        live_result / "maze-result.txt",
        tar_result / "maze-result.txt",
        work_dir / "text.diff",
    )
    payload = assert_equal_json(
        live_result / "maze-result.json",
        tar_result / "maze-result.json",
        work_dir / "json.diff",
    )
    validate_result(
        python,
        case_dir / "validate.py",
        live_result / "maze-result.json",
        repo_root,
        env,
        work_dir / "validate-live.log",
    )
    validate_result(
        python,
        case_dir / "validate.py",
        tar_result / "maze-result.json",
        repo_root,
        env,
        work_dir / "validate-tar.log",
    )

    go_result = payload["go"]
    counts = go_result["counts"]
    print(
        "live/tar %s Go equivalence validated: pid=%d objects=%d roots=%d edges=%d "
        "dominators=%d tar=%s"
        % (
            args.fixture,
            pid,
            counts["object"],
            counts["root"],
            counts["edge"],
            counts["dominator"],
            tarball.relative_to(repo_root),
        )
    )
    print("artifacts retained under %s" % work_dir.relative_to(repo_root))


if __name__ == "__main__":
    try:
        main()
    except (IntegrationError, subprocess.TimeoutExpired) as error:
        print("live/tar Go integration failed: %s" % error, file=sys.stderr)
        raise SystemExit(1)

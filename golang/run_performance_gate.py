#!/usr/bin/env python3
"""Measure and enforce the Maze Go core large-object-graph resource gate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import time

from run_live_tar import IntegrationError, RootResultGuard, reset_work_dir, run_checked


DEFAULT_OBJECTS = 200000
MIN_QUALIFYING_OBJECTS = 200000
SAMPLE_INTERVAL_SECONDS = 0.02
MIB = 1 << 20
HELPER_WALL_LIMIT_SECONDS = 120
MAZE_WALL_LIMIT_SECONDS = 300
HELPER_CPU_LIMIT_SECONDS = 240
MAZE_CPU_LIMIT_SECONDS = 600


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", type=int, default=DEFAULT_OBJECTS)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="allow a non-qualifying object count for harness development",
    )
    parser.add_argument("--keep-large-artifacts", action="store_true")
    return parser.parse_args()


def sha256_optional(path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def process_children(pid):
    task_dir = Path("/proc") / str(pid) / "task"
    children = set()
    try:
        tasks = list(task_dir.iterdir())
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return []
    for task in tasks:
        try:
            values = (task / "children").read_text(encoding="ascii").split()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        children.update(int(value) for value in values)
    return sorted(children)


def process_status(pid):
    path = Path("/proc") / str(pid) / "status"
    try:
        name = "unknown"
        rss = 0
        for line in path.read_text(encoding="ascii", errors="replace").splitlines():
            if line.startswith("Name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("VmRSS:"):
                rss = int(line.split()[1]) * 1024
        return name, rss
    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
        return None


def sample_process_tree(root_pid):
    pending = [root_pid]
    seen = set()
    by_name = {}
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        pending.extend(process_children(pid))
        status = process_status(pid)
        if status is None:
            continue
        name, rss = status
        by_name[name] = by_name.get(name, 0) + rss
    return sum(by_name.values()), by_name


def rusage_snapshot():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime, usage.ru_stime


def run_monitored(command, *, cwd, env, stdout_path, stderr_path=None, timeout=900):
    before_user, before_system = rusage_snapshot()
    started = time.monotonic()
    peak_tree_rss = 0
    peak_by_name = {}
    with stdout_path.open("wb") as stdout:
        if stderr_path is None:
            stderr = subprocess.STDOUT
            stderr_stream = None
        else:
            stderr_stream = stderr_path.open("wb")
            stderr = stderr_stream
        try:
            process = subprocess.Popen(
                [str(part) for part in command],
                cwd=str(cwd),
                env=env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            deadline = started + timeout
            while process.poll() is None:
                tree_rss, by_name = sample_process_tree(process.pid)
                peak_tree_rss = max(peak_tree_rss, tree_rss)
                for name, rss in by_name.items():
                    peak_by_name[name] = max(peak_by_name.get(name, 0), rss)
                if time.monotonic() >= deadline:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    raise IntegrationError("command timed out: %s" % " ".join(map(str, command)))
                time.sleep(SAMPLE_INTERVAL_SECONDS)
            return_code = process.returncode
        finally:
            if stderr_stream is not None:
                stderr_stream.close()
    ended = time.monotonic()
    after_user, after_system = rusage_snapshot()
    measurement = {
        "command": [str(part) for part in command],
        "exit_code": return_code,
        "wall_seconds": round(ended - started, 6),
        "user_cpu_seconds": round(after_user - before_user, 6),
        "system_cpu_seconds": round(after_system - before_system, 6),
        "peak_tree_rss_bytes": peak_tree_rss,
        "peak_rss_by_process_name": dict(sorted(peak_by_name.items())),
        "stdout_bytes": stdout_path.stat().st_size,
    }
    if stderr_path is not None:
        measurement["stderr_bytes"] = stderr_path.stat().st_size
    if return_code != 0:
        tail_path = stderr_path if stderr_path is not None else stdout_path
        tail = tail_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        raise IntegrationError(
            "command failed with exit code %d: %s\n%s"
            % (return_code, " ".join(map(str, command)), "\n".join(tail))
        )
    return measurement


def launch_fixture(binary, objects, log_path):
    stream = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(binary), "--objects", str(objects)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 60
    try:
        while time.monotonic() < deadline:
            timeout = max(0, min(0.25, deadline - time.monotonic()))
            if selector.select(timeout):
                line = process.stdout.readline()
                if line:
                    stream.write(line)
                    stream.flush()
                    if "READY FOR GCORE" in line:
                        return process
            if process.poll() is not None:
                break
    finally:
        selector.close()
        stream.close()
    if process.poll() is None:
        process.kill()
        process.wait()
    raise IntegrationError("performance fixture exited or timed out before readiness")


def stop_fixture(process):
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    finally:
        if process.stdout is not None:
            process.stdout.close()


def scan_ndjson(path, expected_nodes):
    observed = {}
    trailer = None
    first_kind = None
    last_kind = None
    bench_nodes = 0
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            record = json.loads(line)
            kind = record.get("kind")
            if first_kind is None:
                first_kind = kind
            last_kind = kind
            observed[kind] = observed.get(kind, 0) + 1
            if kind == "object" and record.get("display_type") == "main.benchNode":
                bench_nodes += 1
            if kind == "trailer":
                trailer = record
    if first_kind != "header" or last_kind != "trailer" or not trailer or not trailer.get("complete"):
        raise IntegrationError("helper stream is not complete")
    if bench_nodes != expected_nodes:
        raise IntegrationError("helper benchNode objects = %d, want %d" % (bench_nodes, expected_nodes))
    for kind, count in trailer["counts"].items():
        if observed.get(kind, 0) != count:
            raise IntegrationError(
                "helper %s records = %d, trailer says %d" % (kind, observed.get(kind, 0), count)
            )
    return {
        "observed_counts": dict(sorted(observed.items())),
        "trailer": trailer,
        "bench_node_objects": bench_nodes,
    }


def validate_maze_json(path, expected_nodes):
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    go_result = payload.get("go") or {}
    classes = go_result.get("classes") or []
    matches = [item for item in classes if item.get("name") == "main.benchNode"]
    if len(matches) != 1 or matches[0].get("amount") != expected_nodes:
        raise IntegrationError("Maze main.benchNode class = %r, want amount %d" % (matches, expected_nodes))
    return {
        "counts": go_result.get("counts"),
        "bench_node_class": matches[0],
        "json_bytes": path.stat().st_size,
    }


def gate_checks(objects, helper, maze, helper_stream, maze_result):
    helper_rss_limit = 512 * MIB + objects * 1024
    maze_tree_rss_limit = 1024 * MIB + objects * 2048
    helper_output_limit = 64 * MIB + objects * 1024
    checks = {
        "helper_wall_seconds": (helper["wall_seconds"], HELPER_WALL_LIMIT_SECONDS),
        "maze_wall_seconds": (maze["wall_seconds"], MAZE_WALL_LIMIT_SECONDS),
        "helper_cpu_seconds": (
            helper["user_cpu_seconds"] + helper["system_cpu_seconds"],
            HELPER_CPU_LIMIT_SECONDS,
        ),
        "maze_cpu_seconds": (
            maze["user_cpu_seconds"] + maze["system_cpu_seconds"],
            MAZE_CPU_LIMIT_SECONDS,
        ),
        "helper_peak_tree_rss_bytes": (helper["peak_tree_rss_bytes"], helper_rss_limit),
        "maze_peak_tree_rss_bytes": (maze["peak_tree_rss_bytes"], maze_tree_rss_limit),
        "helper_ndjson_bytes": (helper["stdout_bytes"], helper_output_limit),
        "maze_json_bytes": (maze_result["json_bytes"], 128 * MIB),
        "helper_object_count": (helper_stream["trailer"]["counts"]["object"], objects + 100000),
        "helper_edge_count": (helper_stream["trailer"]["counts"]["edge"], objects * 4 + 100000),
    }
    results = {}
    failures = []
    for name, (actual, limit) in checks.items():
        passed = actual <= limit
        results[name] = {"actual": actual, "limit": limit, "passed": passed}
        if not passed:
            failures.append("%s=%s exceeds %s" % (name, actual, limit))
    return results, failures


def allocated_bytes(path):
    stat = path.stat()
    return stat.st_blocks * 512


def main():
    args = parse_arguments()
    if args.objects < 1:
        raise IntegrationError("--objects must be positive")
    if args.objects < MIN_QUALIFYING_OBJECTS and not args.smoke:
        raise IntegrationError(
            "--objects must be at least %d unless --smoke is set" % MIN_QUALIFYING_OBJECTS
        )

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    work_dir = reset_work_dir(repo_root, "golang-performance-gate")
    build_tmp = repo_root / "tmp" / "go-test"
    build_tmp.mkdir(parents=True, exist_ok=True)
    prepare_dir = work_dir / "prepare"
    prepare_dir.mkdir()
    maze_result_dir = work_dir / "maze-result"
    fixture_binary = work_dir / "fixture"
    fixture_source = script_path.parent / "performance_fixture.go"
    helper_output = work_dir / "helper.ndjson"
    helper_stderr = work_dir / "helper.stderr.log"
    results_path = work_dir / "results.json"

    for required in (repo_root / "maze", repo_root / ".maze", repo_root / ".maze-go-core"):
        if not required.is_file():
            raise IntegrationError("missing %s; run ./maze --build first" % required)

    env = os.environ.copy()
    env["TMPDIR"] = str(build_tmp)
    build_env = env.copy()
    build_env["CGO_ENABLED"] = "0"
    build_env["GOTOOLCHAIN"] = "go1.25.6"
    run_checked(
        ["go", "build", "-trimpath", "-buildvcs=false", "-o", fixture_binary, fixture_source],
        cwd=repo_root,
        env=build_env,
        output_path=work_dir / "build.log",
        timeout=180,
    )

    root_hashes_before = {
        name: sha256_optional(repo_root / name)
        for name in RootResultGuard.preserve_names
    }
    fixture = None
    maze_measurement = None
    try:
        with RootResultGuard(repo_root, work_dir) as guard:
            fixture = launch_fixture(fixture_binary, args.objects, work_dir / "fixture.log")
            maze_measurement = run_monitored(
                [
                    repo_root / "maze",
                    "--pid",
                    str(fixture.pid),
                    "--logdir",
                    prepare_dir,
                    "--text",
                    "--json-output",
                    "--limit",
                    "500",
                    "--no-cpp",
                ],
                cwd=repo_root,
                env=env,
                stdout_path=work_dir / "maze.stdout.log",
                timeout=900,
            )
            guard.collect(maze_result_dir)
            if fixture.poll() is not None:
                raise IntegrationError("fixture did not survive Maze GDB detach")
    finally:
        stop_fixture(fixture)

    root_hashes_after = {
        name: sha256_optional(repo_root / name)
        for name in RootResultGuard.preserve_names
    }
    if root_hashes_before != root_hashes_after:
        raise IntegrationError("repository-root result/log files were not restored")

    cores = list(prepare_dir.glob("core.*"))
    if len(cores) != 1:
        raise IntegrationError("expected one retained core, found %d" % len(cores))
    core_path = cores[0]
    core_storage = {
        "logical_bytes": core_path.stat().st_size,
        "allocated_bytes": allocated_bytes(core_path),
    }

    helper_measurement = run_monitored(
        [
            repo_root / ".maze-go-core",
            "analyze",
            "--core",
            core_path,
            "--exe",
            fixture_binary,
            "--base",
            prepare_dir,
            "--max-objects",
            str(args.objects + 100000),
            "--max-edges",
            str(args.objects * 4 + 100000),
        ],
        cwd=repo_root,
        env=env,
        stdout_path=helper_output,
        stderr_path=helper_stderr,
        timeout=600,
    )
    helper_stream = scan_ndjson(helper_output, args.objects)
    maze_result = validate_maze_json(maze_result_dir / "maze-result.json", args.objects)
    checks, failures = gate_checks(
        args.objects, helper_measurement, maze_measurement, helper_stream, maze_result
    )

    result = {
        "schema": "maze.gocore.performance/v1",
        "qualifying": args.objects >= MIN_QUALIFYING_OBJECTS,
        "sampling": {"process_tree_rss_interval_seconds": SAMPLE_INTERVAL_SECONDS},
        "fixture": {
            "go_version": subprocess.check_output(
                ["go", "version"], env=build_env, text=True
            ).strip(),
            "objects": args.objects,
            "source_sha256": sha256_optional(fixture_source),
            "binary_sha256": sha256_optional(fixture_binary),
        },
        "core": core_storage,
        "helper": helper_measurement,
        "helper_stream": helper_stream,
        "maze": maze_measurement,
        "maze_result": maze_result,
        "root_hashes_before": root_hashes_before,
        "root_hashes_after": root_hashes_after,
        "checks": checks,
        "passed": not failures,
    }
    results_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        raise IntegrationError("performance gate failed: " + "; ".join(failures))

    if not args.keep_large_artifacts:
        core_path.unlink()
        helper_output.unlink()

    print(
        "Go performance gate passed: objects=%d helper_wall=%.2fs helper_peak=%d MiB "
        "maze_wall=%.2fs maze_tree_peak=%d MiB ndjson=%d MiB"
        % (
            args.objects,
            helper_measurement["wall_seconds"],
            helper_measurement["peak_tree_rss_bytes"] // MIB,
            maze_measurement["wall_seconds"],
            maze_measurement["peak_tree_rss_bytes"] // MIB,
            helper_measurement["stdout_bytes"] // MIB,
        )
    )
    print("results: %s" % results_path.relative_to(repo_root))


if __name__ == "__main__":
    try:
        main()
    except (IntegrationError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print("Go performance gate failed: %s" % error, file=sys.stderr)
        raise SystemExit(1)

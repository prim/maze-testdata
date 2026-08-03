#!/usr/bin/env python3

import os
import subprocess
import sys
import threading
import unittest

from run_performance_gate import (
    HELPER_CPU_LIMIT_SECONDS,
    HELPER_WALL_LIMIT_SECONDS,
    MAZE_CPU_LIMIT_SECONDS,
    MAZE_WALL_LIMIT_SECONDS,
    MIB,
    gate_checks,
    process_children,
)


class PerformanceGateChecksTest(unittest.TestCase):
    def setUp(self):
        self.objects = 200000
        self.helper = {
            "wall_seconds": HELPER_WALL_LIMIT_SECONDS,
            "user_cpu_seconds": HELPER_CPU_LIMIT_SECONDS,
            "system_cpu_seconds": 0,
            "peak_tree_rss_bytes": 512 * MIB + self.objects * 1024,
            "stdout_bytes": 64 * MIB + self.objects * 1024,
        }
        self.maze = {
            "wall_seconds": MAZE_WALL_LIMIT_SECONDS,
            "user_cpu_seconds": MAZE_CPU_LIMIT_SECONDS,
            "system_cpu_seconds": 0,
            "peak_tree_rss_bytes": 1024 * MIB + self.objects * 2048,
        }
        self.helper_stream = {
            "trailer": {
                "counts": {
                    "object": self.objects + 100000,
                    "edge": self.objects * 4 + 100000,
                }
            }
        }
        self.maze_result = {"json_bytes": 128 * MIB}

    def checks(self):
        return gate_checks(
            self.objects,
            self.helper,
            self.maze,
            self.helper_stream,
            self.maze_result,
        )

    def test_limits_are_inclusive(self):
        checks, failures = self.checks()
        self.assertFalse(failures)
        self.assertTrue(all(check["passed"] for check in checks.values()))

    def test_each_limit_is_enforced(self):
        cases = (
            (self.helper, "wall_seconds", "helper_wall_seconds"),
            (self.helper, "user_cpu_seconds", "helper_cpu_seconds"),
            (self.helper, "peak_tree_rss_bytes", "helper_peak_tree_rss_bytes"),
            (self.helper, "stdout_bytes", "helper_ndjson_bytes"),
            (self.maze, "wall_seconds", "maze_wall_seconds"),
            (self.maze, "user_cpu_seconds", "maze_cpu_seconds"),
            (self.maze, "peak_tree_rss_bytes", "maze_peak_tree_rss_bytes"),
            (self.maze_result, "json_bytes", "maze_json_bytes"),
            (self.helper_stream["trailer"]["counts"], "object", "helper_object_count"),
            (self.helper_stream["trailer"]["counts"], "edge", "helper_edge_count"),
        )
        for container, field, check_name in cases:
            with self.subTest(check=check_name):
                original = container[field]
                container[field] = original + 1
                checks, failures = self.checks()
                container[field] = original
                self.assertFalse(checks[check_name]["passed"])
                self.assertTrue(any(failure.startswith(check_name + "=") for failure in failures))

    def test_process_children_includes_child_started_by_worker_thread(self):
        ready = threading.Event()
        release = threading.Event()
        state = {}

        def launch_child():
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            state["child"] = child
            ready.set()
            release.wait(timeout=10)
            child.terminate()
            child.wait(timeout=10)

        thread = threading.Thread(target=launch_child)
        thread.start()
        try:
            self.assertTrue(ready.wait(timeout=10))
            self.assertIn(state["child"].pid, process_children(os.getpid()))
        finally:
            release.set()
            thread.join(timeout=10)
            child = state.get("child")
            if child is not None and child.poll() is None:
                child.kill()
                child.wait(timeout=10)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()

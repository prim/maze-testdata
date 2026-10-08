#!/usr/bin/env python3

import unittest
import os
from pathlib import Path
import tempfile

from run_runtime_matrix import preserve_root_outputs, restore_root_outputs, select_cases, verify_build_info


class SelectCasesTest(unittest.TestCase):
    def setUp(self):
        self.cases = [
            {"go_version": "go1.20.14"},
            {"go_version": "go1.26.0"},
        ]

    def test_empty_selection_returns_full_matrix(self):
        self.assertEqual(select_cases(self.cases, []), self.cases)

    def test_exact_selection_preserves_matrix_order(self):
        self.assertEqual(
            select_cases(self.cases, ["go1.26.0", "go1.20.14"]),
            self.cases,
        )

    def test_unknown_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown --version value"):
            select_cases(self.cases, ["go1.27.0"])


class OutputPreservationTest(unittest.TestCase):
    def test_replay_restores_dangling_symlink_and_original_file(self):
        temp_root = Path(__file__).resolve().parents[2] / "tmp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            (root / "maze.log").symlink_to("missing-original-log")
            result = root / "maze-result.txt"
            result.write_text("original")
            original_inode = result.stat().st_ino
            backup, state = preserve_root_outputs(root)
            (root / "maze.log").symlink_to("missing-test-log")
            result.write_text("generated")
            (root / "maze-result.json").write_text("{}")
            restore_root_outputs(root, backup, state)
            self.assertEqual(os.readlink(root / "maze.log"), "missing-original-log")
            self.assertEqual(result.read_text(), "original")
            self.assertEqual(result.stat().st_ino, original_inode)
            self.assertFalse((root / "maze-result.json").exists())


class ExecutableIdentityTest(unittest.TestCase):
    def test_manifest_toolchain_cannot_override_actual_binary_version(self):
        info = {"GoVersion": "go1.25.6", "Settings": [
            {"Key": "GOOS", "Value": "linux"},
            {"Key": "GOARCH", "Value": "amd64"},
            {"Key": "CGO_ENABLED", "Value": "0"},
        ]}
        verify_build_info(info, "go1.25.6")
        with self.assertRaisesRegex(RuntimeError, "executable Go version mismatch"):
            verify_build_info(info, "go1.20.14")


if __name__ == "__main__":
    unittest.main()

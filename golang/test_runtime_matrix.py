#!/usr/bin/env python3

import unittest

from run_runtime_matrix import select_cases


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


if __name__ == "__main__":
    unittest.main()

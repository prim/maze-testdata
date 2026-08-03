#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from validate_managed_heap import validate_case


def validate(data):
    return validate_case(
        data,
        expect_server=False,
        expected_runtime_major=11,
        expect_channels=True,
    )

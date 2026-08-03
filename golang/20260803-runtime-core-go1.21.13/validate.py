#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validate_runtime_fixture import validate_fixture


def validate(data):
    return validate_fixture(data, "go1.21.13")


if __name__ == "__main__":
    import json

    with open(sys.argv[1], "r") as stream:
        payload = json.load(stream)
    raise SystemExit(0 if validate(payload) else 1)

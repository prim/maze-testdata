#!/usr/bin/env bash
set -euo pipefail

case_dir=$(cd "$(dirname "$0")" && pwd)
exec "$case_dir/../generate_runtime_matrix_case.sh" \
	"$case_dir" go1.20.14 coredump-runtime-core-go1.20.14.tar.gz

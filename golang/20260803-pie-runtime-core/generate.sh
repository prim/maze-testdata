#!/usr/bin/env bash
set -euo pipefail

case_dir=$(cd "$(dirname "$0")" && pwd)
exec "$case_dir/../generate_executable_form_case.sh" \
	"$case_dir" go1.25.6 coredump-pie-runtime-core.tar.gz pie

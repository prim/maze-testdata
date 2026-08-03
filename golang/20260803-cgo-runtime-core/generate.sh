#!/usr/bin/env bash
set -euo pipefail

case_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$case_dir/../../.." && pwd)
work_dir="$repo_root/tmp/golang-testdata-cgo-runtime-core"
artifact_dir="$work_dir/artifact"
binary="$work_dir/fixture"

mkdir -p "$repo_root/tmp/go-test" "$work_dir"
rm -rf "$artifact_dir"
mkdir -p "$artifact_dir"

CGO_ENABLED=1 TMPDIR="$repo_root/tmp/go-test" \
	go build -trimpath -buildvcs=false -o "$binary" "$case_dir/fixture.go"

TMPDIR="$repo_root/tmp" python3 "$repo_root/cmd/maze-gen-coredump.py" \
	-o "$artifact_dir" "$binary"

mapfile -t generated < <(find "$artifact_dir" -maxdepth 1 -type f -name 'coredump-*.tar.gz' -print)
if [[ ${#generated[@]} -ne 1 ]]; then
	echo "expected one generated tarball, found ${#generated[@]}" >&2
	exit 1
fi

artifact="$case_dir/coredump-cgo-runtime-core.tar.gz"
mv -f "${generated[0]}" "$artifact"
python3 "$case_dir/../update_manifest.py" \
	"$case_dir/fixture.json" "$case_dir/fixture.go" "$binary" "$artifact"

echo "generated $artifact"

#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
	echo "usage: $0 CASE_DIR GO_TOOLCHAIN ARTIFACT_NAME" >&2
	exit 2
fi

case_dir=$(cd "$1" && pwd)
toolchain=$2
artifact_name=$3
script_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
case_name=$(basename "$case_dir")
work_dir="$repo_root/tmp/golang-testdata-$case_name"
artifact_dir="$work_dir/artifact"
binary="$work_dir/fixture"

mkdir -p "$repo_root/tmp/go-test" "$work_dir"
rm -rf "$artifact_dir"
mkdir -p "$artifact_dir"

actual_toolchain=$(GOTOOLCHAIN="$toolchain" go version | awk '{print $3}')
if [[ "$actual_toolchain" != "$toolchain" ]]; then
	echo "requested $toolchain, got $actual_toolchain" >&2
	exit 1
fi

GOTOOLCHAIN="$toolchain" CGO_ENABLED=0 TMPDIR="$repo_root/tmp/go-test" \
	go build -trimpath -buildvcs=false -o "$binary" "$case_dir/fixture.go"

TMPDIR="$repo_root/tmp" python3 "$repo_root/cmd/maze-gen-coredump.py" \
	-o "$artifact_dir" "$binary"

mapfile -t generated < <(find "$artifact_dir" -maxdepth 1 -type f -name 'coredump-*.tar.gz' -print)
if [[ ${#generated[@]} -ne 1 ]]; then
	echo "expected one generated tarball, found ${#generated[@]}" >&2
	exit 1
fi

artifact="$case_dir/$artifact_name"
mv -f "${generated[0]}" "$artifact"
GOTOOLCHAIN="$toolchain" python3 "$script_dir/update_manifest.py" \
	"$case_dir/fixture.json" "$case_dir/fixture.go" "$binary" "$artifact"

echo "generated $artifact with $toolchain"

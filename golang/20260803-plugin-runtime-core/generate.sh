#!/usr/bin/env bash
set -euo pipefail

case_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$case_dir/../../.." && pwd)
work_dir="$repo_root/tmp/golang-testdata-plugin-runtime-core"
artifact_dir="$work_dir/artifact"
binary="$work_dir/fixture"
plugin_binary="$work_dir/fixture_plugin.so"

mkdir -p "$repo_root/tmp/go-test" "$work_dir"
if [[ -d "$artifact_dir" ]]; then
    while IFS= read -r artifact_file; do
        unlink "$artifact_file"
    done < <(find "$artifact_dir" -maxdepth 1 -type f -name 'coredump-*.tar.gz' -print)
    if ! rmdir "$artifact_dir"; then
        echo "refusing to replace non-empty artifact directory: $artifact_dir" >&2
        exit 1
    fi
fi
mkdir -p "$artifact_dir"

CGO_ENABLED=1 TMPDIR="$repo_root/tmp/go-test" \
	go build -trimpath -buildvcs=false -buildmode=plugin \
	-o "$plugin_binary" "$case_dir/fixture_plugin.go"
CGO_ENABLED=1 TMPDIR="$repo_root/tmp/go-test" \
	go build -trimpath -buildvcs=false -o "$binary" "$case_dir/fixture.go"

TMPDIR="$repo_root/tmp" python3 "$repo_root/cmd/maze-gen-coredump.py" \
	-o "$artifact_dir" "$binary $plugin_binary"

mapfile -t generated < <(find "$artifact_dir" -maxdepth 1 -type f -name 'coredump-*.tar.gz' -print)
if [[ ${#generated[@]} -ne 1 ]]; then
	echo "expected one generated tarball, found ${#generated[@]}" >&2
	exit 1
fi

artifact="$case_dir/coredump-plugin-runtime-core.tar.gz"
mv -f "${generated[0]}" "$artifact"
python3 "$case_dir/../update_manifest.py" \
	"$case_dir/fixture.json" "$case_dir/fixture.go" "$binary" "$artifact" \
	--extra-source "$case_dir/fixture_plugin.go" \
	--extra-binary "plugin=$plugin_binary"

echo "generated $artifact"

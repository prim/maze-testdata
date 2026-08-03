#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
	echo "usage: $0 CASE_DIR GO_TOOLCHAIN ARTIFACT_NAME FORM" >&2
	exit 2
fi

case_dir=$(cd "$1" && pwd)
toolchain=$2
artifact_name=$3
form=$4
script_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
case_name=$(basename "$case_dir")
work_dir="$repo_root/tmp/golang-testdata-$case_name"
artifact_dir="$work_dir/artifact"
analysis_binary="$work_dir/fixture-debug"
runtime_binary="$work_dir/fixture-runtime"

mkdir -p "$repo_root/tmp/go-test" "$work_dir"
if [[ -d "$artifact_dir" ]]; then
	find "$artifact_dir" -mindepth 1 -maxdepth 1 -type f -delete
	rmdir "$artifact_dir"
fi
mkdir "$artifact_dir"

actual_toolchain=$(GOTOOLCHAIN="$toolchain" go version | awk '{print $3}')
if [[ "$actual_toolchain" != "$toolchain" ]]; then
	echo "requested $toolchain, got $actual_toolchain" >&2
	exit 1
fi

case "$form" in
pie)
	GOTOOLCHAIN="$toolchain" CGO_ENABLED=0 TMPDIR="$repo_root/tmp/go-test" \
		go build -trimpath -buildvcs=false -buildmode=pie \
		-o "$runtime_binary" "$case_dir/fixture.go"
	analysis_binary="$runtime_binary"
	;;
stripped-runtime-debug-elf)
	GOTOOLCHAIN="$toolchain" CGO_ENABLED=0 TMPDIR="$repo_root/tmp/go-test" \
		go build -trimpath -buildvcs=false \
		-o "$analysis_binary" "$case_dir/fixture.go"
	cp --reflink=auto -- "$analysis_binary" "$runtime_binary"
	strip --strip-all "$runtime_binary"
	if readelf -S "$runtime_binary" | grep -q '\.debug_info'; then
		echo "runtime ELF still contains .debug_info" >&2
		exit 1
	fi
	if [[ $(go tool buildid "$runtime_binary") != $(go tool buildid "$analysis_binary") ]]; then
		echo "stripping changed the Go Build ID" >&2
		exit 1
	fi
	;;
*)
	echo "unknown executable form: $form" >&2
	exit 2
	;;
esac

TMPDIR="$repo_root/tmp" python3 "$repo_root/cmd/maze-gen-coredump.py" \
	-o "$artifact_dir" "$runtime_binary"

mapfile -t generated < <(find "$artifact_dir" -maxdepth 1 -type f -name 'coredump-*.tar.gz' -print)
if [[ ${#generated[@]} -ne 1 ]]; then
	echo "expected one generated tarball, found ${#generated[@]}" >&2
	exit 1
fi

if [[ "$form" == "stripped-runtime-debug-elf" ]]; then
	python3 "$script_dir/rewrite_analysis_elf.py" "${generated[0]}" "$analysis_binary"
fi

artifact="$case_dir/$artifact_name"
mv -f "${generated[0]}" "$artifact"
manifest_args=(
	"$case_dir/fixture.json" "$case_dir/fixture.go" "$analysis_binary" "$artifact"
)
if [[ "$form" == "stripped-runtime-debug-elf" ]]; then
	manifest_args+=(--extra-binary "runtime=$runtime_binary")
fi
GOTOOLCHAIN="$toolchain" python3 "$script_dir/update_manifest.py" "${manifest_args[@]}"

echo "generated $artifact with $toolchain form=$form"

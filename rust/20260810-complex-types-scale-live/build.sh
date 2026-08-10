#!/usr/bin/env bash
set -euo pipefail

case_dir=$(cd "$(dirname "$0")" && pwd)
profile=${1:-dev}
case "$profile" in
dev|release) ;;
*) echo "usage: $0 [dev|release]" >&2; exit 2 ;;
esac

cargo build --locked --manifest-path "$case_dir/Cargo.toml" --profile "$profile"
output_profile=$profile
if [[ "$profile" == "dev" ]]; then
	output_profile=debug
fi
binary="$case_dir/target/$output_profile/maze-rust-complex-scale"
if [[ ! -x "$binary" ]]; then
	echo "missing fixture binary: $binary" >&2
	exit 1
fi

python3 "$case_dir/generate_manifest.py" \
	--binary "$binary" \
	--cargo-toml "$case_dir/Cargo.toml" \
	--cargo-lock "$case_dir/Cargo.lock" \
	--profile "$profile" \
	--output "$case_dir/rust-artifacts.json"
cp "$case_dir/rust-artifacts.json" "$(dirname "$binary")/rust-artifacts.json"

echo "[OK] binary:   $binary"
echo "[OK] manifest: $case_dir/rust-artifacts.json"

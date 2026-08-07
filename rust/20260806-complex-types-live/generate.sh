#!/usr/bin/env bash
# Generate the Phase 0 Rust fixture capture.
#
# Steps:
#   1. cargo build (dev profile, full DWARF)
#   2. collect the locked build identity into rust-artifacts.json
#      (rustc version, target triple, LLVM, Cargo profile, panic strategy,
#      LTO, debug level, allocator, Cargo.lock digest, executable SHA-256)
#   3. capture the core with the standard maze-gen-coredump.py workflow
#   4. inject rust-artifacts.json into the tar at the archive top level
#      (prepareTarPostmanLayout moves it into the profile directory)
#   5. move the final coredump-*.tar.gz into the case directory
#
# Usage: ./generate.sh   (run from anywhere; must have cargo on PATH)
set -euo pipefail

case_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$case_dir/../../.." && pwd)
case_name=$(basename "$case_dir")
work_dir="$repo_root/tmp/rust-testdata-$case_name"
artifact_dir="$work_dir/artifact"
manifest_json="$work_dir/rust-artifacts.json"
binary="$case_dir/target/debug/maze-rust-fixture"

mkdir -p "$work_dir"
rm -rf "$artifact_dir"
mkdir -p "$artifact_dir"

# --- 1. build the fixture ----------------------------------------------------
echo "[1/4] cargo build (dev, full DWARF)..."
cargo build --manifest-path "$case_dir/Cargo.toml" --profile dev
if [[ ! -x "$binary" ]]; then
	echo "fixture binary not produced: $binary" >&2
	exit 1
fi

# --- 2. collect build identity ----------------------------------------------
echo "[2/4] collecting rust build identity..."
python3 - "$case_dir" "$binary" "$manifest_json" <<'PYEOF'
import hashlib
import json
import os
import re
import subprocess
import sys

case_dir, binary, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

rustc_vv = subprocess.run(
    ["rustc", "-vV"], capture_output=True, text=True, check=True
).stdout


def rustc_field(name):
    m = re.search(r"^%s:\s+(.*)$" % name, rustc_vv, re.MULTILINE)
    return m.group(1).strip() if m else ""


rustc_cfg = subprocess.run(
    ["rustc", "--print", "cfg"], capture_output=True, text=True, check=True
).stdout
panic_strategy = "unwind"
for line in rustc_cfg.splitlines():
    line = line.strip()
    if line.startswith("panic="):
        panic_strategy = line[len('panic="'):-1]

# Default Rust std links the system allocator -> glibc ptmalloc on this target.
allocator = "glibc-ptmalloc"

with open(os.path.join(case_dir, "Cargo.toml"), "r", encoding="utf-8") as stream:
    cargo_toml = stream.read()

cargo_lock_path = os.path.join(case_dir, "Cargo.lock")
with open(cargo_lock_path, "rb") as stream:
    cargo_lock_sha256 = hashlib.sha256(stream.read()).hexdigest()

with open(binary, "rb") as stream:
    binary_sha256 = hashlib.sha256(stream.read()).hexdigest()
binary_size = os.path.getsize(binary)

# GNU Build ID from the ELF notes (readelf -n). This is the build identity the
# typed-root analyzer later requires to match the core's executable exactly.
build_id = ""
try:
    readelf_out = subprocess.run(
        ["readelf", "-n", binary], capture_output=True, text=True, check=True
    ).stdout
    for line in readelf_out.splitlines():
        if "Build ID" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                build_id = parts[1].strip()
            break
except subprocess.CalledProcessError:
    pass

# opt_level / debug_level from the [profile.dev] table of Cargo.toml.
opt_level = "0"
debug_level = "0"
profile_dev = re.search(r"\[profile\.dev\]([^[]*)", cargo_toml)
if profile_dev:
    for line in profile_dev.group(1).splitlines():
        m = re.match(r"\s*opt-level\s*=\s*\"?(\w+)\"?", line)
        if m:
            opt_level = m.group(1)
        m = re.match(r"\s*debug\s*=\s*\"?(\w+)\"?", line)
        if m:
            debug_level = m.group(1)

manifest = {
    "schema": "maze.rust-artifacts/v1",
    "rustc_version": rustc_field("release") or "",
    "host_triple": rustc_field("host") or "",
    "target_triple": rustc_field("host") or "",
    "llvm_version": rustc_field("LLVM version") or "",
    "cargo_profile": "dev",
    "opt_level": opt_level,
    "debug_level": debug_level,
    "lto": "off",
    "panic_strategy": panic_strategy,
    "allocator": allocator,
    "cargo_lock_sha256": cargo_lock_sha256,
    "executable": {
        "build_id": build_id,
        "sha256": binary_sha256,
        "size": binary_size,
    },
}

with open(out_path, "w", encoding="utf-8") as stream:
    json.dump(manifest, stream, indent=2, sort_keys=True)
    stream.write("\n")
print("  manifest: %s" % out_path)
print("  rustc:    %s" % manifest["rustc_version"])
print("  triple:   %s" % manifest["target_triple"])
print("  llvm:     %s" % manifest["llvm_version"])
print("  panic:    %s" % panic_strategy)
PYEOF

# --- 3. capture core + package tar with the standard workflow -----------------
echo "[3/4] capturing core + packaging tar..."
cd "$repo_root"
python3 cmd/maze-gen-coredump.py -o "$artifact_dir" -t 120 "$binary"

# --- 4. inject rust-artifacts.json into the tar -------------------------------
echo "[4/4] injecting rust-artifacts.json into tar..."
python3 - "$artifact_dir" "$manifest_json" <<'PYEOF'
import io
import json
import os
import sys
import tarfile

artifact_dir, manifest_path = sys.argv[1], sys.argv[2]

tars = [f for f in os.listdir(artifact_dir) if f.startswith("coredump-") and f.endswith(".tar.gz")]
if len(tars) != 1:
    raise SystemExit("expected one generated tarball, found %d" % len(tars))
tar_path = os.path.join(artifact_dir, tars[0])

with open(manifest_path, "rb") as stream:
    manifest_data = stream.read()

staging = tar_path + ".with-rust"
with tarfile.open(tar_path, "r:gz") as source, tarfile.open(staging, "w:gz", compresslevel=1) as target:
    for member in source:
        payload = source.extractfile(member)
        target.addfile(member, payload)
    info = tarfile.TarInfo("rust-artifacts.json")
    info.mode = 0o644
    info.size = len(manifest_data)
    target.addfile(info, io.BytesIO(manifest_data))
os.replace(staging, tar_path)
print("  injected: %s" % tar_path)
PYEOF

# --- 5. move into case dir -----------------------------------------------------
tar=$(find "$artifact_dir" -maxdepth 1 -name 'coredump-*.tar.gz' -print -quit)
artifact="$case_dir/$(basename "$tar")"
rm -f "$artifact"
mv "$tar" "$artifact"
# Keep the locked build identity next to the fixture (like golang manifest.json)
# so Go tests and validate.py can read it without unpacking the tar.
cp "$manifest_json" "$case_dir/rust-artifacts.json"
# The fixture writes ground truth to its cwd (the repo root during capture);
# copy it next to the fixture so Phase 1/2 validators can reconcile against it.
if [[ -f "$repo_root/rust-fixture-ground-truth.json" ]]; then
    mv "$repo_root/rust-fixture-ground-truth.json" "$case_dir/rust-fixture-ground-truth.json"
fi
echo "[OK] $artifact"
echo "[OK] $case_dir/rust-artifacts.json"
echo "[OK] $case_dir/rust-fixture-ground-truth.json"

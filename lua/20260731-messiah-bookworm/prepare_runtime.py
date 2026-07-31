#!/usr/bin/env python3
"""Restore the H72 Lua/Messiah runtime from a fixture tar or Maze ELF cache."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile


REQUIRED = {
    "lua": "01b46668e7ca4356e2a56a2a578026e4",
    "asiocore.so": "6c6daceea44e9dc7ee8a0af9521ecceb",
    "libenvsdk.so": "95c16ac73b1eb86615dfd8b1a8c3ceaf",
    "libjemalloc_prof.so": "1203c103036ca5a58470921659cff81a",
    "libc.so.6": "93283f4792e89ca473d0593b04f10c09",
    "ld-linux-x86-64.so.2": "395f1f15882967bfbff866832ccac983",
}


def md5_file(path):
    digest = hashlib.md5()
    with open(str(path), "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tar_source(path):
    archive = tarfile.open(str(path), "r:gz")
    manifests = [member for member in archive.getmembers() if member.name.endswith(".md5")]
    if len(manifests) != 1:
        archive.close()
        raise RuntimeError("expected one .md5 manifest in %s" % path)
    stream = archive.extractfile(manifests[0])
    if stream is None:
        archive.close()
        raise RuntimeError("cannot read %s" % manifests[0].name)
    mapping = json.loads(stream.read().decode("utf-8"))

    members = {member.name.lstrip("./"): member for member in archive.getmembers()}

    def copy_digest(digest, destination):
        member = members.get(digest)
        if member is None:
            raise RuntimeError("ELF %s is missing from %s" % (digest, path))
        source = archive.extractfile(member)
        if source is None:
            raise RuntimeError("cannot extract ELF %s" % digest)
        with open(str(destination), "wb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
        os.chmod(str(destination), member.mode)

    return mapping, copy_digest, archive.close


def load_cache_source(manifest, elf_dir):
    with open(str(manifest), "r") as source:
        mapping = json.load(source)

    def copy_digest(digest, destination):
        source = elf_dir / digest
        if not source.is_file():
            raise RuntimeError("ELF cache entry is missing: %s" % source)
        shutil.copyfile(str(source), str(destination))
        os.chmod(str(destination), source.stat().st_mode & 0o777)

    return mapping, copy_digest, lambda: None


def reset_output(path, maze_root):
    allowed_root = (maze_root / "tmp").resolve()
    resolved = path.resolve()
    if resolved == allowed_root or allowed_root not in resolved.parents:
        raise RuntimeError("runtime output must be below %s" % allowed_root)
    if resolved.exists():
        shutil.rmtree(str(resolved))
    resolved.mkdir(parents=True)
    return resolved


def main():
    script = Path(__file__).resolve()
    maze_root = script.parents[3]
    test_dir = script.parent
    default_tarballs = sorted(test_dir.glob("coredump-*.tar.gz"))

    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--tar", type=Path)
    source.add_argument("--manifest", type=Path)
    parser.add_argument("--elf-dir", type=Path, default=maze_root / "db" / "elf")
    parser.add_argument(
        "--output",
        type=Path,
        default=maze_root / "tmp" / "h72-messiah-test-runtime",
    )
    args = parser.parse_args()

    if args.manifest:
        mapping, copy_digest, close_source = load_cache_source(
            args.manifest.resolve(), args.elf_dir.resolve()
        )
    else:
        tarball = args.tar
        if tarball is None:
            if len(default_tarballs) != 1:
                raise RuntimeError("specify --tar; expected exactly one committed fixture")
            tarball = default_tarballs[0]
        try:
            mapping, copy_digest, close_source = load_tar_source(tarball.resolve())
        except tarfile.ReadError as error:
            raise RuntimeError("cannot open fixture; run git lfs pull: %s" % error)

    output = reset_output(args.output, maze_root)
    basenames = {}
    try:
        for original_path, digest in sorted(mapping.items()):
            basename = os.path.basename(original_path)
            previous = basenames.get(basename)
            if previous and previous != digest:
                raise RuntimeError("conflicting runtime basename: %s" % basename)
            basenames[basename] = digest
        for basename, digest in sorted(basenames.items()):
            destination = output / basename
            copy_digest(digest, destination)
            actual = md5_file(destination)
            if actual != digest:
                raise RuntimeError("MD5 mismatch for %s: %s != %s" % (basename, actual, digest))
    finally:
        close_source()

    for basename, digest in REQUIRED.items():
        if basenames.get(basename) != digest:
            raise RuntimeError("unexpected H72 runtime %s: %s" % (basename, basenames.get(basename)))

    os.chmod(str(output / "lua"), 0o755)
    print("Restored %d runtime files to %s" % (len(basenames), output))


if __name__ == "__main__":
    main()

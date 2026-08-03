#!/usr/bin/env python3

import argparse
import copy
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path


def md5_bytes(data):
    return hashlib.md5(data).hexdigest()


def read_member(archive, member):
    stream = archive.extractfile(member)
    if stream is None:
        raise RuntimeError("cannot read archive member %s" % member.name)
    with stream:
        return stream.read()


def main():
    parser = argparse.ArgumentParser(
        description="Replace a captured stripped executable with its exact DWARF ELF"
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("analysis_elf", type=Path)
    args = parser.parse_args()

    archive_path = args.archive.resolve()
    analysis_path = args.analysis_elf.resolve()
    analysis_data = analysis_path.read_bytes()
    analysis_name = md5_bytes(analysis_data)
    temporary = archive_path.with_name(archive_path.name + ".rewrite")

    with tarfile.open(str(archive_path), "r:gz") as source:
        members = source.getmembers()
        exe_members = [member for member in members if Path(member.name).suffix == ".exe"]
        md5_members = [member for member in members if Path(member.name).suffix == ".md5"]
        if len(exe_members) != 1 or len(md5_members) != 1:
            raise RuntimeError("archive must contain exactly one .exe and one .md5 member")
        executable_path = read_member(source, exe_members[0]).decode("utf-8")
        mapping = json.loads(read_member(source, md5_members[0]).decode("utf-8"))
        runtime_name = mapping.get(executable_path)
        runtime_members = [member for member in members if member.name == runtime_name]
        if len(runtime_members) != 1:
            raise RuntimeError("captured executable member %r is missing" % runtime_name)
        if analysis_name == runtime_name:
            raise RuntimeError("analysis ELF is not distinct from the stripped runtime ELF")
        mapping[executable_path] = analysis_name
        mapping_data = json.dumps(mapping, sort_keys=True).encode("utf-8")

        with tarfile.open(str(temporary), "w:gz", compresslevel=1) as destination:
            for member in members:
                if member.name == md5_members[0].name:
                    rewritten = copy.copy(member)
                    rewritten.size = len(mapping_data)
                    destination.addfile(rewritten, io.BytesIO(mapping_data))
                    continue
                if member.name == runtime_name:
                    retained = copy.copy(member)
                    retained.name = "runtime-stripped"
                    destination.addfile(retained, source.extractfile(member))
                    analysis = copy.copy(member)
                    analysis.name = analysis_name
                    analysis.size = len(analysis_data)
                    destination.addfile(analysis, io.BytesIO(analysis_data))
                    continue
                destination.addfile(member, source.extractfile(member) if member.isfile() else None)

    os.replace(str(temporary), str(archive_path))


if __name__ == "__main__":
    main()

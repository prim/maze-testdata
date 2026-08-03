#!/usr/bin/env python3

import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path


INVALID_RUNTIME_POINTER = 0x700000000000


def sha256_path(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sparse_copy(source, destination):
    subprocess.run(
        ["cp", "--sparse=always", "--", str(source), str(destination)],
        check=True,
    )


class ELF64:
    def __init__(self, path):
        self.path = path
        with path.open("rb") as stream:
            header = stream.read(64)
        if len(header) != 64 or header[:4] != b"\x7fELF" or header[4] != 2 or header[5] != 1:
            raise RuntimeError("%s is not little-endian ELF64" % path)
        self.phoff = struct.unpack_from("<Q", header, 32)[0]
        self.shoff = struct.unpack_from("<Q", header, 40)[0]
        self.phentsize = struct.unpack_from("<H", header, 54)[0]
        self.phnum = struct.unpack_from("<H", header, 56)[0]
        self.shentsize = struct.unpack_from("<H", header, 58)[0]
        self.shnum = struct.unpack_from("<H", header, 60)[0]
        self.shstrndx = struct.unpack_from("<H", header, 62)[0]
        if self.phentsize != 56 or self.shentsize not in (0, 64):
            raise RuntimeError("%s has unsupported ELF table sizes" % path)

    def program_headers(self):
        headers = []
        with self.path.open("rb") as stream:
            for index in range(self.phnum):
                entry_offset = self.phoff + index * self.phentsize
                stream.seek(entry_offset)
                data = stream.read(self.phentsize)
                if len(data) != self.phentsize:
                    raise RuntimeError("%s has a truncated program table" % self.path)
                values = struct.unpack("<IIQQQQQQ", data)
                headers.append({
                    "index": index,
                    "entry_offset": entry_offset,
                    "type": values[0],
                    "flags": values[1],
                    "offset": values[2],
                    "vaddr": values[3],
                    "filesz": values[5],
                    "memsz": values[6],
                })
        return headers

    def load_for(self, address, require_file_data=False):
        for header in self.program_headers():
            if header["type"] != 1:
                continue
            size = header["filesz"] if require_file_data else header["memsz"]
            if header["vaddr"] <= address < header["vaddr"] + size:
                return header
        raise RuntimeError("%s has no PT_LOAD for %#x" % (self.path, address))

    def set_program_filesz(self, header, size):
        if size < 0 or size > header["memsz"]:
            raise RuntimeError("invalid PT_LOAD file size %#x" % size)
        with self.path.open("r+b") as stream:
            stream.seek(header["entry_offset"] + 32)
            stream.write(struct.pack("<Q", size))

    def write_virtual(self, address, data):
        header = self.load_for(address, require_file_data=True)
        if address + len(data) > header["vaddr"] + header["filesz"]:
            raise RuntimeError("virtual write crosses PT_LOAD")
        offset = header["offset"] + address - header["vaddr"]
        with self.path.open("r+b") as stream:
            stream.seek(offset)
            stream.write(data)

    def sections(self):
        if self.shoff == 0 or self.shnum == 0 or self.shstrndx >= self.shnum:
            return []
        raw = []
        with self.path.open("rb") as stream:
            for index in range(self.shnum):
                stream.seek(self.shoff + index * self.shentsize)
                data = stream.read(self.shentsize)
                if len(data) != self.shentsize:
                    raise RuntimeError("%s has a truncated section table" % self.path)
                values = struct.unpack("<IIQQQQIIQQ", data)
                raw.append({"name_offset": values[0], "offset": values[4], "size": values[5]})
            strings = raw[self.shstrndx]
            stream.seek(strings["offset"])
            names = stream.read(strings["size"])
        for section in raw:
            begin = section["name_offset"]
            end = names.find(b"\x00", begin)
            if begin >= len(names) or end < 0:
                raise RuntimeError("%s has an invalid section name" % self.path)
            section["name"] = names[begin:end].decode("ascii", errors="replace")
        return raw

    def corrupt_section_prefix(self, name):
        matches = [section for section in self.sections() if section["name"] == name]
        if len(matches) != 1 or matches[0]["size"] < 4:
            raise RuntimeError("%s has no usable %s" % (self.path, name))
        with self.path.open("r+b") as stream:
            stream.seek(matches[0]["offset"])
            stream.write(b"\x00\x00\x00\x00")

    def flip_section_byte(self, name):
        matches = [section for section in self.sections() if section["name"] == name]
        if len(matches) != 1 or matches[0]["size"] < 1:
            raise RuntimeError("%s has no usable %s" % (self.path, name))
        with self.path.open("r+b") as stream:
            stream.seek(matches[0]["offset"])
            value = stream.read(1)
            if len(value) != 1:
                raise RuntimeError("%s has truncated %s" % (self.path, name))
            stream.seek(matches[0]["offset"])
            stream.write(bytes([value[0] ^ 1]))


def go_symbols(executable):
    output = subprocess.check_output(["go", "tool", "nm", str(executable)], text=True)
    symbols = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 3:
            try:
                symbols[fields[2]] = int(fields[0], 16)
            except ValueError:
                continue
    return symbols


def runtime_field_addresses(executable, core):
    expression = (
        "python import gdb,json; "
        "m=gdb.parse_and_eval(\"'runtime.mheap_'\"); "
        "spans=m['allspans']; "
        "live=[spans['array'][i].dereference() for i in range(int(spans['len'])) "
        "if int(spans['array'][i].dereference()['nelems']) > 0]; "
        "manual=[spans['array'][i].dereference() for i in range(int(spans['len'])) "
        "if int(spans['array'][i].dereference()['manualFreeList']) != 0]; "
        "gs=gdb.parse_and_eval(\"'runtime.allgs'\"); "
        "stacked=[gs['array'][i].dereference() for i in range(int(gs['len'])) "
        "if int(gs['array'][i].dereference()['stack']['hi']) > "
        "int(gs['array'][i].dereference()['stack']['lo'])]; "
        "s=live[0]; ms=manual[0]; g=stacked[0]; "
        "print('MAZE_RUNTIME_FIELDS='+json.dumps({"
        "'nelems':int(s['nelems'].address),"
        "'nelems_size':int(s['nelems'].type.sizeof),"
        "'freeindex':int(s['freeindex'].address),"
        "'freeindex_size':int(s['freeindex'].type.sizeof),"
        "'specials':int(s['specials'].address),"
        "'specials_size':int(s['specials'].type.sizeof),"
        "'manual_head':int(ms['manualFreeList']),"
        "'stack_lo_value':int(g['stack']['lo']),"
        "'stack_hi':int(g['stack']['hi'].address),"
        "'stack_hi_size':int(g['stack']['hi'].type.sizeof)"
        "},sort_keys=True))"
    )
    process = subprocess.run(
        [
            "gdb", "-q", "-nx", "-batch",
            "--se=" + str(executable),
            "--core=" + str(core),
            "-ex", expression,
        ],
        capture_output=True,
        text=True,
    )
    marker = "MAZE_RUNTIME_FIELDS="
    lines = [line for line in process.stdout.splitlines() if line.startswith(marker)]
    if process.returncode != 0 or len(lines) != 1:
        raise RuntimeError(
            "failed to resolve runtime fields with GDB:\nstdout=%s\nstderr=%s" %
            (process.stdout, process.stderr)
        )
    fields = json.loads(lines[0][len(marker):])
    for name in ("nelems_size", "freeindex_size"):
        if fields[name] not in (2, 8):
            raise RuntimeError("unexpected %s %d" % (name, fields[name]))
    if fields["specials_size"] != 8 or fields["stack_hi_size"] != 8:
        raise RuntimeError("unexpected pointer-sized runtime field metadata %s" % fields)
    return fields


def legacy_gc_program_address(executable, core):
    expression = (
        "python import gdb,json; "
        "v=gdb.parse_and_eval(\"'main.GlobalGCProg'\"); "
        "t=v['_type'].dereference(); "
        "print('MAZE_GCPROG='+json.dumps({"
        "'type':int(v['_type']),"
        "'kind':int(t['Kind_']),"
        "'gcdata':int(t['GCData'])"
        "},sort_keys=True))"
    )
    process = subprocess.run(
        [
            "gdb", "-q", "-nx", "-batch",
            "--se=" + str(executable),
            "--core=" + str(core),
            "-ex", expression,
        ],
        capture_output=True,
        text=True,
    )
    marker = "MAZE_GCPROG="
    lines = [line for line in process.stdout.splitlines() if line.startswith(marker)]
    if process.returncode != 0 or len(lines) != 1:
        raise RuntimeError(
            "failed to resolve legacy GC program with GDB:\nstdout=%s\nstderr=%s" %
            (process.stdout, process.stderr)
        )
    fields = json.loads(lines[0][len(marker):])
    if fields["type"] == 0 or fields["gcdata"] == 0 or fields["kind"] & (1 << 6) == 0:
        raise RuntimeError("main.GlobalGCProg does not use a valid runtime GC program: %s" % fields)
    return fields["gcdata"]


def unsigned_bytes(size, value):
    if size == 2:
        return struct.pack("<H", value)
    if size == 8:
        return struct.pack("<Q", value)
    raise RuntimeError("unsupported unsigned field size %d" % size)


def find_embedded_executable(directory, expected_sha256):
    matches = []
    for path in directory.iterdir():
        if not path.is_file() or path.name.startswith("core."):
            continue
        if path.stat().st_size > 32 * 1024 * 1024:
            continue
        if sha256_path(path) == expected_sha256:
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError("expected one embedded executable, found %d" % len(matches))
    return matches[0]


def plugin_core_input(maps_path, local_file, expected_sha256):
    original_files = set()
    mappings = []
    for line in maps_path.read_text(encoding="utf-8").splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6 or Path(fields[5]).name != "fixture_plugin.so":
            continue
        begin_text, end_text = fields[0].split("-", 1)
        original_files.add(fields[5])
        mappings.append({
            "begin": int(begin_text, 16),
            "end": int(end_text, 16),
            "offset": int(fields[2], 16),
            "flags": fields[1],
            "file": fields[5],
            "local_file": str(local_file.resolve()),
            "local_file_sha256": expected_sha256,
        })
    if len(original_files) != 1 or len(mappings) < 3:
        raise RuntimeError("expected one plugin path with at least three mappings")
    return json.dumps(
        {"schema": "maze.gocore.input/v2", "mappings": mappings},
        separators=(",", ":"),
        sort_keys=True,
    )


def run_failure_case(
        helper, name, core, executable, expected_code, expected_stage,
        evidence_keys=(), core_input=None, allow_late_diagnostic=False,
        helper_command="inspect"):
    command = [str(helper), helper_command, "--core", str(core), "--exe", str(executable)]
    if core_input is not None:
        command.append("--core-input-stdin")
    process = subprocess.run(
        command,
        input=core_input,
        capture_output=True,
        text=True,
    )
    records = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    if process.returncode == 0:
        raise RuntimeError("%s unexpectedly succeeded" % name)
    if (len(records) < 2 or records[0].get("kind") != "header" or
            records[-1].get("kind") != "diagnostic"):
        raise RuntimeError("%s did not produce a header and final diagnostic: %s" % (name, process.stdout))
    if not allow_late_diagnostic and len(records) != 2:
        raise RuntimeError("%s unexpectedly emitted normal records before its diagnostic: %s" % (name, process.stdout))
    diagnostic = records[-1]
    if diagnostic.get("severity") != "fatal" or diagnostic.get("code") != expected_code or diagnostic.get("stage") != expected_stage:
        raise RuntimeError("%s diagnostic mismatch: %s" % (name, diagnostic))
    if any(record.get("kind") == "trailer" for record in records):
        raise RuntimeError("%s emitted a complete trailer" % name)
    evidence = diagnostic.get("evidence", {})
    for key in evidence_keys:
        if not evidence.get(key):
            raise RuntimeError("%s diagnostic lacks %s evidence" % (name, key))
    for forbidden in ("goroutine ", "runtime/debug.Stack", "maze-go-core panic"):
        if forbidden in process.stderr:
            raise RuntimeError("%s leaked a raw panic stack to stderr" % name)
    if expected_code not in process.stderr:
        raise RuntimeError("%s stderr lacks its stable diagnostic code" % name)
    if core_input is not None:
        payload_sha256 = hashlib.sha256(core_input.encode("utf-8")).hexdigest()
        header = records[0]
        if (header.get("core_input_schema") != "maze.gocore.input/v2" or
                header.get("core_input_sha256") != payload_sha256 or
                header.get("core_input_mappings") == 0):
            raise RuntimeError("%s did not bind its CoreInput identity: %s" % (name, header))
    print("validated %-24s code=%s stage=%s" % (name, expected_code, expected_stage))
    return {
        "name": name,
        "exit_code": process.returncode,
        "record_count": len(records),
        "complete": False,
        "diagnostic": diagnostic,
    }


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    helper = repo_root / ".maze-go-core"
    case_dir = script_dir / "20260803-runtime-core"
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    artifact = case_dir / manifest["artifact"]["path"]
    if sha256_path(artifact) != manifest["artifact"]["sha256"]:
        raise SystemExit("base artifact SHA-256 does not match its manifest")
    if not helper.is_file():
        raise SystemExit("build the helper first with ./maze --build")

    work = repo_root / "tmp" / "golang-corrupt-matrix"
    if work.is_symlink() or (work.exists() and not work.is_dir()):
        raise SystemExit("refusing unsafe work path %s" % work)
    if work.exists():
        shutil.rmtree(str(work))
    work.mkdir(parents=True)
    subprocess.run(["tar", "--sparse", "-xzf", str(artifact), "-C", str(work)], check=True)

    cores = list(work.glob("core.*"))
    if len(cores) != 1 or cores[0].stat().st_size != manifest["artifact"]["core_logical_bytes"]:
        raise SystemExit("base archive does not contain the expected core")
    extracted_core = cores[0]
    executable = find_embedded_executable(work, manifest["build"]["binary_sha256"])
    symbols = go_symbols(executable)
    for required in ("runtime.mheap_", "runtime.allgs", "runtime.buildVersion"):
        if required not in symbols:
            raise SystemExit("missing symbol %s" % required)

    valid_core = work / "core-valid"
    missing_page_core = work / "core-missing-runtime-page"
    corrupt_pointer_core = work / "core-corrupt-runtime-pointer"
    corrupt_slice_core = work / "core-corrupt-runtime-slice"
    oversized_string_core = work / "core-oversized-runtime-string"
    corrupt_nelems_core = work / "core-corrupt-span-nelems"
    corrupt_freeindex_core = work / "core-corrupt-span-freeindex"
    cyclic_specials_core = work / "core-cyclic-span-specials"
    cyclic_manual_core = work / "core-cyclic-manual-freelist"
    reversed_stack_core = work / "core-reversed-goroutine-stack"
    truncated_core = work / "core-truncated"
    for destination in (
            valid_core, missing_page_core, corrupt_pointer_core, corrupt_slice_core,
            oversized_string_core, corrupt_nelems_core, corrupt_freeindex_core,
            cyclic_specials_core, cyclic_manual_core, reversed_stack_core,
            truncated_core):
        sparse_copy(extracted_core, destination)

    runtime_fields = runtime_field_addresses(executable, valid_core)

    missing_elf = ELF64(missing_page_core)
    mheap = symbols["runtime.mheap_"]
    mheap_load = missing_elf.load_for(mheap, require_file_data=True)
    missing_begin = (mheap - mheap_load["vaddr"]) & ~0xFFF
    if missing_begin <= 0 or missing_begin >= mheap_load["filesz"]:
        raise SystemExit("runtime.mheap_ is not suitable for the missing-page mutation")
    missing_elf.set_program_filesz(mheap_load, missing_begin)

    corrupt_elf = ELF64(corrupt_pointer_core)
    corrupt_elf.write_virtual(symbols["runtime.allgs"], struct.pack("<Q", INVALID_RUNTIME_POINTER))
    ELF64(corrupt_slice_core).write_virtual(
        symbols["runtime.allgs"] + 8, struct.pack("<q", (1 << 63) - 1),
    )
    ELF64(oversized_string_core).write_virtual(
        symbols["runtime.buildVersion"] + 8, struct.pack("<Q", (1 << 20) + 1),
    )
    ELF64(corrupt_nelems_core).write_virtual(
        runtime_fields["nelems"],
        unsigned_bytes(
            runtime_fields["nelems_size"],
            (1 << (runtime_fields["nelems_size"] * 8)) - 1,
        ),
    )
    ELF64(corrupt_freeindex_core).write_virtual(
        runtime_fields["freeindex"],
        unsigned_bytes(
            runtime_fields["freeindex_size"],
            (1 << (runtime_fields["freeindex_size"] * 8)) - 1,
        ),
    )
    ELF64(cyclic_specials_core).write_virtual(
        runtime_fields["specials"], struct.pack("<Q", runtime_fields["specials"]),
    )
    ELF64(cyclic_manual_core).write_virtual(
        runtime_fields["manual_head"], struct.pack("<Q", runtime_fields["manual_head"]),
    )
    ELF64(reversed_stack_core).write_virtual(
        runtime_fields["stack_hi"], struct.pack("<Q", runtime_fields["stack_lo_value"] - 1),
    )
    os.truncate(truncated_core, truncated_core.stat().st_size - 1)
    extracted_core.unlink()

    no_dwarf_executable = work / "exe-no-dwarf"
    corrupt_dwarf_executable = work / "exe-corrupt-dwarf"
    shutil.copy2(str(executable), str(no_dwarf_executable))
    shutil.copy2(str(executable), str(corrupt_dwarf_executable))
    subprocess.run(["objcopy", "--strip-debug", str(no_dwarf_executable)], check=True)
    ELF64(corrupt_dwarf_executable).corrupt_section_prefix(".debug_info")

    plugin_case_dir = script_dir / "20260803-plugin-runtime-core"
    plugin_manifest = json.loads((plugin_case_dir / "manifest.json").read_text(encoding="utf-8"))
    plugin_artifact = plugin_case_dir / plugin_manifest["artifact"]["path"]
    if sha256_path(plugin_artifact) != plugin_manifest["artifact"]["sha256"]:
        raise SystemExit("plugin artifact SHA-256 does not match its manifest")
    plugin_work = work / "plugin-fixture"
    plugin_work.mkdir()
    subprocess.run(["tar", "--sparse", "-xzf", str(plugin_artifact), "-C", str(plugin_work)], check=True)
    plugin_cores = list(plugin_work.glob("core.*"))
    if len(plugin_cores) != 1 or plugin_cores[0].stat().st_size != plugin_manifest["artifact"]["core_logical_bytes"]:
        raise SystemExit("plugin archive does not contain the expected core")
    plugin_core = plugin_work / "core-valid"
    sparse_copy(plugin_cores[0], plugin_core)
    plugin_cores[0].unlink()
    plugin_executable = find_embedded_executable(plugin_work, plugin_manifest["build"]["binary_sha256"])
    plugin_expected_sha256 = plugin_manifest["build"]["artifacts"]["plugin"]["sha256"]
    plugin_elf = find_embedded_executable(plugin_work, plugin_expected_sha256)
    substitute_plugin = plugin_work / "substitute-plugin.so"
    shutil.copy2(str(plugin_elf), str(substitute_plugin))
    original_layout = ELF64(plugin_elf).program_headers()
    ELF64(substitute_plugin).flip_section_byte(".debug_info")
    if (substitute_plugin.stat().st_size != plugin_elf.stat().st_size or
            ELF64(substitute_plugin).program_headers() != original_layout or
            sha256_path(substitute_plugin) == plugin_expected_sha256):
        raise SystemExit("substitute plugin mutation did not preserve PT_LOAD layout and change content")
    wrong_plugin_input = plugin_core_input(
        plugin_work / "maps", substitute_plugin, plugin_expected_sha256,
    )

    gcprog_case_dir = script_dir / "20260803-runtime-core-go1.23.0"
    gcprog_manifest = json.loads((gcprog_case_dir / "manifest.json").read_text(encoding="utf-8"))
    gcprog_artifact = gcprog_case_dir / gcprog_manifest["artifact"]["path"]
    if sha256_path(gcprog_artifact) != gcprog_manifest["artifact"]["sha256"]:
        raise SystemExit("Go 1.23 GC-program artifact SHA-256 does not match its manifest")
    gcprog_work = work / "gcprog-fixture"
    gcprog_work.mkdir()
    subprocess.run(["tar", "--sparse", "-xzf", str(gcprog_artifact), "-C", str(gcprog_work)], check=True)
    gcprog_cores = list(gcprog_work.glob("core.*"))
    if len(gcprog_cores) != 1 or gcprog_cores[0].stat().st_size != gcprog_manifest["artifact"]["core_logical_bytes"]:
        raise SystemExit("Go 1.23 GC-program archive does not contain the expected core")
    corrupt_gcprog_core = gcprog_work / "core-corrupt-gc-program"
    sparse_copy(gcprog_cores[0], corrupt_gcprog_core)
    gcprog_cores[0].unlink()
    gcprog_executable = find_embedded_executable(gcprog_work, gcprog_manifest["build"]["binary_sha256"])
    gcdata = legacy_gc_program_address(gcprog_executable, corrupt_gcprog_core)
    ELF64(corrupt_gcprog_core).write_virtual(gcdata + 4, b"\x00")

    results = [
        run_failure_case(helper, "truncated-core", truncated_core, executable, "GOCORE_NOT_ELF_CORE", "core-load"),
        run_failure_case(
            helper, "missing-runtime-page", missing_page_core, executable,
            "GOCORE_CORE_PAGE_MISSING", "go-runtime-load", ("address", "stack_hash"),
        ),
        run_failure_case(
            helper, "corrupt-runtime-pointer", corrupt_pointer_core, executable,
            "GOCORE_CORRUPT_POINTER", "go-runtime-load", ("source", "target", "pointer_type", "stack_hash"),
        ),
        run_failure_case(
            helper, "corrupt-runtime-slice", corrupt_slice_core, executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "go-runtime-load",
            ("address", "component", "detail", "stack_hash"),
        ),
        run_failure_case(
            helper, "oversized-runtime-string", oversized_string_core, executable,
            "GOCORE_RESOURCE_LIMIT", "go-runtime-load",
            ("address", "component", "actual", "limit", "stack_hash"),
        ),
        run_failure_case(
            helper, "corrupt-span-nelems", corrupt_nelems_core, executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "go-runtime-load",
            ("address", "component", "detail", "stack_hash"),
        ),
        run_failure_case(
            helper, "corrupt-span-freeindex", corrupt_freeindex_core, executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "go-runtime-load",
            ("address", "component", "detail", "stack_hash"),
        ),
        run_failure_case(
            helper, "cyclic-span-specials", cyclic_specials_core, executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "go-runtime-load",
            ("address", "component", "detail", "stack_hash"),
        ),
        run_failure_case(
            helper, "cyclic-manual-freelist", cyclic_manual_core, executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "go-runtime-load",
            ("address", "component", "detail", "stack_hash"),
        ),
        run_failure_case(
            helper, "reversed-goroutine-stack", reversed_stack_core, executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "go-runtime-load",
            ("address", "component", "detail", "stack_hash"),
        ),
        run_failure_case(helper, "missing-dwarf", valid_core, no_dwarf_executable, "GOCORE_DWARF_MISSING", "go-runtime-load"),
        run_failure_case(helper, "corrupt-dwarf", valid_core, corrupt_dwarf_executable, "GOCORE_DWARF_MISSING", "go-runtime-load"),
        run_failure_case(
            helper, "wrong-main-go-elf", valid_core, plugin_executable,
            "GOCORE_EXECUTABLE_MISMATCH", "executable-identity",
            ("core_entry", "executable_entry"),
        ),
        run_failure_case(
            helper, "wrong-external-go-elf", plugin_core, plugin_executable,
            "GOCORE_INPUT_INVALID", "core-input", core_input=wrong_plugin_input,
        ),
        run_failure_case(
            helper, "corrupt-runtime-gc-program", corrupt_gcprog_core, gcprog_executable,
            "GOCORE_RUNTIME_LAYOUT_MISMATCH", "objects",
            ("address", "component", "detail", "stack_hash"),
            allow_late_diagnostic=True,
            helper_command="analyze",
        ),
    ]
    (work / "results.json").write_text(
        json.dumps({"schema": "maze.golang.corrupt-matrix/v1", "cases": results}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("wrote %s" % (work / "results.json"))


if __name__ == "__main__":
    main()

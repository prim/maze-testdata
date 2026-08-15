#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Formal same-core Local API acceptance for the Elixir 1.18.4 fixture.

Starts a resident Maze session in one self-contained subprocess and verifies
against the real fixture objects:

  * the v28 contract from the session's own maze-result.json (term_unsupported
    count == 0, graph/term_graph complete, term_graph_precision exact, every
    *_status complete with flavor_status=verified, and
    known_size == allocator_native_covered_bytes);
  * runtime identity over /api/erlang-runtime overview (Build ID f94f08...,
    OTP 27, ERTS 15.2.7, flavor elixir 1.18.4 verified, L4 / global-term-graph /
    complete / exact);
  * all 8 structured BEAM endpoints (runtime/search/object/root-path/aggregate/
    roots/reachable/dominator), each with success + applicable completeness;
  * the /api/exec console commands (text 500, p, ref, ref-dot, sizetree,
    erlang-* aliases);
  * the DUAL-FORM sub-binary chain, located deterministically through
    /api/erlang-roots source=process-dictionary (roots.go exposes every ProcDict
    bucket as a root):
      - small_slice16  (key maze_small_slice16_live): an `Erlang heap binary`
        logical=16 with NO referent chain to the 8000-byte refc Binary;
      - sub_binary100  (key maze_sub_binary100_live): an `Erlang sub-binary`
        logical=100 whose referent chain reaches the same 8000-byte refc Binary
        via a single BinRef.

The Maze subprocess is spawned with `--local-api --json-output --output-dir
<session>/results --logdir <session>/work`, both Maze and core as absolute
paths, with the working directory set to the session directory so ref/sizetree
PNG/DOT artifacts land inside the session. Only that session directory is ever
removed in the finally block; the repository root and any user-owned
maze-result.json are never touched.

No candidate fallback: any missing/duplicate key, multiple 8000-byte refc
binaries, multiple BinRefs, truncated inventory pagination, or ambiguous chain
fails closed.

Usage:
    python3 accept_local_api.py --core .../coredump-*.tar.gz \
        --ground-truth .../ground-truth.txt [--maze ./maze] [--timeout 240]
"""
from __future__ import print_function

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

EXPECTED_BUILD_ID = "f94f08a81260ba544812ca2d62f479a794dc7c77"
EXPECTED_ELIXIR = "1.18.4"
RESULTS_NAME = "maze-result.json"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def post_json(base, path, payload):
    request = urllib.request.Request(
        base + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


def get_json(base, path):
    with urllib.request.urlopen(base + path, timeout=180) as response:
        return json.loads(response.read().decode())


def obj_chain(base, address, depth=3):
    return post_json(base, "/api/erlang-object", {"address": address, "depth": depth, "string_bytes": 160})


def exec_cmd(base, command):
    resp = post_json(base, "/api/exec", {"command": command})
    out = resp.get("output") or ""
    require(out != "", "console command %r produced no output" % command)
    require("usage" not in out.lower() and "Traceback" not in out, "console command %r reported usage/error" % command)
    return out


def wait_ready(base, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status = get_json(base, "/api/status")
            if status.get("ready") is True:
                return status
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            pass
        time.sleep(2)
    raise AssertionError("maze Local API did not become ready")


def discover_base(log_path, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(log_path) as source:
                data = source.read()
            match = re.search(r"http://127\.0\.0\.1:(\d+)", data)
            if match:
                return "http://127.0.0.1:%s" % match.group(1)
        except OSError:
            pass
        time.sleep(2)
    raise AssertionError("maze Local API did not start within %ds" % timeout)


def load_ground_truth(path):
    values = {}
    with open(path) as source:
        for raw in source:
            line = raw.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    require(bool(values), "ground-truth file is empty")
    require("fixture_pid" in values, "ground-truth missing fixture_pid")
    require(values.get("small_slice16_size") == "16" and values.get("small_slice16_referenced_size") == "128",
            "ground-truth small_slice16 constants mismatch")
    require(values.get("sub_binary100_size") == "100" and values.get("sub_binary100_referenced_size") == "8000",
            "ground-truth sub_binary100 constants mismatch")
    return values


def find_fixture_process(base, fixture_pid):
    resp = post_json(base, "/api/erlang-runtime", {"section": "process", "filter": fixture_pid, "limit": 10})
    matches = [item.get("detail") or {} for item in resp.get("items") or []
               if (item.get("detail") or {}).get("pid") == fixture_pid]
    require(len(matches) == 1, "expected exactly one fixture process, found %d" % len(matches))
    return matches[0].get("address")


def page_inventory(base, section, offset, limit):
    """One page of /api/erlang-runtime; fails closed if the query errors."""
    resp = post_json(base, "/api/erlang-runtime",
                     {"section": section, "offset": offset, "limit": limit, "sort": "size"})
    require(resp.get("success") is True, "erlang-runtime section=%s page %d failed: %s"
            % (section, offset, resp.get("error")))
    return resp


def find_8000_refc_unique(base):
    """The one 8000-byte shared Binary, asserted globally unique.

    The binary inventory is fully paginated to truncated==False (so every
    8000-byte candidate in the whole inventory is seen) and its envelope must
    report index/inventory complete before a global uniqueness claim is made.
    Zero or multiple candidates, an unfinished index, or truncated pagination
    all fail closed.
    """
    page_size = 256
    offset = 0
    candidates = []
    saw_index_complete = False
    while True:
        resp = page_inventory(base, "binary", offset, page_size)
        require(resp.get("inventory_complete") is True, "binary inventory is not complete")
        require(resp.get("index_complete") is True, "binary index is not complete")
        saw_index_complete = True
        for item in resp.get("items") or []:
            detail = item.get("detail") or {}
            if detail.get("payload_bytes") == 8000:
                candidates.append(item.get("address"))
        truncated = resp.get("truncated") is True
        if resp.get("returned", 0) == 0:
            break
        offset += page_size
        if not truncated:
            break
    require(saw_index_complete, "binary inventory never returned a complete envelope")
    require(not truncated, "binary inventory pagination did not terminate (truncated)")
    require(len(candidates) == 1,
            "expected exactly one 8000-byte shared Binary across the full inventory, found %d" % len(candidates))
    return candidates[0]


def extract_tuple_value_address(tuple_str, key):
    """Address of field1 of the exact tuple `{key, <term>, ...}`.

    The key must be the tuple's field0 (structural `startswith("{key,")`
    match); a substring match inside a different field or another key is never
    accepted. The field1 address is the first 0x token after the `,` that
    follows the exact key."""
    if not tuple_str.startswith("{" + key + ","):
        return None
    rest = tuple_str[len("{" + key + ","):]
    match = re.search(r"0x([0-9a-f]+)", rest)
    if not match:
        return None
    return "0x" + match.group(1)


def find_dict_value(base, fixture_addr, key):
    """Unified bounded BFS over every process-dictionary root owned by the
    fixture process.

    A bucket root targets either the entry tuple/2 or a cons chain; referents
    drive the traversal. A value is accepted only when its tuple's field0 is
    exactly `key` (structural `{key,` prefix). The roots page is fully
    paginated to truncated==False before the search is declared exhaustive.
    Missing/duplicate keys, unfinished pagination, repeated nodes, and budget
    exhaustion all fail closed."""
    found = []
    visited = set()
    node_budget = 2048
    page_size = 256
    offset = 0
    while True:
        resp = post_json(base, "/api/erlang-roots",
                         {"source": "process-dictionary", "limit": page_size, "offset": offset})
        require(resp.get("success") is True, "erlang-roots process-dictionary page %d failed" % offset)
        items = resp.get("items") or []
        for item in items:
            owner_addr = item.get("owner_address") or (item.get("owner") or {}).get("address")
            if owner_addr != fixture_addr:
                continue
            target = item.get("target_address")
            require(bool(target), "process-dictionary root for fixture missing target_address")
            queue = [target]
            while queue:
                raw = queue.pop(0)
                node_budget -= 1
                require(node_budget > 0, "process-dictionary BFS budget exhausted")
                node = int(raw, 16) & ~0x3
                if node in visited:
                    continue
                visited.add(node)
                o = obj_chain(base, "0x%x" % node, 2)
                obj = o.get("object") or {}
                typ = obj.get("type") or ""
                if typ.startswith("Erlang tuple"):
                    tstr = obj.get("string") or ""
                    if tstr.startswith("{" + key + ","):
                        value = extract_tuple_value_address(tstr, key)
                        require(bool(value), "dict tuple for %s has no value address" % key)
                        found.append(value)
                for r in (o.get("referents") or {}).get("items") or []:
                    if r.get("address"):
                        queue.append(r["address"])
        if resp.get("truncated") is not True:
            break
        if len(items) < page_size:
            break
        offset += page_size
    require(not resp.get("truncated"), "process-dictionary pagination did not terminate (truncated)")
    require(len(found) == 1, "process-dictionary key %s found %d times (must be exactly one)" % (key, len(found)))
    return found[0]


def verify_identity_contract(base):
    status = get_json(base, "/api/status")
    require(status.get("ready") is True, "session not ready")
    require(status.get("process_type") == "erlang", "process type is not erlang")

    overview = post_json(base, "/api/erlang-runtime", {"section": "overview"}).get("overview") or {}
    require(overview.get("otp_release") == "27" and overview.get("erts_version") == "15.2.7",
            "OTP/ERTS identity mismatch")
    require(overview.get("build_id") == EXPECTED_BUILD_ID, "Build ID mismatch")
    require(overview.get("flavor") == "elixir" and overview.get("flavor_version") == EXPECTED_ELIXIR
            and overview.get("flavor_status") == "verified", "Elixir flavor mismatch")
    require(overview.get("support_level") == "L4", "support level is not L4")
    require(overview.get("analysis_mode") == "global-term-graph", "analysis mode mismatch")
    require(overview.get("graph_status") == "complete" and overview.get("graph_precision") == "exact",
            "graph is not complete/exact")

    # Structured contract from the runtime inventory envelope.
    resp = post_json(base, "/api/erlang-runtime", {"section": "overview"})
    require(resp.get("graph_status") == "complete", "graph_status not complete")
    require(resp.get("inventory_complete") is True, "inventory_complete is False")
    require(resp.get("index_complete") is True, "index_complete is False")


def verify_result_json(data):
    """Strict v28 contract from the session's own maze-result.json.

    The subprocess writes this with --json-output into its --output-dir before
    the Local API becomes resident, so reading it here proves the same analysis
    that the live endpoints serve. Every *_status string must be complete
    (flavor_status=verified) and known_size must equal the authoritative BEAM
    allocator coverage."""
    runtime = data.get("erlang") or {}
    require(runtime.get("detected") is True, "BEAM runtime was not detected in maze-result.json")
    require(runtime.get("build_id") == EXPECTED_BUILD_ID, "unexpected Build ID in maze-result.json")
    require(runtime.get("flavor") == "elixir" and runtime.get("flavor_version") == EXPECTED_ELIXIR,
            "Elixir flavor mismatch in maze-result.json")
    require(runtime.get("term_unsupported_count", 0) == 0,
            "term_unsupported_count is not zero: %r" % runtime.get("term_unsupported_count"))
    require(runtime.get("graph_status") == "complete", "graph_status not complete")
    require(runtime.get("term_graph_status") == "complete", "term_graph_status not complete")
    require(runtime.get("term_graph_precision") == "exact", "term_graph_precision not exact")
    non_complete = []
    for key, value in runtime.items():
        if key.endswith("_status") and isinstance(value, str):
            if key == "flavor_status":
                continue
            if value != "complete":
                non_complete.append("%s=%r" % (key, value))
    require(not non_complete, "incomplete BEAM domain statuses: %s" % ", ".join(non_complete))
    require(runtime.get("flavor_status") == "verified", "flavor_status is not verified")
    known_size = data.get("known_size", 0)
    allocator_covered = runtime.get("allocator_native_covered_bytes", 0)
    require(known_size == allocator_covered,
            "known_size %r != allocator_native_covered_bytes %r" % (known_size, allocator_covered))


def call_eight_endpoints(base, refc, sub100):
    # runtime / search / aggregate / roots
    for path, payload in [
        ("/api/erlang-runtime", {"section": "overview"}),
        ("/api/erlang-search", {"filter": "maze", "scope": "atom", "limit": 5}),
        ("/api/erlang-aggregate", {"group_by": "type", "limit": 3}),
        ("/api/erlang-roots", {"limit": 3}),
    ]:
        resp = post_json(base, path, payload)
        require(resp.get("success") is True, "%s failed" % path)
    # object / root-path / reachable / dominator on the real chain
    for path, payload in [
        ("/api/erlang-object", {"address": sub100, "depth": 3, "string_bytes": 100}),
        ("/api/erlang-root-path", {"address": sub100, "max_paths": 3, "max_depth": 12}),
        ("/api/erlang-reachable", {"address": refc, "limit": 3}),
        ("/api/erlang-dominator", {"address": refc, "limit": 3}),
    ]:
        resp = post_json(base, path, payload)
        require(resp.get("success") is True, "%s failed" % path)
        require(resp.get("graph_status") == "complete", "%s graph not complete" % path)
    rp = post_json(base, "/api/erlang-root-path", {"address": sub100, "max_paths": 3, "max_depth": 12})
    require(rp.get("rooted") is True, "root path not rooted")
    require(rp.get("graph_status") == "complete" and rp.get("graph_precision") == "exact",
            "root path not complete/exact")


def call_console_commands(base, refc):
    exec_cmd(base, "text 500")
    exec_cmd(base, "p %s" % refc)
    exec_cmd(base, "ref %s" % refc)
    exec_cmd(base, "ref-dot %s" % refc)
    exec_cmd(base, "sizetree %s" % refc)
    exec_cmd(base, "erlang-search maze 5")
    exec_cmd(base, "erlang-runtime")
    exec_cmd(base, "erlang-aggregate type 3")
    exec_cmd(base, "erlang-object %s" % refc)
    exec_cmd(base, "erlang-root-path %s" % refc)


def verify_dual_chain(base, fixture_addr):
    small16 = find_dict_value(base, fixture_addr, "maze_small_slice16_live")
    sub100 = find_dict_value(base, fixture_addr, "maze_sub_binary100_live")

    so = obj_chain(base, small16, 3)
    sobj = so.get("object") or {}
    require(sobj.get("type") == "Erlang heap binary" and sobj.get("logical_bytes") == 16,
            "small_slice16 is not a 16-byte heap binary")
    require((so.get("referents") or {}).get("total_count", 0) == 0,
            "small_slice16 heap binary must have no referent chain to the 8000-byte refc")

    refc = find_8000_refc_unique(base)
    so2 = obj_chain(base, sub100, 3)
    sobj2 = so2.get("object") or {}
    require(sobj2.get("type") == "Erlang sub-binary" and sobj2.get("logical_bytes") == 100,
            "sub_binary100 is not a 100-byte sub-binary")
    binrefs = [(r.get("address"), r.get("type")) for r in (so2.get("referents") or {}).get("items") or []
               if r.get("type") == "Erlang binary reference"]
    require(len(binrefs) == 1, "sub_binary100 must have exactly one BinRef referent, found %d" % len(binrefs))
    br = obj_chain(base, binrefs[0][0], 2)
    targets = [r.get("address") for r in (br.get("referents") or {}).get("items") or []]
    require(len(targets) == 1 and targets[0] == refc,
            "sub_binary100 BinRef must have exactly one referent equal to the 8000 refc")
    return small16, sub100, refc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, help="core tar.gz to analyze")
    parser.add_argument("--ground-truth", required=True, help="fixture ground-truth.txt")
    parser.add_argument("--maze", default="./maze", help="maze executable")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    core = os.path.abspath(args.core)
    truth_path = os.path.abspath(args.ground_truth)
    require(os.path.isfile(core) and os.path.getsize(core) > 0, "core tar.gz missing or empty")
    require(os.path.isfile(truth_path) and os.path.getsize(truth_path) > 0, "ground-truth missing or empty")
    require(os.path.isfile(args.maze), "maze executable not found")
    ground_truth = load_ground_truth(truth_path)

    # One private session under the repository tmp tree. --output-dir and
    # --logdir are session-private; the cwd is the session so ref/sizetree
    # PNG/DOT artifacts land inside it. Only this directory is ever removed.
    # __file__ is <repo>/testdata/erlang/<fixture>/accept_local_api.py, so the
    # repository root is three `..` above the fixture directory.
    fixture_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(fixture_dir, "..", "..", ".."))
    session_parent = os.path.join(repo_root, "tmp", "elixir-fixture")
    os.makedirs(session_parent, exist_ok=True)
    session = tempfile.mkdtemp(prefix="accept-", dir=session_parent)
    results_dir = os.path.join(session, "results")
    work_dir = os.path.join(session, "work")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)
    log_path = os.path.join(session, "maze.log")
    result_json = os.path.join(results_dir, RESULTS_NAME)

    maze_abs = os.path.abspath(args.maze)
    log_handle = open(log_path, "w")
    proc = subprocess.Popen(
        [maze_abs, "--tar", core, "--local-api", "--json-output",
         "--output-dir", results_dir, "--logdir", work_dir, "--no-cpp"],
        stdout=log_handle, stderr=subprocess.STDOUT, cwd=session)
    base = None
    try:
        base = discover_base(log_path, args.timeout)
        print("Local API base: %s" % base)
        wait_ready(base, args.timeout)
        require(os.path.isfile(result_json),
                "maze subprocess did not write %s (missing --json-output result)" % RESULTS_NAME)
        with open(result_json) as source:
            result_data = json.load(source)
        verify_result_json(result_data)
        verify_identity_contract(base)
        fixture_pid = ground_truth["fixture_pid"].replace("#PID", "")
        fixture_addr = find_fixture_process(base, fixture_pid)
        small16, sub100, refc = verify_dual_chain(base, fixture_addr)
        call_eight_endpoints(base, refc, sub100)
        call_console_commands(base, refc)
        print("Local API acceptance PASSED (identity + v28 contract + dual-form sub-binary chain)")
        print("  fixture process = %s @ %s" % (fixture_pid, fixture_addr))
        print("  small_slice16 = %s (heap binary logical 16, no chain)" % small16)
        print("  sub_binary100 = %s -> single BinRef -> refc %s" % (sub100, refc))
        return 0
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        log_handle.close()
        # Remove ONLY this private session directory. Guard the path so a
        # programming error can never remove the repository root or a user
        # results directory.
        session_abs = os.path.abspath(session)
        parent_abs = os.path.abspath(session_parent)
        if session_abs != parent_abs and session_abs.startswith(parent_abs + os.sep):
            shutil.rmtree(session_abs)


if __name__ == "__main__":
    sys.exit(main())

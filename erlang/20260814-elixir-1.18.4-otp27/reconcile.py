#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Durable two-run (ASLR) reconciliation for the Elixir 1.18.4 fixture.

Compares two maze-result.json files captured from independent Elixir 1.18.4
processes (different PIDs, different ASLR) and asserts:

  * identical runtime identity (Build ID, embedded manifest/schema/producer);
  * identical Elixir flavor evidence and version;
  * every BEAM domain complete in both runs;
  * allocator coverage invariant (known_size == allocator_native_covered_bytes);
  * identical fixture topology / ground truth (process/atom/ETS counts,
    persistent-term count, shared-binary count);
  * different PIDs and non-overlapping ASLR address families for the stable
    samples (processes, module literal areas, shared binaries, heaps, roots).

Timing-sensitive totals (term node/edge counts) are NOT required to be equal.
"""
from __future__ import print_function

import json
import os
import sys


def load(path):
    with open(path) as source:
        return json.load(source)


def address_set(values):
    seen = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.startswith("0x"):
            seen.add(value)
        elif isinstance(value, int) and value > 0x100000:  # mapped addresses only
            seen.add(hex(value))
    return seen


def process_addresses(runtime):
    addresses = []
    for process in runtime.get("processes") or []:
        addresses.append(process.get("address"))
        heap = process.get("young_heap_region") or {}
        addresses.append(heap.get("begin"))
        addresses.append(heap.get("top"))
        stack = process.get("stack_region") or {}
        addresses.append(stack.get("begin"))
    return address_set(addresses)


def module_literal_addresses(runtime):
    addresses = []
    for area in runtime.get("module_literal_areas") or []:
        addresses.append(area.get("address"))
        addresses.append(area.get("start"))
        addresses.append(area.get("end"))
    return address_set(addresses)


def shared_binary_addresses(runtime):
    addresses = []
    for binary in runtime.get("shared_binaries") or []:
        addresses.append(binary.get("address"))
        addresses.append(binary.get("payload_address"))
    return address_set(addresses)


def root_addresses(runtime):
    return address_set((runtime.get("roots") or {}).values())


def complete_domains(runtime):
    domains = []
    for key, value in sorted(runtime.items()):
        if key.endswith("_status") and isinstance(value, str):
            if key == "flavor_status":  # identity status, not a BEAM domain
                continue
            domains.append((key, value))
    return domains


def load_ground_truth(path):
    values = {}
    if path and os.path.isfile(path):
        with open(path) as source:
            for raw in source:
                line = raw.strip()
                if "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip()
    return values


def reconcile(run1_path, run2_path, pid1, pid2, truth1_path="", truth2_path=""):
    data1, data2 = load(run1_path), load(run2_path)
    r1, r2 = data1.get("erlang") or {}, data2.get("erlang") or {}
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    # Identity invariants.
    require(r1.get("build_id") == r2.get("build_id") == "f94f08a81260ba544812ca2d62f479a794dc7c77",
            "Build ID must be identical and f94f08")
    require(r1.get("manifest_path") == r2.get("manifest_path"), "embedded manifest path differs")
    require(r1.get("manifest_path", "").startswith("embedded:otp-27.3.4.1"), "manifest not embedded")
    require((r1.get("layout") or {}).get("schema") == (r2.get("layout") or {}).get("schema") == "maze-erlang-layout-v28",
            "layout schema differs")
    require((r1.get("layout") or {}).get("producer") == (r2.get("layout") or {}).get("producer") == "maze-erlang-dwarf-v29",
            "layout producer differs")
    require(r1.get("otp_release") == r2.get("otp_release") == "27", "OTP release differs")
    require(r1.get("erts_version") == r2.get("erts_version") == "15.2.7", "ERTS version differs")
    require(r1.get("support_level") == r2.get("support_level") == "L4", "support level differs")
    require(r1.get("analysis_mode") == r2.get("analysis_mode") == "global-term-graph", "analysis mode differs")
    require(r1.get("graph_status") == r2.get("graph_status") == "complete", "graph status differs")
    require(r1.get("term_graph_status") == r2.get("term_graph_status") == "complete", "term graph status differs")
    require(r1.get("term_graph_precision") == r2.get("term_graph_precision") == "exact", "term graph precision differs")
    require(r1.get("term_unsupported_count", 0) == 0 and r2.get("term_unsupported_count", 0) == 0,
            "unsupported terms must be zero in both runs")

    # Elixir flavor evidence identical.
    require(r1.get("flavor") == r2.get("flavor") == "elixir", "Elixir flavor differs")
    require(r1.get("flavor_version") == r2.get("flavor_version") == "1.18.4", "Elixir version differs")
    require(r1.get("flavor_status") == r2.get("flavor_status") == "verified", "Elixir flavor status differs")
    require(sorted(r1.get("flavor_evidence") or []) == sorted(r2.get("flavor_evidence") or []),
            "Elixir flavor evidence differs")

    # Domain completeness identical (compare key sets before values so a missing
    # key in one run cannot be hidden by zip truncation).
    domains1 = dict(complete_domains(r1))
    domains2 = dict(complete_domains(r2))
    require(set(domains1) == set(domains2), "domain status key sets differ")
    for key in sorted(domains1):
        if domains1[key] != domains2[key]:
            errors.append("domain status %s differs: %r vs %r" % (key, domains1[key], domains2[key]))
    for key, value in domains1.items():
        if value != "complete":
            errors.append("domain %s not complete in run %s: %r" % (key, pid1, value))
    for key, value in domains2.items():
        if value != "complete":
            errors.append("domain %s not complete in run %s: %r" % (key, pid2, value))

    # Root scan / reachability completeness explicit.
    for field in ["term_root_scan_status", "term_reachability_status"]:
        require(r1.get(field) == r2.get(field), "%s differs between runs" % field)
        require(r1.get(field) == "complete", "%s not complete in run %s" % (field, pid1))

    # Allocator coverage invariant: within EACH run known_size must equal the
    # authoritative BEAM allocator coverage. Cross-run equality is NOT required
    # (atom/allocation timing varies between independent processes).
    require(data1.get("known_size") == r1.get("allocator_native_covered_bytes"), "run %s allocator coverage mismatch" % pid1)
    require(data2.get("known_size") == r2.get("allocator_native_covered_bytes"), "run %s allocator coverage mismatch" % pid2)

    # Fixture topology / ground truth identical.
    for field in ["process_count", "atom_count", "ets_table_count", "persistent_term_count",
                  "shared_binary_count", "module_literal_area_count", "timer_count", "port_count"]:
        require(r1.get(field) == r2.get(field), "%s differs between runs: %r vs %r" % (field, r1.get(field), r2.get(field)))

    # Ground-truth known objects present in both.
    def has_atom(runtime, name):
        return any(atom.get("name") == name for atom in runtime.get("atoms") or [])

    for name in ["MazeFixture", "MazeWorker", "MazeSupervisor", "maze_elixir_ready",
                 "elixir_maze_atom", "elixir_fixture_sentinel", "maze_ets"]:
        require(has_atom(r1, name) and has_atom(r2, name), "ground-truth atom %r missing in a run" % name)

    # Ground-truth binding: each core must match its own capture-time ground
    # truth file (process/atom counts and the worker mailbox/link facts).
    truth1, truth2 = load_ground_truth(truth1_path), load_ground_truth(truth2_path)
    require(bool(truth1) and bool(truth2), "both runs require a persisted ground-truth file")
    require(truth1.get("process_count") == truth2.get("process_count") == "60",
            "ground-truth process_count must be stable at 60")
    require(r1.get("process_count") == int(truth1["process_count"]),
            "run %s process_count does not match its ground truth" % pid1)
    require(r2.get("process_count") == int(truth2["process_count"]),
            "run %s process_count does not match its ground truth" % pid2)
    require(truth1.get("worker_mailbox_size") == truth2.get("worker_mailbox_size") == "3",
            "ground-truth worker mailbox must be stable")
    require(truth1.get("fixture_mailbox_size") == truth2.get("fixture_mailbox_size") == "2",
            "ground-truth fixture mailbox must be stable")
    # Atom counts: the frozen fixture is deterministic, so both runtimes must
    # carry the SAME runtime atom count, and each truth-to-runtime delta
    # (pre-READY snapshot vs captured core, stable measured 20) must be exactly
    # equal to the other and within [0, 64]. A differing count or delta means
    # the two captures are not the same deterministic process shape and the
    # reconciliation fails closed.
    r1_atoms, r2_atoms = r1.get("atom_count", 0), r2.get("atom_count", 0)
    t1_atoms, t2_atoms = int(truth1.get("atom_count", "0")), int(truth2.get("atom_count", "0"))
    require(r1_atoms == r2_atoms,
            "runtime atom counts must be identical across runs (%d vs %d)" % (r1_atoms, r2_atoms))
    delta1, delta2 = r1_atoms - t1_atoms, r2_atoms - t2_atoms
    require(delta1 == delta2,
            "truth-to-runtime atom deltas must be identical (%d vs %d)" % (delta1, delta2))
    require(0 <= delta1 <= 64,
            "run %s atom delta %d outside [0,64]" % (pid1, delta1))
    require(0 <= delta2 <= 64,
            "run %s atom delta %d outside [0,64]" % (pid2, delta2))

    # ASLR: different PIDs and non-overlapping stable address families.
    capture1, capture2 = data1.get("capture") or {}, data2.get("capture") or {}
    sourcePid1, sourcePid2 = str(capture1.get("source_pid")), str(capture2.get("source_pid"))
    require(sourcePid1 != "" and sourcePid1 != sourcePid2, "captured source PIDs must differ (got %r vs %r)" % (sourcePid1, sourcePid2))
    require(str(pid1) != str(pid2), "runs must come from different PIDs")
    require(sourcePid1 == str(pid1) and sourcePid2 == str(pid2), "capture source PID must match the CLI PID")
    for label, extract in [("process", process_addresses), ("module-literal", module_literal_addresses),
                           ("shared-binary", shared_binary_addresses), ("roots", root_addresses)]:
        set1, set2 = extract(r1), extract(r2)
        # The stable address families must be non-empty in BOTH runs (the
        # fixture really contains processes, module literal areas and shared
        # binaries) and must not overlap at all across the two ASLR runs.
        require(len(set1) > 0 and len(set2) > 0,
                "ASLR address family %s is empty in a run (run%s=%d run%s=%d)" %
                (label, pid1, len(set1), pid2, len(set2)))
        overlap = set1 & set2
        if overlap:
            errors.append("ASLR address family %s overlaps between runs (%d shared): %s" %
                          (label, len(overlap), sorted(overlap)[:3]))
        print("  address family %-14s run%s=%d run%s=%d overlap=%d" %
              (label, pid1, len(set1), pid2, len(set2), len(overlap)))

    if errors:
        print("RECONCILIATION FAILED (%d checks)" % len(errors))
        for error in errors[:40]:
            print("  - " + error)
        return 1

    print("RECONCILIATION PASSED: PIDs %s/%s, identity/manifest/flavor/domains/allocator/topology identical, "
          "ASLR address families disjoint" % (pid1, pid2))
    return 0


if __name__ == "__main__":
    import os
    args = sys.argv
    truth1 = args[5] if len(args) > 5 else ""
    truth2 = args[6] if len(args) > 6 else ""
    sys.exit(reconcile(args[1], args[2], args[3], args[4], truth1, truth2))

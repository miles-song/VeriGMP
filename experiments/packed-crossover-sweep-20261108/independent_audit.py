"""Independent archived-evidence audit; performs no timing or production writes."""
import argparse
import ast
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import statistics
import struct
import subprocess
import tempfile
import zipfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
TIP = "80447fdb090e6ea47e09ee487434bd5d7d13089e"
SOURCE = "83c4c52f52b40c8adac2cbda6ed4f0768d0f99a0"
MAIN = "8cc144b349269d31a59b18838aea28f52645a8fa"
PRECISIONS = (7, 17, 29, 30, 53)
DISCOVERY = list(range(1, 36)) + list(range(125, 132)) + list(range(509, 516))
CONFIRMATION = list(range(60, 70)) + list(range(253, 260)) + list(range(1019, 1025))
ALL_COUNTS = sorted(DISCOVERY + CONFIRMATION)
SHAPES = [(n, p) for p in PRECISIONS for n in ALL_COUNTS]
MASK = (1 << 64) - 1


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    if str(ROOT).startswith("/mnt/"):
        drive, rest = str(ROOT)[5:].split("/", 1)
        command = ["/mnt/c/Program Files/Git/cmd/git.exe", "-C", drive.upper() + ":/" + rest]
    else:
        command = ["git", "-C", str(ROOT)]
    return subprocess.check_output(command + list(args))


def csv_rows(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def inputs(n, p, index):
    state = (16438731 ^ n * 0x9E3779B97F4A7C15 ^ p * 0xD1B54A32D192ED03
             ^ index * 0x94D049BB133111EB) & MASK
    if state == 0:
        state = 1
    values = []
    for _ in range(2 * n):
        state = (state ^ (state << 13)) & MASK
        state ^= state >> 7
        state = (state ^ (state << 17)) & MASK
        values.append(state & ((1 << p) - 1))
    return values[:n], values[n:]


def gmean(values):
    return math.exp(statistics.mean(map(math.log, values)))


def metrics(rows, selected):
    ratios = [r["ratio"] if take else 1.0 for r, take in zip(rows, selected)]
    return dict(geometric_mean_ratio=gmean(ratios), minimum_ratio=min(ratios),
                maximum_ratio=max(ratios), median_ratio=statistics.median(ratios),
                regression_groups=sum(x > 1 for x in ratios),
                wins_over_1pct=sum(x < .99 for x in ratios),
                regressions_over_1pct=sum(x > 1.01 for x in ratios),
                regressions_over_5pct=sum(x > 1.05 for x in ratios),
                passes_no_regression=all(x <= 1 for x in ratios),
                passes_gain=gmean(ratios) <= .99)


def audit(output):
    evidence = PACKAGE / "evidence"
    receipt = json.loads((evidence / "receipt.json").read_bytes())
    result = dict(reviewed_commit=TIP, reviewed_tree=git("rev-parse", TIP + "^{tree}").decode().strip(),
                  main_commit=MAIN, measured_source=SOURCE, audit_script_sha256=digest(Path(__file__).read_bytes()),
                  status="running", archives=[], runs=[])
    for name, wanted in receipt["artifact_sha256"].items():
        assert digest((evidence / name).read_bytes()) == wanted, name
    for line in (evidence / "SHA256SUMS").read_text().splitlines():
        wanted, name = line.split(None, 1)
        assert digest((evidence / name.strip()).read_bytes()) == wanted, name
    for name, wanted in receipt["package_document_sha256"].items():
        assert digest((PACKAGE / name).read_bytes()) == wanted, name
    for name, wanted in receipt["source_file_sha256"].items():
        assert digest(git("show", SOURCE + ":" + name)) == wanted, name
    analysis_path = "experiments/packed-crossover-sweep-20261108/analyze.py"
    preregistered_analysis = git("show", SOURCE + ":" + analysis_path)
    final_analysis = (PACKAGE / "analyze.py").read_bytes()
    assert digest(final_analysis) == receipt["analysis_script_sha256"]
    old_functions = {node.name: ast.dump(node) for node in ast.parse(preregistered_analysis).body
                     if isinstance(node, ast.FunctionDef)}
    new_functions = {node.name: ast.dump(node) for node in ast.parse(final_analysis).body
                     if isinstance(node, ast.FunctionDef)}
    assert old_functions.keys() == new_functions.keys()
    assert [name for name in old_functions if old_functions[name] != new_functions[name]] == ["confirm"]
    for name in ("PROTOCOL.md", "crossover_bench.rs", "run_sweep.py"):
        assert (PACKAGE / name).read_bytes() == git("show", SOURCE + ":experiments/packed-crossover-sweep-20261108/" + name)
    result["analysis_identities"] = dict(preregistered_source_sha256=digest(preregistered_analysis),
                                         final_script_sha256=digest(final_analysis),
                                         unchanged_selection_functions=True,
                                         confirm_diff="Manually reviewed: metadata counts, self-hash and emulator caveat only")
    native = [name for name in git("ls-tree", "-r", "--name-only", TIP, "native").decode().splitlines()
              if name.endswith(".rs")]
    assert all(git("show", TIP + ":" + name) == git("show", MAIN + ":" + name) for name in native)
    assert all(name.startswith("experiments/packed-crossover-sweep-20261108/") for name in
               git("diff", "--name-only", MAIN + "..." + TIP).decode().splitlines())
    result["native_rust_files_identical_to_main"] = len(native)
    identities = git("log", "--format=%an <%ae>|%cn <%ce>", MAIN + ".." + TIP).decode().splitlines()
    assert identities and all(line == "miles-song <2324715854@qq.com>|miles-song <2324715854@qq.com>" for line in identities)
    result["branch_commit_author_and_committer_checks"] = len(identities)
    archives = {}
    for name, info in receipt["archives"].items():
        data = (evidence / name).read_bytes()
        assert len(data) == info["bytes"] and digest(data) == info["sha256"]
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert len(set(archive.namelist())) == len(archive.namelist())
            assert set(archive.namelist()) == set(info["inventory"])
            entries = {n: archive.read(n) for n in archive.namelist()}
        for entry, expected in info["inventory"].items():
            assert len(entries[entry]) == expected["bytes"] and digest(entries[entry]) == expected["sha256"]
        archives[name] = entries
        result["archives"].append(dict(name=name, entries=len(entries), sha256=digest(data)))
    gate = json.loads(archives["layout-gate.zip"]["verification.json"])
    assert digest(archives["layout-gate.zip"]["verification.json"]) == receipt["source_gate"]["report_sha256"]
    assert gate["source_git"]["head"] == SOURCE and gate["library_verified_items"] == 350
    for name, wanted in gate["source_git"]["source_sha256"].items():
        assert digest(git("show", SOURCE + ":" + name)) == wanted, name
        assert digest(archives["layout-gate.zip"]["source/" + name]) == wanted, name
    for command in gate["commands"]:
        for stream in ("stdout", "stderr"):
            assert digest(archives["layout-gate.zip"][command["name"] + "." + stream + ".log"]) == command[stream + "_sha256"]
    gate_entries = archives["layout-gate.zip"]
    classifier = {}
    exec(compile(gate_entries["source/experiments/packed-convolution/verus_logs.py"], "archived-verus-logs.py", "exec"), classifier)
    classifier["self_check"]()
    classified = []
    for command in gate["commands"]:
        name = command["name"]
        log = (gate_entries[name + ".stdout.log"] + gate_entries[name + ".stderr.log"]).decode()
        if name.startswith("mutant-"):
            assert classifier["strict_semantic_rejection"](log, command["returncode"], "packed_layout")
            classified.append(name)
        else:
            assert command["returncode"] == 0
        if name == "library-build":
            assert re.findall(r"verification results:: (\d+) verified, (\d+) errors", log) == [("350", "0")]
            assert "--no-cheating" in command["argv"] and "-O" in command["argv"]
    assert len(classified) == 3
    assert gate["runtime_oracle"]["cases"] == 208 and gate["runtime_oracle"]["error_cases"] == 18
    assert digest(gate_entries["packed-layout-runtime"]) == gate["runtime_oracle"]["executable_sha256"]
    assert digest(gate_entries["alias-negative.stderr.log"]) == gate["alias_negative"]["stderr_sha256"]
    assert b"error[E0502]" in gate_entries["alias-negative.stderr.log"]
    result["reused_gate"] = dict(verified_items=350, valid_cases=208, error_cases=18,
                                 semantic_rejections=classified, alias_error="E0502",
                                 policy="Identity and retained-log verification; no new proof execution claimed")
    all_groups, exact_groups = [], []
    oracle_records = oracle_coefficients = direct_coefficients = 0
    tools = None
    pids = []
    for run_name in ("discovery-a", "discovery-b", "confirmation-a", "confirmation-b"):
        entry = archives[run_name + ".zip"]
        meta = json.loads(entry["metadata.json"])
        pids.append(meta["runner_pid"])
        assert meta["run_id"] == run_name and meta["status"] == "pass"
        assert meta["measured_source_commit"] == SOURCE and meta["cpu_affinity"] == [0]
        assert digest(entry["packed-crossover-bench"]) == meta["harness_binary_sha256"]
        for name, wanted in meta["output_sha256"].items():
            assert digest(entry[name]) == wanted
        for suffix in ("metadata.json", "timings.csv", "summary.csv", "discarded.csv"):
            assert entry[suffix] == (evidence / (run_name + "-" + suffix)).read_bytes()
        assert meta["source_file_sha256"] == receipt["source_file_sha256"]
        assert digest(archives["layout-gate.zip"]["libverigmp.rlib"]) == meta["library_rlib_sha256"] == gate["library_sha256"]["rlib"]
        assert digest(archives["layout-gate.zip"]["verigmp.vir"]) == meta["library_metadata_sha256"] == gate["library_sha256"]["metadata"]
        assert meta["candidate_product_blobs"] == meta["mainline_product_blobs"]
        for name, blob in meta["candidate_product_blobs"].items():
            assert git("rev-parse", MAIN + ":" + name).decode().strip() == blob
        if tools is None:
            tools = meta["tool_file_sha256"]
            for name, wanted in tools.items():
                assert digest(Path(name).read_bytes()) == wanted, name
        else:
            assert tools == meta["tool_file_sha256"]
        selected_counts = DISCOVERY if meta["split"] == "discovery" else CONFIRMATION
        shape_ids = [i for i, (n, _) in enumerate(SHAPES) if n in selected_counts]
        rows = csv_rows(entry["timings.csv"])
        assert not entry["runner.stderr.log"]
        stdout = entry["runner.stdout.log"].decode().splitlines()
        sample_fields = ("shape", "phase", "mode", "repetition", "iterations", "total_ns")
        assert [line for line in stdout if line.startswith("SAMPLE,") and not line.startswith("SAMPLE,shape,")] == [
            "SAMPLE," + ",".join(row[key] for key in sample_fields) for row in rows]
        seen, grouped = set(), {}
        for row in rows:
            shape, rep = int(row["shape"]), int(row["repetition"])
            key = (shape, row["phase"], row["mode"], rep)
            assert key not in seen and shape in shape_ids and rep in range(7)
            assert row["phase"] in ("reuse", "streaming") and row["mode"] in ("layout", "bulk_zero")
            seen.add(key)
            n, p = SHAPES[shape]; q = 2 * p + (n - 1).bit_length(); slot = (q + 63) // 64
            assert (int(row["count"]), int(row["precision_bits"]), int(row["result_precision_bits"]), int(row["slot_words"]), int(row["guard_margin_bits"])) == (n, p, q, slot, 64 * slot - q)
            duration, iterations = int(row["total_ns"]), int(row["iterations"])
            assert duration >= 10_000_000 and iterations > 0
            value = Fraction(duration, iterations)
            assert float(value) == float(row["ns_per_call"])
            grouped.setdefault(key[:3], []).append(value)
        assert len(seen) == len(shape_ids) * 2 * 2 * 7 and all(len(x) == 7 for x in grouped.values())
        summary = csv_rows(entry["summary.csv"])
        assert len(summary) == len(shape_ids) * 2
        assert len({(r["shape"], r["phase"]) for r in summary}) == len(summary)
        for row in summary:
            shape, phase = int(row["shape"]), row["phase"]
            medians = {m: statistics.median(grouped[(shape, phase, m)]) for m in ("layout", "bulk_zero")}
            exact_ratio = float(medians["layout"] / medians["bulk_zero"])
            assert f"{exact_ratio:.8f}" == row["layout_over_bulk_zero"]
            for mode in medians:
                assert f"{float(medians[mode]):.3f}" == row[mode + "_median_ns"]
                assert f"{float(max(grouped[(shape, phase, mode)])):.3f}" == row[mode + "_p95_ns"]
            n, p = SHAPES[shape]; q = 2 * p + (n - 1).bit_length(); slot = (q + 63) // 64
            group = dict(run_id=run_name, split=meta["split"], shape=shape, phase=phase, count=n,
                         precision_bits=p, slot_words=slot, guard_margin_bits=64 * slot - q,
                         ratio=float(row["layout_over_bulk_zero"]))
            all_groups.append(group);exact_groups.append(dict(group, ratio=exact_ratio))
        discarded = csv_rows(entry["discarded.csv"])
        assert [line for line in stdout if line.startswith("SHORT,") and not line.startswith("SHORT,shape,")] == [
            "SHORT," + ",".join(row[key] for key in sample_fields) for row in discarded]
        for short in discarded:
            assert 0 < int(short["total_ns"]) < 10_000_000 and short["status"] == "below_10ms_retried"
            final = next(r for r in rows if all(r[k] == short[k] for k in ("shape", "phase", "mode", "repetition")))
            assert int(final["iterations"]) >= 2 * int(short["iterations"])
        result["runs"].append(dict(name=run_name, samples=len(rows), shape_phase_groups=len(summary),
                                   short_attempts=len(discarded), minimum_ns=min(int(x["total_ns"]) for x in rows)))
        if run_name.endswith("-b"):
            previous = archives[run_name[:-1] + "a.zip"]
            for name in ("results.bin", "inputs.csv", "oracle-checks.csv", "packed-crossover-bench"):
                assert entry[name] == previous[name], name
            continue
        stream = io.BytesIO(entry["results.bin"]);assert stream.read(8) == b"PCROSS01"
        checks = iter(csv_rows(entry["oracle-checks.csv"]))
        input_receipts = {int(x["shape"]): x for x in csv_rows(entry["inputs.csv"])}
        for shape in shape_ids:
            n, p = SHAPES[shape];q = 2 * p + (n - 1).bit_length();words = (q + 63) // 64
            assert n * ((1 << p) - 1) ** 2 < 1 << q <= 1 << 128
            ring_hash = hashlib.sha256()
            for index in range(32):
                left, right = inputs(n, p, index)
                ring_hash.update(struct.pack("<" + "Q" * (2 * n), *(left + right)))
                # Uniform 128-bit digits independently avoid every variable guard boundary.
                a = int.from_bytes(b"".join(x.to_bytes(16, "little") for x in left), "little")
                b = int.from_bytes(b"".join(x.to_bytes(16, "little") for x in right), "little")
                product = (a * b).to_bytes(32 * n, "little")
                expected = b"".join(product[16 * i:16 * i + 8 * words] for i in range(2 * n))
                assert int.from_bytes(product[-16:], "little") == 0
                # A second direct finite-sum check covers edge, middle and zero-tail coefficients.
                for degree in sorted({0, n - 1, n, 2 * n - 2, 2 * n - 1}):
                    direct = sum(left[i] * right[degree - i] for i in range(max(0, degree - n + 1), min(n, degree + 1)))
                    assert direct == int.from_bytes(product[16 * degree:16 * (degree + 1)], "little")
                    direct_coefficients += 1
                for mode, mode_name in enumerate(("layout", "bulk_zero")):
                    assert struct.unpack("<IIBQ", stream.read(17)) == (shape, index, mode, 2 * n * words)
                    payload = stream.read(len(expected));assert payload == expected
                    check = next(checks)
                    assert (int(check["shape"]), int(check["set_index"]), check["mode"]) == (shape, index, mode_name)
                    assert check["oracle_sha256"] == check["output_sha256"] == digest(payload)
                    assert check["every_coefficient_equal"] == check["cross_path_equal"] == "true"
                    oracle_records += 1;oracle_coefficients += 2 * n
            assert ring_hash.hexdigest() == input_receipts[shape]["input_sha256"]
        assert not stream.read(1) and next(checks, None) is None
    assert len(set(pids)) == 4
    discovery = [r for r in all_groups if r["split"] == "discovery"]
    raw_discovery = [r for r in exact_groups if r["split"] == "discovery"]
    rules = [("slot_words", "eq", 1), ("slot_words", "ge", 2)]
    rules += [("count", "le", x) for x in (16, 32, 64, 128, 256, 512)]
    rules += [("guard_margin_bits", "ge", x) for x in (4, 8, 12, 16, 20, 24, 32, 48, 56)]
    recorded_candidates = json.loads((evidence / "candidates.json").read_bytes())
    eligibility = []
    for i, (field, op, threshold, when) in enumerate((f, op, t, w) for f, op, t in rules for w in (True, False)):
        def take(row):
            v = row[field];return ({"eq": v == threshold, "ge": v >= threshold, "le": v <= threshold}[op]) == when
        selected = list(map(take, discovery));sides = [[r for r, hit in zip(discovery, selected) if hit == value] for value in (True, False)]
        coverage = all(len({r["count"] for r in side}) >= 3 and len({r["precision_bits"] for r in side}) >= 2 for side in sides)
        stats = metrics(discovery, selected);raw_stats = metrics(raw_discovery, selected)
        eligible = coverage and stats["passes_no_regression"] and stats["passes_gain"]
        old = recorded_candidates[i]
        assert old["index"] == i and old["rule"] == dict(field=field, operation=op, threshold=threshold, layout_when=when)
        assert old["eligible"] == eligible and old["distinct_branch_coverage"] == coverage
        assert (old["groups"], old["layout_selected_groups"], old["bulk_selected_groups"]) == (len(discovery), sum(selected), len(discovery) - sum(selected))
        for key, value in stats.items():
            assert math.isclose(old[key], value, rel_tol=1e-13, abs_tol=1e-13), (i, key)
        assert eligible == bool(coverage and raw_stats["passes_no_regression"] and raw_stats["passes_gain"])
        eligibility.append(dict(index=i, eligible=eligible, regressions=stats["regression_groups"], coverage=coverage))
    assert len(eligibility) == 34 and not any(x["eligible"] for x in eligibility)
    selection = json.loads((evidence / "selection.json").read_bytes())
    assert selection["selected_rule"] is None and selection["eligible_candidate_count"] == 0
    analysis = json.loads((evidence / "analysis.json").read_bytes())
    assert analysis["analysis_script_sha256"] == digest(final_analysis)
    assert analysis["source_file_sha256"] == receipt["source_file_sha256"]
    expected_group_map = {(r["run_id"], r["shape"], r["phase"]): r for r in all_groups}
    for filename, groups in (("all-groups.csv", all_groups),
                             ("largest-layout-regressions.csv", sorted(all_groups, key=lambda r: r["ratio"], reverse=True)[:25])):
        stored = csv_rows((evidence / filename).read_bytes())
        assert len(stored) == len(groups)
        assert [(r["run_id"], int(r["shape"]), r["phase"]) for r in stored] == [(r["run_id"], r["shape"], r["phase"]) for r in groups]
        for row in stored:
            group = expected_group_map[(row["run_id"], int(row["shape"]), row["phase"])]
            assert float(row["layout_over_bulk_zero"]) == group["ratio"]
    bands = [(1, 16), (17, 35), (60, 69), (125, 131), (253, 259), (509, 515), (1019, 1024)]
    margins = [(0, 0), (1, 7), (8, 15), (16, 31), (32, 47), (48, 63)]
    strata = csv_rows((evidence / "strata.csv").read_bytes())
    assert len(strata) == 22
    for row in strata:
        axis, value = row["axis"], row["value"]
        if axis in ("count_band", "guard_margin_bits_bin"):
            low, high = (int(x) for x in (value.split("-") if "-" in value else [value, value]))
            assert (low, high) in (bands if axis == "count_band" else margins)
            field = "count" if axis == "count_band" else "guard_margin_bits"
            group = [r for r in all_groups if low <= r[field] <= high]
        else:
            assert axis in ("precision_bits", "slot_words", "phase")
            group = [r for r in all_groups if str(r[axis]) == value]
        assert int(row["groups"]) == int(row["layout_selected_groups"]) == len(group)
        assert int(row["bulk_selected_groups"]) == 0 and row["distinct_branch_coverage"] == "True"
        for key, value in metrics(group, [True] * len(group)).items():
            if isinstance(value, bool):
                assert row[key] == str(value)
            else:
                assert math.isclose(float(row[key]), value, rel_tol=1e-13, abs_tol=1e-13), (axis, key)
    bulk = metrics([dict(r, ratio=1 / r["ratio"]) for r in all_groups], [True] * len(all_groups))
    for key, value in analysis["universal_bulk_zero"].items():
        assert math.isclose(value, len(all_groups) if key == "groups" else bulk[key], rel_tol=1e-13, abs_tol=1e-13)
    universal = metrics(all_groups, [True] * len(all_groups))
    for key, value in universal.items():
        assert math.isclose(analysis["universal_layout"][key], value, rel_tol=1e-13, abs_tol=1e-13)
    signs = 0
    for shape in range(len(SHAPES)):
        for phase in ("reuse", "streaming"):
            pair = [r for r in all_groups if r["shape"] == shape and r["phase"] == phase];assert len(pair) == 2
            signs += (pair[0]["ratio"] < 1) != (pair[1]["ratio"] < 1)
    assert signs == analysis["independent_winner_changes"]
    sign_rows = csv_rows((evidence / "independent-signs.csv").read_bytes())
    assert len(sign_rows) == 720
    for row in sign_rows:
        pair = [r for r in all_groups if r["shape"] == int(row["shape"]) and r["phase"] == row["phase"]]
        assert float(row["run_a_ratio"]) == pair[0]["ratio"] and float(row["run_b_ratio"]) == pair[1]["ratio"]
        assert row["winner_changed"] == str((pair[0]["ratio"] < 1) != (pair[1]["ratio"] < 1))
    assert analysis["selected_rule"] is None and analysis["candidate_confirmation"] is None
    assert not analysis["candidate_accepted_as_experiment"] and analysis["conclusion"] == "no_robust_policy_established"
    assert digest((evidence / "selection.json").read_bytes()) == receipt["frozen_selection_sha256"] == analysis["selection_receipt_sha256"]
    # Rebuild the harness, without executing it, against the hash-checked gate library.
    # Original compiler paths are deliberate: Rust panic locations can bind source paths.
    build_meta = json.loads(archives["discovery-a.zip"]["metadata.json"])
    command = build_meta["compiler_command"].copy()
    deps = Path(command[0]).parents[2]
    env = dict(os.environ, CARGO_HOME=str(deps / "cargo"), RUSTUP_HOME=str(deps / "rustup"),
               RUSTUP_TOOLCHAIN=build_meta["toolchain_pin"]["rust_toolchain"])
    env["PATH"] = str(deps / "cargo/bin") + os.pathsep + env.get("PATH", "")
    linked_library = Path(next(arg for arg in command if arg.startswith("verigmp=")).split("=", 1)[1])
    assert digest(linked_library.read_bytes()) == build_meta["library_rlib_sha256"]
    with tempfile.TemporaryDirectory(prefix="verigmp-independent-harness-") as temporary:
        binary = Path(temporary) / "packed-crossover-bench"
        command[-1] = str(binary)
        build = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=300)
        assert build.returncode == 0, build.stderr.decode()
        rebuilt_sha = digest(binary.read_bytes())
        assert rebuilt_sha == build_meta["harness_binary_sha256"]
        result["independent_release_rebuild"] = dict(sha256=rebuilt_sha, executed=False,
                                                    stdout_sha256=digest(build.stdout), stderr_sha256=digest(build.stderr))
    result.update(status="pass", accepted_samples=sum(x["samples"] for x in result["runs"]),
                  independent_tool_identities=len(tools), gate_source_identities=len(gate["source_git"]["source_sha256"]),
                  oracle_records=oracle_records, oracle_coefficients=oracle_coefficients,
                  additional_direct_sum_coefficients=direct_coefficients, candidate_eligibility=eligibility,
                  strata_verified=len(strata), universal_bulk_zero=analysis["universal_bulk_zero"],
                  universal_layout=universal, unrounded_raw_universal=metrics(exact_groups, [True] * len(exact_groups)),
                  independent_winner_changes=signs, selected_rule=None,
                  oracle_method="Independent Python integer multiplication using fixed 128-bit digits for every result coefficient, plus independently evaluated direct finite sums at edge/middle/tail positions for every input pair; no benchmark timings rerun.")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("candidate_eligibility", "archives")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise RuntimeError("Choose a new output path; existing evidence is immutable")
    audit(arguments.output)

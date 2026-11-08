#!/usr/bin/env python3
"""Select a preregistered predicate on discovery data and audit confirmation."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "fe9081f1a1d4075f74a46cdd66d97145d065c5ad"
EXPERIMENT = "experiments/packed-crossover-sweep-20261108"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gmean(values):
    return math.exp(statistics.mean(math.log(value) for value in values))


def write_json(path, content):
    Path(path).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_run(path, expected_split):
    path = Path(path).resolve()
    meta_path = path / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta["status"] != "pass" or meta["split"] != expected_split:
        raise RuntimeError("Expected a passing run for split " + expected_split)
    if meta["base_commit"] != BASE_COMMIT:
        raise RuntimeError("Run is bound to a different reviewed package base")
    for name, expected_sha in meta["output_sha256"].items():
        if sha(path / name) != expected_sha:
            raise RuntimeError("Run artifact hash mismatch: " + name)
    with (path / "summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for name in ("shape", "count", "precision_bits", "result_precision_bits", "slot_words",
                     "required_guard_bits", "guard_margin_bits"):
            row[name] = int(row[name])
        for name in ("layout_median_ns", "bulk_zero_median_ns", "layout_over_bulk_zero",
                     "layout_p95_ns", "bulk_zero_p95_ns"):
            row[name] = float(row[name])
        row["run_id"] = meta["run_id"]
        row["split"] = expected_split
    if len(rows) != 2 * meta["split_shape_count"]:
        raise RuntimeError("Incomplete per-group summary")
    receipt = dict(run_id=meta["run_id"], split=expected_split, metadata_sha256=sha(meta_path),
                   timings_sha256=sha(path / "timings.csv"), summary_sha256=sha(path / "summary.csv"),
                   result_dump_sha256=meta["result_dump_sha256"],
                   harness_binary_sha256=meta["harness_binary_sha256"],
                   oracle_checks_sha256=meta["oracle_checks_sha256"],
                   inputs_csv_sha256=meta["inputs_csv_sha256"], run_directory=str(path))
    return rows, meta, receipt


def load_pair(paths, split):
    a, meta_a, receipt_a = load_run(paths[0], split)
    b, meta_b, receipt_b = load_run(paths[1], split)
    for name in ("harness_binary_sha256", "library_rlib_sha256", "measured_source_commit",
                 "source_file_sha256", "cpu_model", "cpu_affinity", "verus_version", "rustc_version",
                 "result_dump_sha256", "inputs_csv_sha256", "oracle_checks_sha256", "tool_file_sha256"):
        if meta_a[name] != meta_b[name]:
            raise RuntimeError("Independent run identity mismatch: " + name)
    return a + b, [meta_a, meta_b], [receipt_a, receipt_b]


def predicates():
    rules = [
        dict(field="slot_words", operation="eq", threshold=1),
        dict(field="slot_words", operation="ge", threshold=2),
    ]
    rules.extend(dict(field="count", operation="le", threshold=threshold)
                 for threshold in (16, 32, 64, 128, 256, 512))
    rules.extend(dict(field="guard_margin_bits", operation="ge", threshold=threshold)
                 for threshold in (4, 8, 12, 16, 20, 24, 32, 48, 56))
    return [dict(**rule, layout_when=value) for rule in rules for value in (True, False)]


def test_predicate(row, rule):
    value = row[rule["field"]]
    threshold = rule["threshold"]
    if rule["operation"] == "eq":
        result = value == threshold
    elif rule["operation"] == "ge":
        result = value >= threshold
    elif rule["operation"] == "le":
        result = value <= threshold
    else:
        raise RuntimeError("Unregistered predicate operation")
    return result == rule["layout_when"]


def evaluate(rows, rule=None):
    ratios = [
        row["layout_over_bulk_zero"] if rule is None or test_predicate(row, rule) else 1.0
        for row in rows
    ]
    selected = [row for row in rows if rule is None or test_predicate(row, rule)]
    other = [row for row in rows if rule is not None and not test_predicate(row, rule)]
    counts_ok = rule is None or all(len({row["count"] for row in side}) >= 3 for side in (selected, other))
    precisions_ok = rule is None or all(len({row["precision_bits"] for row in side}) >= 2 for side in (selected, other))
    return dict(groups=len(rows), layout_selected_groups=len(selected),
                bulk_selected_groups=len(other), distinct_branch_coverage=counts_ok and precisions_ok,
                geometric_mean_ratio=gmean(ratios), minimum_ratio=min(ratios),
                maximum_ratio=max(ratios), median_ratio=statistics.median(ratios),
                regression_groups=sum(ratio > 1.0 for ratio in ratios),
                wins_over_1pct=sum(ratio < 0.99 for ratio in ratios),
                regressions_over_1pct=sum(ratio > 1.01 for ratio in ratios),
                regressions_over_5pct=sum(ratio > 1.05 for ratio in ratios),
                passes_no_regression=all(ratio <= 1.0 for ratio in ratios),
                passes_gain=gmean(ratios) <= 0.99)


def selection(train_rows, receipts, metas, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    candidates = []
    for index, rule in enumerate(predicates()):
        stats = evaluate(train_rows, rule)
        eligible = stats["distinct_branch_coverage"] and stats["passes_no_regression"] and stats["passes_gain"]
        candidates.append(dict(index=index, rule=rule, eligible=eligible, **stats))
    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    winner = min(eligible, key=lambda candidate: (candidate["geometric_mean_ratio"], candidate["index"])) if eligible else None
    receipt = dict(status="selection_frozen", reviewed_base_commit=BASE_COMMIT,
                   measured_source_commit=metas[0]["measured_source_commit"],
                   protocol_sha256=sha(ROOT / EXPERIMENT / "PROTOCOL.md"),
                   source_file_sha256=metas[0]["source_file_sha256"],
                   discovery_runs=receipts, candidate_count=len(candidates),
                   eligible_candidate_count=len(eligible),
                   selected_rule=winner["rule"] if winner else None,
                   discovery_result=winner if winner else None,
                   conclusion="candidate_requires_held_out_confirmation" if winner else "no_discovery_candidate",
                   no_confirmation_timings_read=True)
    write_json(output / "selection.json", receipt)
    write_json(output / "candidates.json", candidates)
    write_csv(output / "discovery-groups.csv", train_rows)
    print(json.dumps(receipt, indent=2))


def margin_bin(row):
    margin = row["guard_margin_bits"]
    if margin == 0:
        return "0"
    if margin <= 7:
        return "1-7"
    if margin <= 15:
        return "8-15"
    if margin <= 31:
        return "16-31"
    if margin <= 47:
        return "32-47"
    return "48-63"


def count_band(row):
    n = row["count"]
    if n <= 16:
        return "1-16"
    if n <= 35:
        return "17-35"
    if n <= 69:
        return "60-69"
    if n <= 131:
        return "125-131"
    if n <= 259:
        return "253-259"
    if n <= 515:
        return "509-515"
    return "1019-1024"


def strata(rows):
    axes = (
        ("precision_bits", lambda row: str(row["precision_bits"])),
        ("count_band", count_band),
        ("slot_words", lambda row: str(row["slot_words"])),
        ("guard_margin_bits_bin", margin_bin),
        ("phase", lambda row: row["phase"]),
    )
    result = []
    for axis, key_function in axes:
        groups = {}
        for row in rows:
            groups.setdefault(key_function(row), []).append(row)
        for value, group in sorted(groups.items()):
            stats = evaluate(group)
            result.append(dict(axis=axis, value=value, **stats))
    return result


def confirm(train_rows, train_meta, train_receipts, confirm_rows, confirm_meta, confirm_receipts, selection_path, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    selection_path = Path(selection_path).resolve()
    receipt = json.loads(selection_path.read_text(encoding="utf-8"))
    if receipt["status"] != "selection_frozen" or receipt["discovery_runs"] != train_receipts:
        raise RuntimeError("Selection receipt is not bound to the supplied discovery runs")
    rule = receipt["selected_rule"]
    all_rows = train_rows + confirm_rows
    for key in ("harness_binary_sha256", "library_rlib_sha256", "measured_source_commit",
                "source_file_sha256", "cpu_model", "cpu_affinity"):
        if train_meta[0][key] != confirm_meta[0][key]:
            raise RuntimeError("Source/tool identity changed between discovery and confirmation: " + key)
    universal_layout = evaluate(all_rows)
    bulk_ratios = [1 / row["layout_over_bulk_zero"] for row in all_rows]
    universal_bulk = dict(groups=len(all_rows), geometric_mean_ratio=gmean(bulk_ratios),
                          maximum_ratio=max(bulk_ratios), regression_groups=sum(ratio > 1 for ratio in bulk_ratios),
                          passes_no_regression=all(ratio <= 1 for ratio in bulk_ratios),
                          passes_gain=gmean(bulk_ratios) <= 0.99)
    candidate_confirmation = evaluate(confirm_rows, rule) if rule else None
    accepted = bool(rule and candidate_confirmation["passes_no_regression"] and candidate_confirmation["passes_gain"])
    final = dict(
        status="pass_experiment_archive", reviewed_base_commit=BASE_COMMIT,
        measured_source_commit=train_meta[0]["measured_source_commit"],
        measured_source_tree=train_meta[0]["measured_source_tree"],
        source_file_sha256=train_meta[0]["source_file_sha256"],
        analysis_script_sha256=sha(Path(__file__)),
        protocol_sha256=sha(ROOT / EXPERIMENT / "PROTOCOL.md"),
        selection_receipt_sha256=sha(selection_path),
        discovery_runs=train_receipts, confirmation_runs=confirm_receipts,
        registered_shapes=360, registered_shape_phase_groups=720,
        independent_replicates=2,
        per_process_shape_phase_groups={
            meta["run_id"]: 2 * meta["split_shape_count"] for meta in train_meta + confirm_meta
        },
        total_raw_samples=sum(meta["split_shape_count"] * 2 * 2 * 7 for meta in train_meta + confirm_meta),
        all_batches_at_least_10ms=True,
        independent_release_binary_sha256=train_meta[0]["harness_binary_sha256"],
        universal_layout=universal_layout, universal_bulk_zero=universal_bulk,
        selected_rule=rule, candidate_confirmation=candidate_confirmation,
        candidate_accepted_as_experiment=accepted,
        conclusion="hybrid_experiment_candidate_confirmed" if accepted else "no_robust_policy_established",
        production_dispatch_enabled=False, production_sources_changed=False,
        formal_composition_claim=False, gmp_parity_claim=False,
        ready_for_independent_measurement_review=True,
        caveats=[
            "Single WSL2 x86_64 machine, CPU 0, pinned Verus/Rust and mainline product implementation.",
            "The emulator was observed stopped before controlled runs and running after timing; continuous suspension was not monitored, so timing is not guaranteed emulator-free.",
            "Registered p <= 53 one-limb coefficients and n <= 1024 do not establish a policy for arbitrary precision or sizes.",
            "Cache eviction is outside batches; streaming is a rotating 32-input condition, not per-call DRAM coldness.",
            "Seven medians and the strict registered no-regression rule are an experimental screen, not a statistical or worst-case guarantee.",
            "Pack cost is measured inside the exact Toom/extract composition and can be small relative to total consumer time.",
            "No production dispatch, new functional refinement proof, or GMP comparison is part of this experiment.",
        ],
    )
    write_csv(output / "all-groups.csv", all_rows)
    write_csv(output / "strata.csv", strata(all_rows))
    worst = sorted(all_rows, key=lambda row: row["layout_over_bulk_zero"], reverse=True)[:25]
    write_csv(output / "largest-layout-regressions.csv", worst)
    instability = []
    for split, paths_rows in (("discovery", train_rows), ("confirmation", confirm_rows)):
        grouped = {}
        for row in paths_rows:
            grouped.setdefault((row["shape"], row["phase"]), []).append(row)
        for (shape_id, phase), pair in grouped.items():
            if len(pair) != 2:
                raise RuntimeError("Independent pair has missing shape/phase group")
            ratios = [row["layout_over_bulk_zero"] for row in pair]
            instability.append(dict(split=split, shape=shape_id, count=pair[0]["count"],
                                    precision_bits=pair[0]["precision_bits"], phase=phase,
                                    run_a_ratio=ratios[0], run_b_ratio=ratios[1],
                                    winner_changed=(ratios[0] < 1) != (ratios[1] < 1)))
    write_csv(output / "independent-signs.csv", instability)
    final["independent_winner_changes"] = sum(row["winner_changed"] for row in instability)
    final["output_sha256"] = {name: sha(output / name) for name in
                             ("all-groups.csv", "strata.csv", "largest-layout-regressions.csv", "independent-signs.csv")}
    write_json(output / "analysis.json", final)
    print(json.dumps(final, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, nargs=2, required=True)
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--confirmation", type=Path, nargs=2)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    train_rows, train_meta, train_receipts = load_pair(args.train, "discovery")
    if args.select:
        if args.confirmation or args.selection:
            raise RuntimeError("Selection cannot read confirmation data")
        selection(train_rows, train_receipts, train_meta, args.output)
    else:
        if not args.confirmation or not args.selection:
            raise RuntimeError("Final analysis requires confirmation runs and a frozen selection")
        confirm_rows, confirm_meta, confirm_receipts = load_pair(args.confirmation, "confirmation")
        confirm(train_rows, train_meta, train_receipts, confirm_rows, confirm_meta, confirm_receipts,
                args.selection, args.output)


if __name__ == "__main__":
    main()

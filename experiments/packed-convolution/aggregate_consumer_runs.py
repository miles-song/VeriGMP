#!/usr/bin/env python3
"""Audit two independent consumer runs and write a confirmation dataset."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

MODES = ("layout", "bulk_zero", "direct")
PHASES = ("reuse", "streaming")
MIN_BATCH_NS = 10_000_000
REPS = 7


def sha_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-one", type=Path, required=True)
    parser.add_argument("--run-two", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    first, second, output = (path.resolve() for path in (args.run_one, args.run_two, args.output_dir))
    if first == second or not first.is_dir() or not second.is_dir() or not output.is_dir():
        raise RuntimeError("Both run directories and the existing output directory are required")
    metadata = [json.loads((root / "metadata.json").read_text(encoding="utf-8"))
                for root in (first, second)]
    if any(item.get("status") != "pass" for item in metadata):
        raise RuntimeError("An input run did not pass")
    comparable = ("measured_source_commit", "measured_source_tree", "source_sha256",
                  "library_source_commit", "library_rlib_sha256", "library_metadata_sha256",
                  "packed_layout_source_sha256", "rustc", "verus", "cpu_model", "cpu_affinity")
    if any(metadata[0][key] != metadata[1][key] for key in comparable):
        raise RuntimeError("The independent runs differ in source, tools or CPU identity")
    if metadata[0]["run_id"] == metadata[1]["run_id"] or metadata[0]["run_pid"] == metadata[1]["run_pid"]:
        raise RuntimeError("Run identifiers/processes are not independent")
    if metadata[0]["harness_binary_sha256"] != metadata[1]["harness_binary_sha256"]:
        raise RuntimeError("Release harness rebuilds are not byte-identical")

    input_receipts = [json.loads((root / "inputs.json").read_text(encoding="utf-8"))
                      for root in (first, second)]
    result_receipts = [json.loads((root / "results.json").read_text(encoding="utf-8"))
                       for root in (first, second)]
    if input_receipts[0] != input_receipts[1] or result_receipts[0] != result_receipts[1]:
        raise RuntimeError("Independent runs do not share identical inputs and oracle outputs")

    raw = [read_csv(root / "timings.csv") for root in (first, second)]
    discarded = [read_csv(root / "discarded.csv") for root in (first, second)]
    summaries = [read_csv(root / "summary.csv") for root in (first, second)]
    expected_groups = len(summaries[0])
    if expected_groups == 0 or len(summaries[1]) != expected_groups:
        raise RuntimeError("A run has incomplete summary groups")
    for run_rows in raw:
        if len(run_rows) != expected_groups * len(MODES) * REPS:
            raise RuntimeError("A run has incomplete raw repetitions")
        if any(int(row["total_ns"]) < MIN_BATCH_NS for row in run_rows):
            raise RuntimeError("A recorded sample is shorter than the 10 ms protocol floor")
    for attempts in discarded:
        if any(int(row["total_ns"]) >= MIN_BATCH_NS or row["status"] != "below_10ms_retried"
               for row in attempts):
            raise RuntimeError("A discarded short timing attempt has an invalid reason")

    indexed = []
    for run_rows in summaries:
        indexed.append({(int(row["shape"]), row["phase"]): row for row in run_rows})
    raw_indexed = []
    for rows in raw:
        grouped = {}
        for row in rows:
            grouped.setdefault((int(row["shape"]), row["phase"], row["mode"]), []).append(
                float(row["ns_per_call"]))
        if any(len(values) != REPS for values in grouped.values()):
            raise RuntimeError("A timing group does not have exactly seven raw repetitions")
        raw_indexed.append(grouped)

    combined = []
    for key, first_summary in indexed[0].items():
        second_summary = indexed[1].get(key)
        if second_summary is None:
            raise RuntimeError("A workload/phase is missing from the confirmation run")
        row = dict(shape=key[0], phase=key[1], count=first_summary["count"],
                   precision_bits=first_summary["precision_bits"],
                   result_precision_bits=first_summary["result_precision_bits"],
                   slot_words=first_summary["slot_words"])
        run_medians = []
        for run_index, summary in enumerate((first_summary, second_summary)):
            mode_medians = {}
            for mode in MODES:
                values = raw_indexed[run_index][(key[0], key[1], mode)]
                median = statistics.median(values)
                mode_medians[mode] = median
                row[f"run{run_index + 1}_{mode}_median_ns"] = f"{median:.3f}"
                row[f"run{run_index + 1}_{mode}_p95_ns"] = f"{float(summary[f'{mode}_p95_ns']):.3f}"
            row[f"run{run_index + 1}_layout_over_bulk_zero"] = f"{mode_medians['layout'] / mode_medians['bulk_zero']:.6f}"
            row[f"run{run_index + 1}_layout_over_direct"] = f"{mode_medians['layout'] / mode_medians['direct']:.6f}"
            run_medians.append(mode_medians)
        for mode in MODES:
            row[f"run2_over_run1_{mode}"] = f"{run_medians[1][mode] / run_medians[0][mode]:.6f}"
            all_samples = raw_indexed[0][(key[0], key[1], mode)] + raw_indexed[1][(key[0], key[1], mode)]
            row[f"combined_{mode}_median_ns"] = f"{statistics.median(all_samples):.3f}"
        row["combined_layout_over_bulk_zero"] = f"{float(row['combined_layout_median_ns']) / float(row['combined_bulk_zero_median_ns']):.6f}"
        row["combined_layout_over_direct"] = f"{float(row['combined_layout_median_ns']) / float(row['combined_direct_median_ns']):.6f}"
        combined.append(row)

    with (output / "confirmation.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(combined[0]))
        writer.writeheader()
        writer.writerows(combined)
    receipt = dict(
        status="pass",
        run_ids=[item["run_id"] for item in metadata],
        run_pids=[item["run_pid"] for item in metadata],
        measured_source_commit=metadata[0]["measured_source_commit"],
        measured_source_tree=metadata[0]["measured_source_tree"],
        source_sha256=metadata[0]["source_sha256"],
        library_rlib_sha256=metadata[0]["library_rlib_sha256"],
        harness_binary_sha256=metadata[0]["harness_binary_sha256"],
        cpu_model=metadata[0]["cpu_model"],
        cpu_affinity=metadata[0]["cpu_affinity"],
        workload_phase_groups=len(combined),
        repetitions_per_mode_per_run=REPS,
        raw_samples_per_run=len(raw[0]),
        short_attempts_per_run=[len(discarded[0]), len(discarded[1])],
        discarded_attempts_sha256=[sha_file(first / "discarded.csv"), sha_file(second / "discarded.csv")],
        all_batches_at_least_10ms=True,
        all_coefficients_independently_oracle_checked=True,
        inputs_identical=True,
        outputs_identical=True,
        run_metadata_sha256=[sha_file(first / "metadata.json"), sha_file(second / "metadata.json")],
        run_timings_sha256=[sha_file(first / "timings.csv"), sha_file(second / "timings.csv")],
        run_stdout_sha256=[sha_file(first / "runner.stdout.log"), sha_file(second / "runner.stdout.log")],
        confirmation_csv_sha256=sha_file(output / "confirmation.csv"),
    )
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status="pass", run_ids=receipt["run_ids"],
                          workload_phase_groups=len(combined), raw_samples_per_run=len(raw[0])), indent=2))


if __name__ == "__main__":
    main()

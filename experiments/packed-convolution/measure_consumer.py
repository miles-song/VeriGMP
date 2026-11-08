#!/usr/bin/env python3
"""Build and independently oracle-check one pinned packed-consumer run."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
SEED = 16_438_731
MAINLINE_BASELINE = "8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa"
STREAM_SETS = 32
REPS = 7
MIN_BATCH_NS = 10_000_000
SHAPES = [
    (0, 7), (1, 7), (1, 53), (2, 17), (7, 29), (63, 29), (64, 29),
    (64, 30), (65, 30), (257, 17), (1024, 7), (1024, 17), (1024, 29),
    (1024, 53),
]
MODES = ("layout", "bulk_zero", "direct")
PHASES = ("reuse", "streaming")
PRODUCT_SOURCES = (
    "native/verified/toom_multiply.rs",
    "native/verified/toom_words.rs",
    "native/verified/toom_evaluate.rs",
    "native/verified/toom_interpolate.rs",
    "native/verified/fast_multiply.rs",
    "native/verified/fast_words.rs",
    "native/verified/multiply.rs",
    "native/verified/kernel.rs",
    "native/specs/toom.rs",
    "native/specs/toom_blocks.rs",
    "native/specs/radix.rs",
    "native/specs/product.rs",
    "native/specs/fast_product.rs",
)
MASK64 = (1 << 64) - 1


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git_adapter():
    pointer = (ROOT / ".git").read_text(encoding="utf-8") if (ROOT / ".git").is_file() else ""
    match = re.fullmatch(r"gitdir: ([A-Za-z]):[/\\](.+)\s*", pointer.strip())
    if platform.system() == "Linux" and match:
        windows_git = Path("/mnt/c/Program Files/Git/cmd/git.exe")
        mounted_root = re.fullmatch(r"/mnt/([a-z])/(.+)", str(ROOT))
        if windows_git.is_file() and mounted_root:
            return [str(windows_git), "-C", mounted_root[1].upper() + ":/" + mounted_root[2]]
        gitdir = Path("/mnt") / match[1].lower() / match[2].replace("\\", "/")
        return ["git", f"--git-dir={gitdir}", f"--work-tree={ROOT}"]
    return ["git", "-C", str(ROOT)]


def git(*args):
    return subprocess.run(git_adapter() + list(args), check=True, capture_output=True,
                          text=True, timeout=60).stdout.strip()


def ceil_log2(n):
    return 0 if n <= 1 else (n - 1).bit_length()


def slot_words(count, precision):
    coefficient_words = (precision + 63) // 64
    if count == 0:
        return coefficient_words
    return max(coefficient_words, (2 * precision + ceil_log2(count) + 63) // 64)


def result_precision(count, precision):
    return precision if count == 0 else 2 * precision + ceil_log2(count)


def make_inputs(count, precision, set_index):
    state = (SEED ^ (count * 0x9E3779B97F4A7C15) ^
             (precision * 0xD1B54A32D192ED03) ^ (set_index * 0x94D049BB133111EB)) & MASK64
    if state == 0:
        state = 1
    coefficient_mask = (1 << precision) - 1

    def next_word():
        nonlocal state
        state ^= (state << 13) & MASK64
        state &= MASK64
        state ^= state >> 7
        state ^= (state << 17) & MASK64
        state &= MASK64
        return state & coefficient_mask

    left = [next_word() for _ in range(count)]
    right = [next_word() for _ in range(count)]
    return left, right


def words_bytes(words):
    return b"".join(word.to_bytes(8, "little") for word in words)


def input_bytes(pair):
    return words_bytes(pair[0]) + words_bytes(pair[1])


def oracle(left, right, precision):
    result = []
    for degree in range(len(left) + len(right)):
        low = max(0, degree - len(right) + 1)
        high = min(len(left) - 1, degree)
        total = sum(left[i] * right[degree - i] for i in range(low, high + 1))
        result.append(total)
    return result


def cpu_model():
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def percentile95(values):
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def write_csv(path, fieldnames, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps-root", type=Path, required=True)
    parser.add_argument("--layout-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cpu", type=int, default=0)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError("Choose a fresh output directory outside the checkout")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("Pinned benchmark requires x86_64 Linux/WSL")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Commit all benchmark sources before measurement")

    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    base_feature = "a94e71a1945352b35e9df882612381d50dbf1fbf"
    subprocess.run(git_adapter() + ["merge-base", "--is-ancestor", base_feature, head],
                   check=True, capture_output=True, timeout=60)
    mainline = git("rev-parse", MAINLINE_BASELINE)
    mainline_product_blobs = {}
    candidate_product_blobs = {}
    for name in PRODUCT_SOURCES:
        mainline_blob = git("rev-parse", f"{mainline}:{name}")
        candidate_blob = git("rev-parse", f"HEAD:{name}")
        if mainline_blob != candidate_blob:
            raise RuntimeError("Exact product implementation differs from the mainline baseline: " + name)
        mainline_product_blobs[name] = mainline_blob
        candidate_product_blobs[name] = candidate_blob
    source_files = [ROOT / "experiments/packed-convolution/consumer_bench.rs", Path(__file__).resolve()]
    source_hashes = {str(path.relative_to(ROOT)): file_sha(path) for path in source_files}
    for path in source_files:
        if git("show", f"HEAD:{path.relative_to(ROOT).as_posix()}") != path.read_text(encoding="utf-8"):
            raise RuntimeError("Committed source does not match the measured source: " + str(path))

    layout_dir = args.layout_gate.resolve()
    layout_report_path = layout_dir / "verification.json"
    layout_report = json.loads(layout_report_path.read_text(encoding="utf-8"))
    if layout_report.get("status") != "pass_runtime_refinement_candidate":
        raise RuntimeError("The same-source packed layout refinement gate did not pass")
    if layout_report.get("source_git", {}).get("head") != head:
        raise RuntimeError("Packed layout refinement report is bound to another source commit")
    module_hash = file_sha(ROOT / "native/verified/packed_layout.rs")
    layout_source_hash = layout_report["source_git"]["source_sha256"]["native/verified/packed_layout.rs"]
    if module_hash != layout_source_hash:
        raise RuntimeError("Packed layout code differs from the refinement-gate source")
    gate_rlib = layout_dir / "libverigmp.rlib"
    if file_sha(gate_rlib) != layout_report["library_sha256"]["rlib"]:
        raise RuntimeError("Refinement-gate library hash does not match its receipt")

    deps = args.deps_root.resolve()
    pin = json.loads((ROOT / "native/toolchain.json").read_text(encoding="utf-8"))
    verifier = deps / "verus/verus-x86-linux/verus"
    rustup = deps / "cargo/bin/rustup"
    env = dict(os.environ, CARGO_HOME=str(deps / "cargo"), RUSTUP_HOME=str(deps / "rustup"),
               RUSTUP_TOOLCHAIN=pin["rust_toolchain"], PYTHONDONTWRITEBYTECODE="1")
    env["PATH"] = str(deps / "cargo/bin") + os.pathsep + env.get("PATH", "")
    verus_result = subprocess.run([verifier, "--version"], env=env, check=True,
                                  capture_output=True, text=True)
    verus_version = verus_result.stdout + verus_result.stderr
    rustc_version = subprocess.run([rustup, "run", pin["rust_toolchain"], "rustc", "-vV"], env=env,
                                    check=True, capture_output=True, text=True).stdout
    if pin["verus_version"] not in verus_version or pin["rust_toolchain"] not in verus_version:
        raise RuntimeError("Installed Verus does not match native/toolchain.json")
    if "release: 1.99.1" not in rustc_version:
        raise RuntimeError("Installed rustc does not match native/toolchain.json")

    os.sched_setaffinity(0, {args.cpu})
    output.mkdir(parents=True)
    binary = output / "packed-consumer-bench"
    command = [rustup, "run", pin["rust_toolchain"], "rustc",
               ROOT / "experiments/packed-convolution/consumer_bench.rs", "--crate-name", "packed_consumer_bench",
               "--edition=2024", "-O", "-C", "debuginfo=0",
               "-L", f"dependency={layout_dir}", "-L", f"dependency={verifier.parent}",
               "--extern", f"verigmp={gate_rlib}", "-o", binary]
    build = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=300)
    (output / "build.stdout.log").write_text(build.stdout, encoding="utf-8")
    (output / "build.stderr.log").write_text(build.stderr, encoding="utf-8")
    if build.returncode:
        raise RuntimeError("Release harness build failed; inspect build.stderr.log")

    cpu_set = sorted(os.sched_getaffinity(0))
    if cpu_set != [args.cpu]:
        raise RuntimeError("Benchmark process is not pinned to exactly the requested CPU")
    run = subprocess.run([binary], cwd=ROOT, env=env, capture_output=True,
                         timeout=3600)
    stdout = run.stdout
    stderr = run.stderr
    (output / "runner.stdout.log").write_bytes(stdout)
    (output / "runner.stderr.log").write_bytes(stderr)
    if run.returncode:
        raise RuntimeError("Benchmark runner failed; inspect runner.stderr.log")

    shape_lines = {}
    result_lines = {}
    sample_rows = []
    short_rows = []
    for raw in stdout.decode("utf-8").splitlines():
        if raw.startswith("SHAPE,shape,") or raw.startswith("SAMPLE,shape,") or raw.startswith("RESULT,shape,"):
            continue
        fields = raw.split(",")
        if fields[0] == "SHAPE":
            shape_lines[int(fields[1])] = dict(count=int(fields[2]), input_precision=int(fields[3]),
                                               output_precision=int(fields[4]), slot_words=int(fields[5]),
                                               guard_bits=int(fields[6]), output_words=int(fields[7]))
        elif fields[0] == "RESULT":
            _, shape, mode, encoded = raw.split(",", 3)
            key = (int(shape), mode)
            if key in result_lines:
                raise RuntimeError("Duplicate output record: " + str(key))
            result_lines[key] = [int(word, 16) for word in encoded.split(";") if word]
        elif fields[0] == "SAMPLE":
            if len(fields) != 7:
                raise RuntimeError("Malformed raw sample line: " + raw)
            sample_rows.append(dict(shape=int(fields[1]), phase=fields[2], mode=fields[3],
                                    repetition=int(fields[4]), iterations=int(fields[5]),
                                    total_ns=int(fields[6])))
        elif fields[0] == "SHORT":
            if len(fields) != 7:
                raise RuntimeError("Malformed short-attempt line: " + raw)
            short_rows.append(dict(shape=int(fields[1]), phase=fields[2], mode=fields[3],
                                   repetition=int(fields[4]), iterations=int(fields[5]),
                                   total_ns=int(fields[6]), status="below_10ms_retried"))
        else:
            raise RuntimeError("Unrecognized runner output: " + raw[:120])

    if len(shape_lines) != len(SHAPES):
        raise RuntimeError("Runner did not emit every declared workload")
    if len(sample_rows) != len(SHAPES) * len(PHASES) * len(MODES) * REPS:
        raise RuntimeError("Raw sample count is incomplete")

    input_records = []
    result_records = []
    for shape, (count, precision) in enumerate(SHAPES):
        info = shape_lines[shape]
        output_bits = result_precision(count, precision)
        output_words = (output_bits + 63) // 64
        if info["count"] != count or info["input_precision"] != precision:
            raise RuntimeError("Runner workload declaration differs from the oracle matrix")
        expected_slot = slot_words(count, precision)
        if info["slot_words"] != expected_slot:
            raise RuntimeError("Runner chose an invalid guard-slot width")
        if info["output_precision"] != output_bits or info["output_words"] != output_words:
            raise RuntimeError("Runner output precision differs from the guard proof bound")
        max_coefficient = count * ((1 << precision) - 1) ** 2
        if max_coefficient >= 1 << output_bits:
            raise RuntimeError("The chosen output precision does not cover the coefficient bound")
        if max_coefficient >= 1 << 128:
            raise RuntimeError("u128 direct baseline would overflow")
        ring_count = STREAM_SETS
        ring = [make_inputs(count, precision, index) for index in range(ring_count)]
        input_hash = sha(b"".join(input_bytes(pair) for pair in ring))
        expected = oracle(ring[0][0], ring[0][1], precision)
        if len(expected) != 2 * count or (expected and expected[-1] != 0):
            raise RuntimeError("Oracle result-tail invariant failed")
        if any(coefficient >= 1 << output_bits for coefficient in expected):
            raise RuntimeError("Oracle coefficient exceeds the declared extracted precision")
        expected_words = [((coefficient >> (64 * limb)) & MASK64)
                          for coefficient in expected for limb in range(output_words)]
        input_records.append(dict(shape=shape, count=count, precision_bits=precision,
                                  result_precision_bits=output_bits, output_words=output_words,
                                  slot_words=expected_slot, available_guard_bits=info["guard_bits"],
                                  required_guard_bits=ceil_log2(count), ring_sets=ring_count,
                                  ring_input_sha256=input_hash,
                                  oracle_input_sha256=sha(input_bytes(ring[0]))))
        for mode in MODES:
            actual = result_lines.get((shape, mode))
            if actual != expected_words:
                raise RuntimeError(f"Independent arbitrary-integer oracle mismatch: shape={shape}, mode={mode}")
            result_records.append(dict(shape=shape, count=count, precision_bits=precision, mode=mode,
                                       result_precision_bits=output_bits, coefficient_count=len(expected),
                                       output_word_count=len(actual), final_tail_zero=(not expected or expected[-1] == 0),
                                       output_sha256=sha(words_bytes(actual)),
                                       oracle_sha256=sha(words_bytes(expected_words)),
                                       checked_every_coefficient=True))

    for row in sample_rows:
        if row["phase"] not in PHASES or row["mode"] not in MODES:
            raise RuntimeError("Unknown timing group")
        if row["repetition"] >= REPS or row["total_ns"] < MIN_BATCH_NS:
            raise RuntimeError("A recorded batch is shorter than the protocol minimum")
        row["ns_per_call"] = row["total_ns"] / row["iterations"]
        n, p = SHAPES[row["shape"]]
        row["count"] = n
        row["precision_bits"] = p
        row["slot_words"] = slot_words(n, p)

    summary_rows = []
    grouped = {}
    for row in sample_rows:
        grouped.setdefault((row["shape"], row["phase"], row["mode"]), []).append(row["ns_per_call"])
    for shape, (count, precision) in enumerate(SHAPES):
        for phase in PHASES:
            medians = {mode: statistics.median(grouped[(shape, phase, mode)]) for mode in MODES}
            summary_rows.append(dict(shape=shape, count=count, precision_bits=precision,
                                     slot_words=slot_words(count, precision),
                                     result_precision_bits=result_precision(count, precision), phase=phase,
                                     layout_median_ns=f"{medians['layout']:.3f}",
                                     bulk_zero_median_ns=f"{medians['bulk_zero']:.3f}",
                                     direct_median_ns=f"{medians['direct']:.3f}",
                                     layout_over_bulk_zero=f"{medians['layout'] / medians['bulk_zero']:.6f}",
                                     layout_over_direct=f"{medians['layout'] / medians['direct']:.6f}",
                                     layout_p95_ns=f"{percentile95(grouped[(shape, phase, 'layout')]):.3f}",
                                     bulk_zero_p95_ns=f"{percentile95(grouped[(shape, phase, 'bulk_zero')]):.3f}",
                                     direct_p95_ns=f"{percentile95(grouped[(shape, phase, 'direct')]):.3f}"))

    raw_fields = ["shape", "count", "precision_bits", "slot_words", "phase", "mode",
                  "repetition", "iterations", "total_ns", "ns_per_call"]
    write_csv(output / "timings.csv", raw_fields, sample_rows)
    write_csv(output / "discarded.csv", list(short_rows[0]) if short_rows else
              ["shape", "phase", "mode", "repetition", "iterations", "total_ns", "status"], short_rows)
    write_csv(output / "summary.csv", list(summary_rows[0]), summary_rows)
    (output / "results.json").write_text(json.dumps(result_records, indent=2) + "\n", encoding="utf-8")
    (output / "inputs.json").write_text(json.dumps(input_records, indent=2) + "\n", encoding="utf-8")
    metadata = dict(
        status="pass",
        run_id=args.run_id,
        measured_source_commit=head,
        measured_source_tree=tree,
        base_feature_commit=base_feature,
        mainline_baseline_commit=mainline,
        mainline_product_blobs=mainline_product_blobs,
        candidate_product_blobs=candidate_product_blobs,
        source_sha256=source_hashes,
        harness_binary_sha256=file_sha(binary),
        library_source_commit=layout_report["source_git"]["head"],
        library_rlib_sha256=file_sha(gate_rlib),
        library_metadata_sha256=file_sha(layout_dir / "verigmp.vir"),
        layout_refinement_report_sha256=file_sha(layout_report_path),
        packed_layout_source_sha256=module_hash,
        layout_refinement_status=layout_report["status"],
        layout_library_verified_items=layout_report["library_verified_items"],
        rustc=rustc_version,
        verus=verus_version,
        verifier_sha256=file_sha(verifier),
        rustup_sha256=file_sha(rustup),
        source_bound_gate_toolchain=layout_report.get("toolchain", {}),
        toolchain_pin=pin,
        cpu_model=cpu_model(),
        cpu_affinity=cpu_set,
        kernel=platform.release(),
        run_pid=os.getpid(),
        compiler_command=list(map(str, command)),
        runner_command=[str(binary)],
        allocation_boundary="All coefficient, packed, product, scratch, direct-accumulator, output and eviction buffers are allocated before timing. Timed operations allocate no heap storage; input generation, cache preparation, oracle checks and output hashing are outside timing.",
        cache_policy={
            "reuse": "one fixed input pair; three warm-up calls per mode; no eviction between samples",
            "streaming": "32 pre-generated input pairs; rotating starting index; before every warm-up, calibration and measured batch, touch one word per cache line across a preallocated 64 MiB buffer; cache preparation is excluded from elapsed time",
            "limitation": "Streaming is eviction-cycled, not a claim that every operation begins from DRAM; no system-wide cache flush is available.",
        },
        measurement_protocol=dict(repetitions=REPS, min_batch_ns=MIN_BATCH_NS,
                                  calibration_target_ns=25_000_000,
                                  modes=list(MODES), phases=list(PHASES),
                                  product="current production exact full product via verigmp::toom_multiply::full; threshold 24, with its 12n caller-owned scratch contract",
                                  packed_postprocess="extract exact coefficients at q=2p+ceil(log2(n)); guard words ensure each product slot is below 2^q",
                                  direct_baseline="u128 exact schoolbook coefficient convolution; all configured sums are checked below 2^128",
                                  seed=SEED),
        short_sample_attempts=len(short_rows),
        output_hashes={name: file_sha(output / name) for name in
                       ("runner.stdout.log", "runner.stderr.log", "timings.csv", "discarded.csv", "summary.csv",
                        "results.json", "inputs.json")},
    )
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status=metadata["status"], run_id=args.run_id,
                          source=head, shape_count=len(SHAPES), sample_count=len(sample_rows),
                          output=str(output)), indent=2))


if __name__ == "__main__":
    main()

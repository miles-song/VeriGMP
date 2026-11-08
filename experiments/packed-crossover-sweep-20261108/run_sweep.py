#!/usr/bin/env python3
"""Build, measure, and hash-bind one preregistered packed-layout sweep."""
import argparse
import csv
import filecmp
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import struct
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "fe9081f1a1d4075f74a46cdd66d97145d065c5ad"
MAINLINE_BASELINE = "8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa"
SEED = 16_438_731
STREAM_SETS = 32
REPS = 7
MIN_BATCH_NS = 10_000_000
PHASES = ("reuse", "streaming")
MODES = ("layout", "bulk_zero")
PRECISIONS = (7, 17, 29, 30, 53)
TRAIN_COUNTS = set(range(1, 36)) | set(range(125, 132)) | set(range(509, 516))
CONFIRM_COUNTS = set(range(60, 70)) | set(range(253, 260)) | set(range(1019, 1025))
ALL_COUNTS = sorted(TRAIN_COUNTS | CONFIRM_COUNTS)
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
MEASURED_FILES = (
    "experiments/packed-crossover-sweep-20261108/PROTOCOL.md",
    "experiments/packed-crossover-sweep-20261108/crossover_bench.rs",
    "experiments/packed-crossover-sweep-20261108/run_sweep.py",
    "experiments/packed-crossover-sweep-20261108/analyze.py",
    "native/toolchain.json",
    "native/verified/packed_layout.rs",
) + PRODUCT_SOURCES
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


def git_bytes(*args):
    return subprocess.run(git_adapter() + list(args), check=True, capture_output=True,
                          timeout=60).stdout


def ceil_log2(n):
    return 0 if n <= 1 else (n - 1).bit_length()


def output_precision(n, p):
    return 2 * p + ceil_log2(n)


def slot_words(n, p):
    return max((p + 63) // 64, (output_precision(n, p) + 63) // 64)


def selected_counts(split):
    if split == "discovery":
        return sorted(TRAIN_COUNTS)
    if split == "confirmation":
        return sorted(CONFIRM_COUNTS)
    raise ValueError("unknown split")


def shape_rows(split):
    selected = set(selected_counts(split))
    return [(shape_id, n, p)
            for shape_id, (n, p) in enumerate((n, p) for p in PRECISIONS for n in ALL_COUNTS)
            if n in selected]


def make_inputs(n, p, set_index):
    state = (SEED ^ (n * 0x9E3779B97F4A7C15) ^
             (p * 0xD1B54A32D192ED03) ^
             (set_index * 0x94D049BB133111EB)) & MASK64
    if state == 0:
        state = 1
    coefficient_mask = (1 << p) - 1

    def next_word():
        nonlocal state
        state ^= (state << 13) & MASK64
        state &= MASK64
        state ^= state >> 7
        state ^= (state << 17) & MASK64
        state &= MASK64
        return state & coefficient_mask

    return ([next_word() for _ in range(n)], [next_word() for _ in range(n)])


def words_bytes(words):
    return b"".join(struct.pack("<Q", word) for word in words)


def oracle(left, right):
    result = [0] * (len(left) + len(right))
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] += a * b
    return result


def cpu_model():
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def percentile(values, percent):
    ordered = sorted(values)
    return ordered[max(0, (percent * len(ordered) + 99) // 100 - 1)]


def write_csv(path, fields, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_result_stream(path, split, shape_info):
    checks = []
    output_path = Path(path)
    with output_path.open("rb") as stream:
        if stream.read(8) != b"PCROSS01":
            raise RuntimeError("Invalid result dump magic")
        for shape_id, n, p in shape_rows(split):
            q = output_precision(n, p)
            result_words = (q + 63) // 64
            for set_index in range(STREAM_SETS):
                left, right = make_inputs(n, p, set_index)
                exact = oracle(left, right)
                if len(exact) != 2 * n or exact[-1] != 0:
                    raise RuntimeError("Oracle result-tail invariant failed")
                if max(exact, default=0) >= 1 << q or max(exact, default=0) >= 1 << 128:
                    raise RuntimeError("Result precision/u128 domain check failed")
                expected = [((value >> (64 * limb)) & MASK64)
                            for value in exact for limb in range(result_words)]
                expected_bytes = words_bytes(expected)
                oracle_hash = sha(expected_bytes)
                first_mode = None
                for mode_index, mode in enumerate(MODES):
                    header = stream.read(17)
                    if len(header) != 17:
                        raise RuntimeError("Truncated result record")
                    actual_shape, actual_set, actual_mode, word_count = struct.unpack("<IIBQ", header)
                    if (actual_shape, actual_set, actual_mode) != (shape_id, set_index, mode_index):
                        raise RuntimeError("Result records are out of registered order")
                    if word_count != len(expected):
                        raise RuntimeError("Result record has an invalid word count")
                    payload = stream.read(word_count * 8)
                    if len(payload) != word_count * 8:
                        raise RuntimeError("Truncated result payload")
                    actual = list(struct.unpack("<" + "Q" * word_count, payload))
                    actual_hash = sha(payload)
                    if actual != expected:
                        raise RuntimeError(
                            f"Independent coefficient oracle mismatch: n={n}, p={p}, set={set_index}, mode={mode}"
                        )
                    if first_mode is not None and actual != first_mode:
                        raise RuntimeError("Cross-path exact word comparison failed")
                    if mode_index == 0:
                        first_mode = actual
                    checks.append(dict(shape=shape_id, count=n, precision_bits=p, set_index=set_index,
                                       mode=mode, coefficients=len(exact), output_words=len(actual),
                                       oracle_sha256=oracle_hash, output_sha256=actual_hash,
                                       every_coefficient_equal="true", cross_path_equal="true"))
        if stream.read(1):
            raise RuntimeError("Unexpected trailing bytes in result dump")
    if len(shape_info) != len(shape_rows(split)):
        raise RuntimeError("Runner omitted a registered shape")
    return checks


def input_hashes(split):
    rows = []
    for shape_id, n, p in shape_rows(split):
        digest = hashlib.sha256()
        for set_index in range(STREAM_SETS):
            left, right = make_inputs(n, p, set_index)
            digest.update(words_bytes(left))
            digest.update(words_bytes(right))
        rows.append(dict(shape=shape_id, count=n, precision_bits=p, ring_sets=STREAM_SETS,
                         input_sha256=digest.hexdigest()))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps-root", type=Path, required=True)
    parser.add_argument("--layout-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--split", choices=("discovery", "confirmation"), required=True)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--reference-run", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError("Choose a fresh output directory outside the checkout")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("Pinned benchmark requires x86_64 Linux/WSL")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Commit all preregistration sources before measurement")
    head = git("rev-parse", "HEAD")
    if head != git("rev-parse", f"{BASE_COMMIT}^{{commit}}") and not subprocess.run(
            git_adapter() + ["merge-base", "--is-ancestor", BASE_COMMIT, head],
            capture_output=True).returncode == 0:
        raise RuntimeError("Measured source does not descend from the reviewed package tip")
    tree = git("rev-parse", "HEAD^{tree}")
    mainline = git("rev-parse", f"{MAINLINE_BASELINE}^{{commit}}")
    for name in MEASURED_FILES:
        path = ROOT / name
        if git_bytes("show", f"HEAD:{name}") != path.read_bytes():
            raise RuntimeError("Measured file differs from committed source: " + name)
    for name in PRODUCT_SOURCES:
        if git("rev-parse", f"{mainline}:{name}") != git("rev-parse", f"HEAD:{name}"):
            raise RuntimeError("Exact product source differs from pinned mainline baseline: " + name)
    source_hashes = {name: file_sha(ROOT / name) for name in MEASURED_FILES}

    layout_dir = args.layout_gate.resolve()
    report_path = layout_dir / "verification.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "pass_runtime_refinement_candidate" or report.get("source_git", {}).get("head") != head:
        raise RuntimeError("Packed-layout verification gate is not bound to this source commit")
    if file_sha(ROOT / "native/verified/packed_layout.rs") != report["source_git"]["source_sha256"]["native/verified/packed_layout.rs"]:
        raise RuntimeError("Packed-layout source differs from gate")
    gate_rlib = layout_dir / "libverigmp.rlib"
    if file_sha(gate_rlib) != report["library_sha256"]["rlib"]:
        raise RuntimeError("Packed-layout gate rlib hash mismatch")

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
    if pin["verus_version"] not in verus_version or "release: 1.99.1" not in rustc_version:
        raise RuntimeError("Installed Verus/Rust differs from native/toolchain.json")
    rustc_path = Path(subprocess.run(
        [rustup, "which", "--toolchain", pin["rust_toolchain"], "rustc"],
        env=env, check=True, capture_output=True, text=True,
    ).stdout.strip())
    tool_files = [verifier, rustup, rustc_path] + [
        verifier.parent / name for name in (
            "rust_verify", "z3", "libvstd.rlib", "vstd.vir",
            "libverus_builtin.rlib", "libverus_builtin_macros.so",
        )
    ]
    tool_sha256 = {str(path): file_sha(path) for path in tool_files}

    os.sched_setaffinity(0, {args.cpu})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    binary = output / "packed-crossover-bench"
    rust_source = ROOT / "experiments/packed-crossover-sweep-20261108/crossover_bench.rs"
    command = [rustup, "run", pin["rust_toolchain"], "rustc", rust_source,
               "--crate-name", "packed_crossover_bench", "--edition=2024",
               "-O", "-C", "debuginfo=0", "-L", f"dependency={layout_dir}",
               "-L", f"dependency={verifier.parent}", "--extern", f"verigmp={gate_rlib}",
               "-o", binary]
    build = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=300)
    (output / "build.stdout.log").write_text(build.stdout, encoding="utf-8")
    (output / "build.stderr.log").write_text(build.stderr, encoding="utf-8")
    if build.returncode:
        raise RuntimeError("Release harness build failed; inspect build.stderr.log")
    cpu_set = sorted(os.sched_getaffinity(0))
    if cpu_set != [args.cpu]:
        raise RuntimeError("Measurement is not pinned to exactly the requested CPU")

    result_path = output / "results.bin"
    run = subprocess.run([binary, args.split, result_path], cwd=ROOT, env=env,
                         capture_output=True, timeout=7200)
    (output / "runner.stdout.log").write_bytes(run.stdout)
    (output / "runner.stderr.log").write_bytes(run.stderr)
    if run.returncode:
        raise RuntimeError("Crossover runner failed; inspect runner.stderr.log")

    shape_records = {}
    sample_rows = []
    short_rows = []
    for raw in run.stdout.decode("utf-8").splitlines():
        if raw.startswith("SHAPE,shape,") or raw.startswith("SAMPLE,shape,") or raw.startswith("SHORT,shape,"):
            continue
        fields = raw.split(",")
        if fields[0] == "SHAPE":
            shape_id = int(fields[1])
            if shape_id in shape_records:
                raise RuntimeError("Duplicate shape metadata row")
            shape_records[shape_id] = dict(count=int(fields[2]), precision_bits=int(fields[3]),
                                           result_precision_bits=int(fields[4]), slot_words=int(fields[5]),
                                           required_guard_bits=int(fields[6]), guard_margin_bits=int(fields[7]))
        elif fields[0] in ("SAMPLE", "SHORT"):
            if len(fields) != 7:
                raise RuntimeError("Malformed runner timing row")
            row = dict(shape=int(fields[1]), phase=fields[2], mode=fields[3],
                       repetition=int(fields[4]), iterations=int(fields[5]), total_ns=int(fields[6]))
            if fields[0] == "SHORT":
                row["status"] = "below_10ms_retried"
                short_rows.append(row)
            else:
                sample_rows.append(row)
        else:
            raise RuntimeError("Unrecognized runner output: " + raw[:120])

    expected_shapes = shape_rows(args.split)
    if len(shape_records) != len(expected_shapes):
        raise RuntimeError("Runner shape count differs from preregistered split")
    for shape_id, n, p in expected_shapes:
        info = shape_records.get(shape_id)
        q = output_precision(n, p)
        if info is None or info != dict(count=n, precision_bits=p, result_precision_bits=q,
                                        slot_words=slot_words(n, p), required_guard_bits=ceil_log2(n),
                                        guard_margin_bits=64 * slot_words(n, p) - q):
            raise RuntimeError(f"Runner shape metadata mismatch: {shape_id}")
        maximum = n * ((1 << p) - 1) ** 2
        if maximum >= 1 << q or maximum >= 1 << 128:
            raise RuntimeError("Registered coefficient bound exceeds precision or u128")
    expected_sample_count = len(expected_shapes) * len(PHASES) * len(MODES) * REPS
    if len(sample_rows) != expected_sample_count:
        raise RuntimeError(f"Expected {expected_sample_count} sample rows, got {len(sample_rows)}")
    if any(row["total_ns"] < MIN_BATCH_NS for row in sample_rows):
        raise RuntimeError("Recorded timing row is shorter than 10 ms")
    registered_keys = {
        (shape_id, phase, mode, repetition)
        for shape_id, _, _ in expected_shapes for phase in PHASES
        for mode in MODES for repetition in range(REPS)
    }
    actual_keys = [(row["shape"], row["phase"], row["mode"], row["repetition"]) for row in sample_rows]
    if len(set(actual_keys)) != len(actual_keys) or set(actual_keys) != registered_keys:
        raise RuntimeError("Measured sample groups are incomplete or duplicated")

    for row in sample_rows:
        if row["shape"] not in shape_records or row["phase"] not in PHASES or row["mode"] not in MODES:
            raise RuntimeError("Timing row has an unregistered group")
        if row["repetition"] >= REPS or row["iterations"] <= 0:
            raise RuntimeError("Timing row has an invalid repetition or iteration count")
        info = shape_records[row["shape"]]
        row.update(count=info["count"], precision_bits=info["precision_bits"],
                   slot_words=info["slot_words"], result_precision_bits=info["result_precision_bits"],
                   required_guard_bits=info["required_guard_bits"], guard_margin_bits=info["guard_margin_bits"],
                   ns_per_call=row["total_ns"] / row["iterations"])
    groups = {}
    for row in sample_rows:
        groups.setdefault((row["shape"], row["phase"], row["mode"]), []).append(row["ns_per_call"])
    summary_rows = []
    for shape_id, n, p in expected_shapes:
        info = shape_records[shape_id]
        for phase in PHASES:
            layout = groups[(shape_id, phase, "layout")]
            bulk = groups[(shape_id, phase, "bulk_zero")]
            layout_median = statistics.median(layout)
            bulk_median = statistics.median(bulk)
            summary_rows.append(dict(shape=shape_id, count=n, precision_bits=p,
                                     result_precision_bits=info["result_precision_bits"],
                                     slot_words=info["slot_words"], required_guard_bits=info["required_guard_bits"],
                                     guard_margin_bits=info["guard_margin_bits"], phase=phase,
                                     layout_median_ns=f"{layout_median:.3f}",
                                     bulk_zero_median_ns=f"{bulk_median:.3f}",
                                     layout_over_bulk_zero=f"{layout_median / bulk_median:.8f}",
                                     layout_p95_ns=f"{percentile(layout, 95):.3f}",
                                     bulk_zero_p95_ns=f"{percentile(bulk, 95):.3f}"))
    raw_fields = ["shape", "count", "precision_bits", "result_precision_bits", "slot_words",
                  "required_guard_bits", "guard_margin_bits", "phase", "mode", "repetition",
                  "iterations", "total_ns", "ns_per_call"]
    write_csv(output / "timings.csv", raw_fields, sample_rows)
    short_fields = ["shape", "count", "precision_bits", "phase", "mode", "repetition",
                    "iterations", "total_ns", "status"]
    short_output = []
    for row in short_rows:
        info = shape_records[row["shape"]]
        row.update(count=info["count"], precision_bits=info["precision_bits"])
        short_output.append(row)
    write_csv(output / "discarded.csv", short_fields, short_output)
    write_csv(output / "summary.csv", list(summary_rows[0]), summary_rows)

    inputs_rows = input_hashes(args.split)
    write_csv(output / "inputs.csv", ["shape", "count", "precision_bits", "ring_sets", "input_sha256"], inputs_rows)
    oracle_checks = []
    reference_meta = None
    if args.reference_run:
        reference = args.reference_run.resolve()
        reference_meta = json.loads((reference / "metadata.json").read_text(encoding="utf-8"))
        if reference_meta.get("split") != args.split or reference_meta.get("status") != "pass":
            raise RuntimeError("Reference run is not a passing run of the same split")
        if reference_meta.get("harness_binary_sha256") != file_sha(binary):
            raise RuntimeError("Independent release executable hash differs from reference")
        if reference_meta.get("inputs_csv_sha256") != file_sha(output / "inputs.csv"):
            raise RuntimeError("Reference input hashes differ")
        if not filecmp.cmp(result_path, reference / "results.bin", shallow=False):
            raise RuntimeError("Independent result dump differs byte for byte")
        shutil.copyfile(reference / "oracle-checks.csv", output / "oracle-checks.csv")
        if file_sha(output / "oracle-checks.csv") != reference_meta["oracle_checks_sha256"]:
            raise RuntimeError("Reference oracle receipt hash mismatch")
        oracle_mode = "byte_identical_to_oracle_checked_independent_run"
    else:
        oracle_checks = read_result_stream(result_path, args.split, shape_records)
        write_csv(output / "oracle-checks.csv", list(oracle_checks[0]), oracle_checks)
        oracle_mode = "independent_python_integer_convolution_every_coefficient"
    if len(inputs_rows) != len(expected_shapes):
        raise RuntimeError("Input ring hash coverage incomplete")

    metadata = dict(
        status="pass", run_id=args.run_id, split=args.split, base_commit=BASE_COMMIT,
        measured_source_commit=head, measured_source_tree=tree,
        mainline_product_baseline_commit=mainline,
        mainline_product_blobs={name: git(f"rev-parse", f"{mainline}:{name}") for name in PRODUCT_SOURCES},
        candidate_product_blobs={name: git(f"rev-parse", f"HEAD:{name}") for name in PRODUCT_SOURCES},
        source_file_sha256=source_hashes,
        layout_gate_commit=report["source_git"]["head"],
        layout_gate_report_sha256=file_sha(report_path),
        packed_layout_source_sha256=file_sha(ROOT / "native/verified/packed_layout.rs"),
        library_rlib_sha256=file_sha(gate_rlib),
        library_metadata_sha256=file_sha(layout_dir / "verigmp.vir"),
        harness_binary_sha256=file_sha(binary),
        verifier_sha256=file_sha(verifier), rustup_sha256=file_sha(rustup),
        tool_file_sha256=tool_sha256,
        verus_version=verus_version, rustc_version=rustc_version,
        toolchain_pin=pin, cpu_model=cpu_model(), cpu_affinity=cpu_set,
        kernel=platform.release(), runner_pid=os.getpid(), split_shape_count=len(expected_shapes),
        registered_precisions_bits=list(PRECISIONS), stream_sets=STREAM_SETS, phases=list(PHASES),
        modes=list(MODES), repetitions=REPS, min_batch_ns=MIN_BATCH_NS,
        calibration_target_ns=25_000_000, short_attempt_count=len(short_rows),
        all_recorded_batches_at_least_10ms=True,
        allocation_boundary="All inputs, workspaces, result buffers, and the 64 MiB eviction buffer are allocated before timing. Input generation, output dump writes, cache preparation, Python oracle checks, and file hashing are outside timed batches.",
        product_composition="pack_coefficients or bulk-zero/copy packing, then verigmp::toom_multiply::full at threshold 24 with 12n caller-owned scratch, then extract_coefficients at q=2p+ceil(log2(n)).",
        streaming_policy="32 pre-generated input pairs; one word per cache line is touched across a preallocated 64 MiB buffer before each batch; eviction preparation is outside timing.",
        oracle_mode=oracle_mode,
        reference_run=args.reference_run.resolve().as_posix() if args.reference_run else None,
        result_dump_sha256=file_sha(result_path), inputs_csv_sha256=file_sha(output / "inputs.csv"),
        oracle_checks_sha256=file_sha(output / "oracle-checks.csv"),
        output_sha256={name: file_sha(output / name) for name in
                       ("runner.stdout.log", "runner.stderr.log", "timings.csv", "discarded.csv", "summary.csv",
                        "inputs.csv", "oracle-checks.csv", "results.bin")},
        compiler_command=list(map(str, command)),
        allocation_and_timing_statement="No benchmark buffer, source input, or consumer workspace is allocated inside the timed operation. The result binary is written after timing for each shape.",
    )
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(status="pass", run_id=args.run_id, split=args.split, source=head,
                          shape_count=len(expected_shapes), raw_samples=len(sample_rows),
                          binary_sha256=metadata["harness_binary_sha256"],
                          result_sha256=metadata["result_dump_sha256"], output=str(output)), indent=2))


if __name__ == "__main__":
    main()

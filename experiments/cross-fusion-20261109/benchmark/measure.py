#!/usr/bin/env python3
"""Measurement driver: execute only after root explicitly grants a quiet window."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def order(cell, block, run):
    return "ABBA" if (cell + block + run) % 2 == 0 else "BAAB"


def telemetry(cpu):
    result = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    for name, path in (("stat", "/proc/stat"), ("load", "/proc/loadavg"),
                       ("pressure", "/proc/pressure/cpu"),
                       ("frequency", f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq")):
        try:
            result[name] = Path(path).read_text().strip()
        except OSError as error:
            result[name] = {"unavailable": str(error)}
    result["temperatures"] = {}
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            result["temperatures"][str(path)] = path.read_text().strip()
        except OSError as error:
            result["temperatures"][str(path)] = {"unavailable": str(error)}
    return result


def record(stream, row):
    stream.write(json.dumps(row, sort_keys=True) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def invoke(argv, stream, fields, cpu):
    record(stream, dict(fields, record="invocation", argv=argv, telemetry=telemetry(cpu)))
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               preexec_fn=lambda: os.sched_setaffinity(0, {cpu}))
    try:
        stdout, stderr = process.communicate(timeout=180)
        timeout = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        timeout = True
    record(stream, dict(fields, record="outcome", exit_code=process.returncode,
                        timeout=timeout, stdout_hex=stdout.hex(), stderr_hex=stderr.hex(),
                        telemetry=telemetry(cpu)))
    if timeout or process.returncode:
        raise RuntimeError("benchmark invocation failed; inspect retained outcome")
    value = json.loads(stdout)
    if value.get("verified") is not True:
        raise RuntimeError("GMP comparison was not reported as verified")
    if value.get("cpus_allowed") != str(cpu):
        raise RuntimeError("benchmark process did not retain the requested CPU affinity")
    return value


def verify_inputs(root, manifest):
    for path, digest in manifest["input_files"].items():
        if sha(root / path) != digest:
            raise RuntimeError("input bytes changed: " + path)


def verify_build(build, manifest):
    if sha(build["native_mapping"]) != build["native_mapping_sha256"]:
        raise RuntimeError("baseline to main source mapping changed")
    for path, digest in build["harness_files"].items():
        if sha(path) != digest:
            raise RuntimeError("committed harness changed: " + path)
    compiler = build["compiler_identity"]
    for name in ("rustc", "cc", "linker"):
        if sha(compiler[name + "_path"]) != compiler[name + "_sha256"]:
            raise RuntimeError("compiler or linker changed: " + name)
    for label in ("baseline", "candidate"):
        row = build["binaries"][label]
        if row["commit"] != manifest[label + "_commit"]:
            raise RuntimeError("unexpected source commit: " + label)
        if not row["same_source_verified"] or not row["rlib_sha256"] or not row["vir_sha256"]:
            raise RuntimeError("missing source-bound proof and compilation: " + label)
        for key in ("path", "rlib", "vir", "proof_receipt", "symbols", "disassembly", "relocations", "link_map"):
            if sha(row[key]) != row[key + "_sha256"]:
                raise RuntimeError("build identity changed: " + label + "/" + key)
        if sha(row["harness"]) != row["harness_sha256"]:
            raise RuntimeError("benchmark source changed: " + label)
        for path, digest in row["dependencies"].items():
            if sha(path) != digest:
                raise RuntimeError("linked library changed: " + path)
        for path, digest in row["link_inputs"].items():
            if sha(path) != digest:
                raise RuntimeError("link input changed: " + path)
    if build["binaries"]["baseline"]["harness_sha256"] != build["binaries"]["candidate"]["harness_sha256"]:
        raise RuntimeError("harness sources differ")
    if build["binaries"]["baseline"]["compiler_identity"] != build["binaries"]["candidate"]["compiler_identity"]:
        raise RuntimeError("compiler identities differ")


def main_refs(build):
    mapping = json.loads(Path(build["native_mapping"]).read_text())
    refs = {}
    for name in ("refs/heads/main", "refs/remotes/origin/main"):
        tip = subprocess.run(["git", "rev-parse", name], check=True, capture_output=True, text=True).stdout.strip()
        tree = subprocess.run(["git", "rev-parse", tip + ":native"], check=True, capture_output=True, text=True).stdout.strip()
        if tree != mapping["native_trees"]["baseline"]:
            raise RuntimeError("current main native tree differs from the proven baseline")
        refs[name] = dict(commit=tip, native_tree=tree)
    if refs["refs/heads/main"] != refs["refs/remotes/origin/main"]:
        raise RuntimeError("local and remote-tracking main identities differ")
    return refs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--run", type=int, choices=(1, 2), required=True)
    parser.add_argument("--group", choices=("full", "default"), required=True)
    args = parser.parse_args()
    authorization = json.loads(args.authorization.read_text())
    if authorization.get("root_explicitly_authorized_timing") is not True:
        raise RuntimeError("root timing authorization is required")
    manifest = json.loads(args.manifest.read_text())
    build = json.loads(args.build.read_text())
    verify_build(build, manifest)
    verify_inputs(args.manifest.parent, manifest)
    refs = main_refs(build)
    preflight = json.loads(args.preflight.read_text())
    if (preflight.get("status") != "pass" or preflight.get("manifest_sha256") != sha(args.manifest)
            or preflight.get("build_sha256") != sha(args.build)
            or preflight.get("checks") != 2 * len(manifest["cells"])
            or sha(preflight["raw"]) != preflight["raw_sha256"]):
        raise RuntimeError("complete untimed GMP preflight is required for this exact build and manifest")
    if args.cpu not in os.sched_getaffinity(0):
        raise RuntimeError("requested CPU is not available")
    if (authorization.get("build_sha256") != sha(args.build)
            or authorization.get("manifest_sha256") != sha(args.manifest)
            or authorization.get("preflight_sha256") != sha(args.preflight)):
        raise RuntimeError("authorization must bind the exact build, input manifest and preflight")
    args.output.mkdir(parents=True, exist_ok=False)
    cells = [c for c in manifest["cells"] if ("_full" in c["op"]) == (args.group == "full")]
    report = dict(status="running", run=args.run, group=args.group, cpu=args.cpu,
                  manifest_sha256=sha(args.manifest), build_sha256=sha(args.build),
                  preflight_sha256=sha(args.preflight),
                  authorization_sha256=sha(args.authorization),
                  native_mapping_sha256=build["native_mapping_sha256"], main_refs_before=refs,
                  allowed_cpus=sorted(os.sched_getaffinity(0)), uname=list(os.uname()),
                  cpu_siblings=Path(f"/sys/devices/system/cpu/cpu{args.cpu}/topology/thread_siblings_list").read_text().strip(),
                  cpuinfo=Path("/proc/cpuinfo").read_text(), cells=[])
    binary = {"A": build["binaries"]["baseline"]["path"],
              "B": build["binaries"]["candidate"]["path"]}
    with (args.output / "raw.jsonl").open("w") as raw:
        try:
            for index, cell in enumerate(cells):
                path = args.manifest.parent / cell["input"]
                if sha(path) != cell["input_sha256"]:
                    raise RuntimeError("input changed before cell")
                def call(label, mode, count, **fields):
                    argv = [binary[label], mode, cell["op"], str(cell["n"]), str(cell["top"]),
                            str(path), str(cell["alias"]).lower(), str(count)]
                    return invoke(argv, raw, dict(cell=index, input_sha256=cell["input_sha256"],
                                                   label=label, mode=mode, **fields), args.cpu)
                calibration_order = "AB" if (index + args.run) % 2 == 0 else "BA"
                counts = [call(label, "calibrate", 1)["iterations"] for label in calibration_order]
                count = max(counts)
                blocks = []
                for block in range(4):
                    for attempt in range(4):
                        labels = order(index, block, args.run)
                        rows = [call(label, "sample", count, block=block, attempt=attempt,
                                     position=position, sequence=labels)
                                for position, label in enumerate(labels)]
                        valid = all(row["ns"] >= 10_000_000 and row["iterations"] == count for row in rows)
                        record(raw, dict(record="block_decision", cell=index, block=block,
                                         attempt=attempt, sequence=labels, valid=valid, count=count))
                        if valid:
                            by_label = {label: [row["ns"] / count for x, row in zip(labels, rows) if x == label]
                                        for label in "AB"}
                            ratio = math.sqrt(math.prod(by_label["B"]) / math.prod(by_label["A"]))
                            blocks.append(dict(sequence=labels, count=count, ratio=ratio, samples=by_label))
                            break
                        count *= 2
                    else:
                        raise RuntimeError("four complete blocks below minimum duration")
                if sha(path) != cell["input_sha256"]:
                    raise RuntimeError("input changed after cell")
                report["cells"].append(dict(**cell, blocks=blocks,
                    candidate_over_baseline=statistics.median(block["ratio"] for block in blocks)))
                (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            verify_inputs(args.manifest.parent, manifest)
            verify_build(build, manifest)
            report["main_refs_after"] = main_refs(build)
            if report["main_refs_after"] != refs:
                raise RuntimeError("main identity changed during run")
            if sha(args.manifest) != report["manifest_sha256"] or sha(args.build) != report["build_sha256"]:
                raise RuntimeError("manifest or build receipt changed during run")
            report["status"] = "complete_pending_host_and_review"
        except Exception as error:
            report["status"] = "failed"
            report["failure"] = repr(error)
            raise
        finally:
            raw.flush()
            report["raw_sha256"] = sha(args.output / "raw.jsonl")
            (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

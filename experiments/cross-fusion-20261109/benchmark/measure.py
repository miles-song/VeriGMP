#!/usr/bin/env python3
"""Measurement driver: execute only after root explicitly grants a quiet window."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import statistics
import subprocess

RUNTIME_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}


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


def process_identity(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return dict(pid=pid, start_ticks=int(stat[19]))
    except (OSError, ValueError, IndexError):
        return dict(pid=pid, start_ticks=None)


def invoke(argv, stream, fields, cpu, runtime_environment):
    record(stream, dict(fields, record="invocation", argv=argv, telemetry=telemetry(cpu)))
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               preexec_fn=lambda: os.sched_setaffinity(0, {cpu}),
                               env=runtime_environment)
    identity = process_identity(process.pid)
    try:
        stdout, stderr = process.communicate(timeout=180)
        timeout = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        timeout = True
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record(stream, dict(fields, record="outcome", process_identity=identity,
                        started_utc=started_utc,
                        ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        child_cpu_seconds=(after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime),
                        exit_code=process.returncode,
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
    if build["runtime_environment"] != RUNTIME_ENVIRONMENT:
        raise RuntimeError("unexpected runtime environment; loader variables must be absent")
    if sha(build["native_mapping"]) != build["native_mapping_sha256"]:
        raise RuntimeError("baseline to main source mapping changed")
    for path, digest in build["harness_files"].items():
        if sha(path) != digest:
            raise RuntimeError("committed harness changed: " + path)
    compiler = build["compiler_identity"]
    for name in ("rustc", "cc", "linker", "ldd", "shell"):
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


def public_remote_main(git, expected):
    windows_git = Path('/mnt/c/Program Files/Git/cmd/git.exe')
    executable = str(windows_git) if windows_git.is_file() else git
    command = [executable, 'ls-remote', '--exit-code',
               'https://github.com/miles-song/VeriGMP.git', 'refs/heads/main']
    environment = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        environment.pop(key, None)
    process = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60,
                             cwd='/mnt/c' if windows_git.is_file() else '/', env=environment)
    if process.stdout.strip() != expected + '\trefs/heads/main':
        raise RuntimeError('actual public main differs from the recorded local main')
    tools = {executable: sha(executable)}
    if windows_git.is_file():
        for path in (Path('/mnt/c/Program Files/Git/mingw64/bin/git.exe'),
                     Path('/mnt/c/Program Files/Git/mingw64/libexec/git-core/git-remote-https.exe')):
            if path.is_file():
                tools[str(path)] = sha(path)
    return dict(command=command, exit_code=process.returncode, stdout=process.stdout.strip(), tools=tools)


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
    origin = subprocess.run(["git", "remote", "get-url", "origin"], check=True,
                            capture_output=True, text=True).stdout.strip()
    if origin not in ("git@github.com:miles-song/VeriGMP.git", "https://github.com/miles-song/VeriGMP.git"):
        raise RuntimeError("origin does not match the public repository")
    refs["public_remote"] = dict(origin=origin, **public_remote_main('git', refs["refs/heads/main"]["commit"]))
    return refs


def runtime_dependencies(build, cpu=None):
    environment = build["runtime_environment"]
    if environment != RUNTIME_ENVIRONMENT:
        raise RuntimeError("unexpected runtime environment")
    config = {}
    for name in ("/etc/ld.so.cache", "/etc/ld.so.preload"):
        path = Path(name)
        config[name] = sha(path) if path.is_file() else None
    result = dict(environment=environment, excluded="all LD_* variables and GLIBC_TUNABLES",
                  loader_config=config, binaries={}, errors=[])
    for label in ("baseline", "candidate"):
        row = build["binaries"][label]
        command = [build["compiler_identity"]["ldd_path"], row["path"]]
        affinity = None if cpu is None else lambda: os.sched_setaffinity(0, {cpu})
        process = subprocess.run(command, capture_output=True, text=True, env=environment,
                                 preexec_fn=affinity, timeout=60)
        if process.returncode or "not found" in process.stdout:
            result["errors"].append("runtime loader inspection failed: " + label)
        paths = re.findall(r"(?:=>\s+|^\s*)(/\S+)\s+\(0x[0-9a-f]+\)", process.stdout, re.M)
        dependencies = {}
        for path in paths:
            try:
                dependencies[path] = sha(path)
            except OSError as error:
                result["errors"].append("unreadable runtime dependency: " + path + ": " + str(error))
        if dependencies != row["dependencies"]:
            result["errors"].append("effective runtime dependencies differ from the build: " + label)
        result["binaries"][label] = dict(command=command, exit_code=process.returncode,
                                         stdout=process.stdout, stderr=process.stderr,
                                         dependencies=dependencies)
    if result["binaries"]["baseline"]["dependencies"] != result["binaries"]["candidate"]["dependencies"]:
        result["errors"].append("baseline and candidate resolve different runtime libraries")
    return result


def require_runtime_dependencies(result):
    if result["errors"]:
        raise RuntimeError("; ".join(result["errors"]))


def stability(blocks):
    directions = {direction: [block["ratio"] for block in blocks if block["sequence"] == direction]
                  for direction in ("ABBA", "BAAB")}
    if any(len(values) != 2 for values in directions.values()):
        raise RuntimeError("each order must occur exactly twice")
    means = {name: math.sqrt(math.prod(values)) for name, values in directions.items()}
    repeated_spread = {name: max(values) / min(values) for name, values in directions.items()}
    order_spread = max(means.values()) / min(means.values())
    median = statistics.median(block["ratio"] for block in blocks)
    return dict(direction_ratios=directions, direction_geometric_means=means,
                repeated_spread=repeated_spread, order_spread=order_spread, median=median,
                stable=all(value <= 1.02 for value in repeated_spread.values()) and order_spread <= 1.02,
                improvement=median <= 0.97 and all(value <= 0.98 for value in means.values()),
                no_regression=median <= 1.03 and all(value <= 1.03 for value in means.values()))


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
    parser.add_argument("--attempt", type=int, choices=(1, 2), required=True)
    parser.add_argument("--retry-of", type=Path)
    parser.add_argument("--retry-reason", choices=("stability", "environment"))
    parser.add_argument("--environment-receipt", type=Path)
    parser.add_argument("--host-telemetry", type=Path, required=True)
    parser.add_argument("--wsl-telemetry", type=Path, required=True)
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
            or preflight.get("warmup_checks") != 2 * len(manifest["cells"])
            or sha(preflight["raw"]) != preflight["raw_sha256"]):
        raise RuntimeError("complete untimed GMP preflight is required for this exact build and manifest")
    if args.cpu not in os.sched_getaffinity(0):
        raise RuntimeError("requested CPU is not available")
    if (authorization.get("build_sha256") != sha(args.build)
            or authorization.get("manifest_sha256") != sha(args.manifest)
            or authorization.get("preflight_sha256") != sha(args.preflight)):
        raise RuntimeError("authorization must bind the exact build, input manifest and preflight")
    if args.output.exists():
        raise RuntimeError("output directory already exists")
    retry = None
    if args.attempt == 1:
        if args.retry_of or args.retry_reason or args.environment_receipt:
            raise RuntimeError("first attempt cannot specify a retry")
    else:
        if not args.retry_of or not args.retry_reason:
            raise RuntimeError("retry requires its original report and reason")
        previous = json.loads(args.retry_of.read_text())
        if (previous.get("attempt") != 1 or previous.get("run") != args.run
                or previous.get("group") != args.group or previous.get("cpu") != args.cpu
                or previous.get("manifest_sha256") != sha(args.manifest)
                or previous.get("build_sha256") != sha(args.build)):
            raise RuntimeError("retry must match the original complete session identity")
        retry = dict(report=str(args.retry_of.resolve()), report_sha256=sha(args.retry_of), reason=args.retry_reason)
        if args.retry_reason == "stability":
            if previous.get("status") != "complete_unstable" or args.environment_receipt:
                raise RuntimeError("stability retry requires an original session with unstable cells")
        else:
            if not args.environment_receipt:
                raise RuntimeError("environment retry requires a host review receipt")
            review = json.loads(args.environment_receipt.read_text())
            if (review.get("status") != "environment_violation" or not review.get("reason")
                    or review.get("report_sha256") != retry["report_sha256"]
                    or review.get("build_sha256") != previous["build_sha256"]
                    or review.get("raw_sha256") != previous["raw_sha256"]
                    or Path(review["paths"]["report"]).resolve() != args.retry_of.resolve()
                    or Path(review["paths"]["build"]).resolve() != args.build.resolve()
                    or Path(review["paths"]["raw"]).resolve() != Path(previous["raw"]).resolve()
                    or Path(review["paths"]["host"]).resolve() != Path(previous["host_telemetry"]).resolve()
                    or Path(review["paths"]["wsl"]).resolve() != Path(previous["wsl_telemetry"]).resolve()):
                raise RuntimeError("host review receipt does not invalidate the original session")
            for name in ("report", "raw", "build", "host", "wsl"):
                if sha(review["paths"][name]) != review[name + "_sha256"]:
                    raise RuntimeError("environment receipt artifact changed: " + name)
            review_script = review["review_script"]
            if (sha(review_script) != review["review_script_sha256"]
                    or build["harness_files"].get(review_script) != review["review_script_sha256"]):
                raise RuntimeError("environment receipt does not use the fixed review script")
            retry["environment_receipt"] = str(args.environment_receipt.resolve())
            retry["environment_receipt_sha256"] = sha(args.environment_receipt)
        with (args.retry_of.parent / "retry-claimed.json").open("x") as claim:
            json.dump(dict(**retry, output=str(args.output.resolve())), claim, sort_keys=True)
            claim.write("\n")
    args.output.mkdir(parents=True, exist_ok=False)
    cells = [c for c in manifest["cells"] if ("_full" in c["op"]) == (args.group == "full")]
    report = dict(status="running", run=args.run, group=args.group, cpu=args.cpu,
                  attempt=args.attempt, retry=retry, runtime_environment=build["runtime_environment"],
                  manifest_sha256=sha(args.manifest), build_sha256=sha(args.build),
                  preflight_sha256=sha(args.preflight),
                  authorization_sha256=sha(args.authorization),
                  native_mapping_sha256=build["native_mapping_sha256"], main_refs_before=refs,
                  allowed_cpus=sorted(os.sched_getaffinity(0)), uname=list(os.uname()),
                  cpu_siblings=Path(f"/sys/devices/system/cpu/cpu{args.cpu}/topology/thread_siblings_list").read_text().strip(),
                  cpuinfo=Path("/proc/cpuinfo").read_text(),
                  runner_identity=process_identity(os.getpid()),
                  host_telemetry=str(args.host_telemetry.resolve(strict=True)),
                  wsl_telemetry=str(args.wsl_telemetry.resolve(strict=True)), cells=[])
    binary = {"A": build["binaries"]["baseline"]["path"],
              "B": build["binaries"]["candidate"]["path"]}
    with (args.output / "raw.jsonl").open("w") as raw:
        try:
            report["loader_before"] = runtime_dependencies(build, args.cpu)
            require_runtime_dependencies(report["loader_before"])
            report["session_start_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            for index, cell in enumerate(cells):
                path = args.manifest.parent / cell["input"]
                if sha(path) != cell["input_sha256"]:
                    raise RuntimeError("input changed before cell")
                def call(label, mode, count, **fields):
                    argv = [binary[label], mode, cell["op"], str(cell["n"]), str(cell["top"]),
                            str(path), str(cell["alias"]).lower(), str(count)]
                    return invoke(argv, raw, dict(cell=index, input_sha256=cell["input_sha256"],
                                                   label=label, mode=mode, **fields), args.cpu,
                                  build["runtime_environment"])
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
                assessment = stability(blocks)
                report["cells"].append(dict(**cell, blocks=blocks, stability=assessment,
                                            candidate_over_baseline=assessment["median"]))
                (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            report["session_end_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            verify_inputs(args.manifest.parent, manifest)
            verify_build(build, manifest)
            report["loader_after"] = runtime_dependencies(build, args.cpu)
            require_runtime_dependencies(report["loader_after"])
            if report["loader_after"]["loader_config"] != report["loader_before"]["loader_config"]:
                raise RuntimeError("loader configuration changed during run")
            report["main_refs_after"] = main_refs(build)
            if report["main_refs_after"] != refs:
                raise RuntimeError("main identity changed during run")
            if sha(args.manifest) != report["manifest_sha256"] or sha(args.build) != report["build_sha256"]:
                raise RuntimeError("manifest or build receipt changed during run")
            report["status"] = ("complete_unstable" if any(not cell["stability"]["stable"] for cell in report["cells"])
                                else "complete_pending_host_and_review")
        except Exception as error:
            if "session_start_utc" in report:
                report.setdefault("session_end_utc", datetime.datetime.now(datetime.timezone.utc).isoformat())
            report["status"] = "failed"
            report["failure"] = repr(error)
            try:
                verify_inputs(args.manifest.parent, manifest)
                verify_build(build, manifest)
                report["loader_after"] = runtime_dependencies(build, args.cpu)
                require_runtime_dependencies(report["loader_after"])
                report["main_refs_after"] = main_refs(build)
                if report["loader_after"]["loader_config"] != report["loader_before"]["loader_config"] or report["main_refs_after"] != refs:
                    raise RuntimeError("loader configuration or main identity changed during run")
            except Exception as postflight_error:
                report["status"] = "failed"
                report["postflight_failure"] = repr(postflight_error)
            raise
        finally:
            raw.flush()
            report["raw"] = str((args.output / "raw.jsonl").resolve())
            report["raw_sha256"] = sha(args.output / "raw.jsonl")
            (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

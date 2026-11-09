#!/usr/bin/env python3
"""Read-only validation of the registered original 86-cell harness output."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import statistics

SEED = 20261108
MINIMUM_NS = 10_000_000
CALIBRATION_NS = 20_000_000
REPETITIONS = 7
PATHS = ("baseline", "candidate", "gmp")
U64_MAX = (1 << 64) - 1
FULL_SIZES = (1,2,7,8,9,23,24,25,31,32,33,47,48,49,63,64,65,127,128,129,
              191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096)
KEY_SHAPES = ((1,1),(1,64),(2,1),(23,63),(24,63),(25,63),(63,63),(64,63),
              (65,63),(127,63),(128,63),(129,63),(191,63),(192,63),(193,63),
              (255,63),(256,63),(257,63),(511,63),(512,63),(513,63),(1023,63),
              (1024,63),(1025,63),(2048,63),(4096,63))
CELLS = tuple((0,n,64) for n in FULL_SIZES) + tuple(
    (op,n,top) for op in (1,2) for n,top in KEY_SHAPES)
BASE = "4510b46e4010dd287c9cf760f0195f2edc32e1f7"
BASELINE_RECEIPT = "e64a33d921810b456e343de139ccff96b4be484adc93e0cf642229fbc3568fe8"
NATIVE_TREES = dict(baseline="72dc8a5da2cbb7eddcdd26c219d50770e8b73b06",
                    candidate="212dd5d00d4b2159abd4627a6aaec8b16a1157e5")
PROOF_TOOLS = {"verus","rust_verify","z3","vstd.vir","libvstd.rlib","rustup","rustc",
               "llvm","rustc_driver","archive","libverus_builtin.rlib",
               "libverus_builtin_macros.so","libverus_state_machines_macros.so"}
FIELDS = ("op", "n", "top", "path", "kind", "repetition", "argv")
PAYLOAD = ("iterations", "ns", "checksum", "calibration")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mapping_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def strict_json(data):
    def pairs(items):
        result = {}
        for key,value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError("non-finite JSON constant: " + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def integer(value, low, high, name):
    require(type(value) is int and low <= value <= high, "invalid integer: " + name)


def digest(value, length=64):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{%d}" % length, value),
            "invalid digest")


def artifact(row):
    require(isinstance(row, dict) and set(row) == {"path", "sha256"}, "invalid artifact reference")
    digest(row["sha256"])
    require(isinstance(row["path"], str) and PurePosixPath(row["path"]).is_absolute(),
            "artifact requires the frozen absolute Linux path")
    data = Path(row["path"]).read_bytes()
    require(sha(data) == row["sha256"], "artifact drift: " + row["path"])
    return data


def native_tree(files):
    """Compute Git's 100644 blob/tree identity from the complete native inventory."""
    root = {}
    for name,row in files.items():
        parts = PurePosixPath(name).parts
        require(len(parts) >= 2 and parts[0] == "native" and ".." not in parts, "invalid native file name")
        node = root
        for part in parts[1:-1]:
            node = node.setdefault(part, {})
        require(parts[-1] not in node, "duplicate native file")
        node[parts[-1]] = artifact(row)
    def git_hash(kind, data):
        return hashlib.sha1(kind + b" " + str(len(data)).encode() + b"\0" + data).digest()
    def tree(node):
        entries = []
        for name,value in sorted(node.items(), key=lambda item:item[0] + ("/" if isinstance(item[1],dict) else "")):
            directory = isinstance(value, dict)
            mode = b"40000" if directory else b"100644"
            entries.append(mode + b" " + name.encode() + b"\0" +
                           (tree(value) if directory else git_hash(b"blob",value)))
        return git_hash(b"tree",b"".join(entries))
    return tree(root).hex()


def validate_build(data, expected_sha256):
    """The expected digest comes from the independently approved pre-timing receipt."""
    digest(expected_sha256)
    require(sha(data) == expected_sha256, "external frozen build digest mismatch")
    build = strict_json(data)
    require(build["schema"] == "fused-interpolation-bench-build-v1" and
            build["status"] == "static_pass", "not the frozen static-passing build")
    require(build["seed"] == SEED and build["cell_count"] == 86 and
            build["key_shapes"] == [list(pair) for pair in KEY_SHAPES], "registered matrix changed")
    identity = strict_json(artifact(build["identity_receipt"]))
    require(identity["schema"] == "fused-interpolation-identity-v1" and
            identity["status"] == "static_pass", "invalid static identity receipt")
    require(set(identity["sources"]) == {"baseline","candidate"}, "wrong source inventory")
    for label,source in identity["sources"].items():
        digest(source["head"],40);digest(source["tree"],40)
        require(PurePosixPath(source["root"]).is_absolute() and all(
            row["path"] == str(PurePosixPath(source["root"])/name)
            for name,row in source["files"].items()), "source snapshot paths differ from compiler root")
        require(source["native_tree"] == NATIVE_TREES[label] == native_tree(source["files"]),
                "native Git tree mismatch: " + label)
        manifest = {name:row["sha256"] for name,row in source["files"].items()}
        require(mapping_sha(manifest) == source["native_manifest_sha256"], "native manifest mismatch")
    require(identity["sources"]["baseline"]["head"] == BASE, "wrong baseline source")
    require((build["source_head"],build["source_tree"]) ==
            (identity["sources"]["candidate"]["head"],identity["sources"]["candidate"]["tree"]),
            "build/source receipt mismatch")
    require(set(identity["sources"]["baseline"]["files"]) ==
            set(identity["sources"]["candidate"]["files"]), "native inventories differ")
    tools = identity["tools"]
    required_tools = PROOF_TOOLS | {"python","git","ar","objdump","objcopy"}
    require(required_tools <= set(tools), "incomplete tool inventory")
    for row in tools.values():
        artifact(row)
    pin = strict_json(artifact(identity["sources"]["candidate"]["files"]["native/toolchain.json"]))
    require(tools["archive"]["sha256"] == pin["sha256"], "archive differs from native toolchain pin")
    inputs = identity["inputs"]
    required_inputs = {"experiments/arithmetic-precondition-checks-20261108/bench.rs",
                       "experiments/arithmetic-precondition-checks-20261108/measure.py",
                       "experiments/fused-interpolation-20261108/raw_validate.py",
                       "experiments/fused-interpolation-20261108/summarize.py",
                       "experiments/fused-interpolation-20261108/PROTOCOL.md"}
    require(required_inputs <= set(inputs), "incomplete harness/protocol inventory")
    for row in inputs.values():
        artifact(row)
    here = Path(__file__).resolve().parent
    for name in ("raw_validate.py","summarize.py","PROTOCOL.md"):
        require(sha((here/name).read_bytes()) == inputs["experiments/fused-interpolation-20261108/"+name]["sha256"],
                "validator/protocol differs from frozen source")
    require(set(identity["producers"]) == set(build["binaries"]) == {"baseline","candidate"},
            "wrong producer/binary inventory")
    baseline = identity["producers"]["baseline"]
    require(baseline["receipt"]["sha256"] == BASELINE_RECEIPT, "not the accepted 358-item baseline receipt")
    accepted = strict_json(artifact(baseline["receipt"]))
    require(accepted["status"] == "pass" and accepted["library_verified_items"] == 358,
            "baseline producer receipt failed")
    old_tools = accepted["toolchain"]["actual_file_sha256"]
    for name in PROOF_TOOLS-{"archive"}:
        matches = [value for path,value in old_tools.items()
                   if PurePosixPath(path).name == PurePosixPath(tools[name]["path"]).name]
        require(matches == [tools[name]["sha256"]], "tool differs from accepted baseline: "+name)
    require(accepted["toolchain"]["archive_sha256"] == tools["archive"]["sha256"], "baseline archive differs")
    baseline_rust = {name:row["sha256"] for name,row in identity["sources"]["baseline"]["files"].items()
                     if name.endswith(".rs")}
    require(baseline_rust == {name:value for name,value in accepted["source_git"]["source_sha256"].items()
                             if name.startswith("native/") and name.endswith(".rs")}, "baseline Rust source differs")
    for label,producer in identity["producers"].items():
        source = identity["sources"][label]
        require(producer["native_tree"] == source["native_tree"] and
                producer["native_manifest_sha256"] == source["native_manifest_sha256"],
                "producer/source mismatch")
        require(producer["tools_sha256"] == {name:tools[name]["sha256"] for name in PROOF_TOOLS},
                "producer/tool mismatch")
        artifact(producer["receipt"]);artifact(producer["rlib"]);artifact(producer["vir"])
        command = producer["proof"]
        text = (artifact(command["stdout"]) + artifact(command["stderr"])).decode("utf-8")
        summaries = re.findall(r"(?m)^verification results:: (\d+) verified, (\d+) errors(?: .*)?$",text)
        require(command["returncode"] == 0 and len(summaries) == 1 and summaries[0][1] == "0" and
                int(summaries[0][0]) == producer["verified_items"] and
                re.search(r"(?m)^verification results:: \d+ verified, 0 errors$",text),
                "not a complete successful producer proof")
        argv = command["argv"]
        require(all(flag in argv for flag in ("--crate-type","lib","--crate-name","verigmp",
                                             "--no-cheating","--compile","-O")) and
                not any(str(flag).startswith(("--verify-","--no-verify","--external")) for flag in argv),
                "producer command is filtered or lacks required release/proof flags")
        if label == "baseline":
            require(producer["verified_items"] == 358, "wrong reused baseline proof")
            old_command = accepted["producer_reuse"]["original_complete_build_command"]
            require(argv == old_command["argv"] and command["cwd"] == old_command["cwd"] and
                    all(command[stream]["sha256"] == old_command[stream+"_sha256"]
                        for stream in ("stdout","stderr")) and
                    producer["rlib"]["sha256"] == accepted["exports_sha256"]["libverigmp.rlib"] and
                    producer["vir"]["sha256"] == accepted["exports_sha256"]["verigmp.vir"],
                    "reused baseline command/log/export differs")
        else:
            require(command["cwd"] == source["root"] and argv[1] in
                    ("native/lib.rs",source["files"]["native/lib.rs"]["path"]), "proof/source path mismatch")
            require("--num-threads" in argv and argv[argv.index("--num-threads")+1] == "2",
                    "candidate proof thread setting changed")
            expected = [tools["verus"]["path"],argv[1],"--crate-type","lib","--crate-name","verigmp",
                        "--no-cheating","--compile","-O","--num-threads","2","--export",
                        producer["vir"]["path"],"-o",producer["rlib"]["path"]]
            require(argv == expected, "candidate complete proof argv changed")
        row = build["binaries"][label]
        artifact(dict(path=row["path"],sha256=row["sha256"]))
        artifact(dict(path=row["gmp_path"],sha256=row["gmp_sha256"]))
        require(row["library_sha256"] == producer["rlib"]["sha256"], "binary/library mismatch")
        rustup = tools["rustup"]["path"]
        toolchain = "1.99.1-x86_64-unknown-linux-gnu"
        expected = [rustup,"run",toolchain,"rustc",inputs["experiments/arithmetic-precondition-checks-20261108/bench.rs"]["path"],
                    "-O","--edition=2024","-L","dependency="+str(PurePosixPath(tools["verus"]["path"]).parent),
                    "-L","dependency="+str(PurePosixPath(producer["rlib"]["path"]).parent),
                    "--extern","verigmp="+producer["rlib"]["path"],"-o",row["path"]]
        require(row["argv"] == expected, "benchmark compiler argv changed")
        require(row["build_command"]["argv"] == expected and row["build_command"]["returncode"] == 0,
                "benchmark compile receipt mismatch")
        artifact(row["build_command"]["stdout"]);artifact(row["build_command"]["stderr"])
    require(build["binaries"]["baseline"]["gmp_sha256"] == build["binaries"]["candidate"]["gmp_sha256"],
            "GMP identity differs between producers")
    for name in ("correctness","semantic_mutants","domain_alias_capacity","control_identity","host"):
        artifact(identity["gate_receipts"][name])
    return build,identity


def sample_paths(index, repetition):
    paths = ["baseline","candidate"] if repetition % 2 == 0 else ["candidate","baseline"]
    paths.insert((index+repetition)%3,"gmp")
    return paths


def validate_rows(raw, build, cpu):
    lines = [strict_json(line) for line in raw.splitlines()]
    cursor = 0
    retry_count = 0
    calibration_count = 0
    accepted_count = 0
    summaries = []
    def call(key, path, count, kind, repetition):
        nonlocal cursor
        require(cursor+3 <= len(lines), "incomplete invocation/outcome/result triple")
        invocation,outcome,result = lines[cursor:cursor+3]
        cursor += 3
        require(set(invocation) == {"record",*FIELDS,"cpu","timeout_seconds"} and
                invocation["record"] == "invocation", "invalid invocation record")
        require(set(outcome) == {"record",*FIELDS,"returncode","timed_out","stdout","stderr","stdout_hex","stderr_hex"}
                and outcome["record"] == "outcome", "invalid outcome record")
        require(set(result) == {"record",*FIELDS,*PAYLOAD} and result["record"] == "result", "invalid result record")
        op,n,top = key
        binary = build["binaries"]["baseline" if path in ("baseline","gmp") else "candidate"]["path"]
        argv = [binary,str(op),str(n),str(top),str(SEED),str(path == "gmp").lower(),str(count),"registered"]
        expected = dict(op=op,n=n,top=top,path=path,kind=kind,repetition=repetition,argv=argv)
        for row in (invocation,outcome,result):
            require({name:row[name] for name in FIELDS} == expected, "cell/path/count/order/argv mismatch")
            for name in ("op","n","top","repetition"):
                require(type(row[name]) is int, "non-integer invocation metadata")
        require(type(invocation["cpu"]) is int and invocation["cpu"] == cpu and
                type(invocation["timeout_seconds"]) is int and invocation["timeout_seconds"] == 180,
                "CPU/timeout differs from registered invocation")
        require(type(outcome["returncode"]) is int and outcome["returncode"] == 0 and
                outcome["timed_out"] is False, "failed or timed-out invocation")
        for stream in ("stdout","stderr"):
            value = outcome[stream+"_hex"]
            require(isinstance(value,str), "non-string raw stream")
            data = bytes.fromhex(value)
            require(data.hex() == value and data.decode(errors="replace") == outcome[stream], "raw stream encoding mismatch")
        payload = strict_json(bytes.fromhex(outcome["stdout_hex"]).decode("utf-8"))
        require(isinstance(payload,dict) and set(payload) == set(PAYLOAD) and
                result == dict(payload,**expected,record="result"), "stdout/result payload mismatch")
        integer(payload["iterations"],1,U64_MAX,"iterations")
        integer(payload["ns"],1,(1<<128)-1,"ns")
        integer(payload["checksum"],0,U64_MAX,"checksum")
        ladder = payload["calibration"]
        require(type(ladder) is list, "invalid calibration ladder")
        if kind == "calibration":
            require(ladder and len(ladder) <= 64, "missing/oversized calibration ladder")
            for index,pair in enumerate(ladder):
                require(type(pair) is list and len(pair) == 2, "invalid calibration step")
                integer(pair[0],1,U64_MAX,"calibration iterations")
                integer(pair[1],0,(1<<128)-1,"calibration ns")
                require(pair[0] == 1 << index, "calibration does not double from one")
                require((pair[1] >= CALIBRATION_NS) == (index == len(ladder)-1), "calibration stop rule changed")
            require(ladder[-1] == [payload["iterations"],payload["ns"]], "calibration terminal mismatch")
        else:
            require(ladder == [] and payload["iterations"] == count, "sample/count/calibration mismatch")
        return payload
    for index,key in enumerate(CELLS):
        counts = {}
        groups = {path:[] for path in PATHS}
        checksums = set()
        for path in PATHS:
            row = call(key,path,0,"calibration",-1)
            counts[path] = row["iterations"]
            checksums.add(row["checksum"])
            calibration_count += 1
        for repetition in range(REPETITIONS):
            for path in sample_paths(index,repetition):
                row = call(key,path,counts[path],"sample",repetition)
                checksums.add(row["checksum"])
                while row["ns"] < MINIMUM_NS:
                    counts[path] *= 2
                    integer(counts[path],1,U64_MAX,"retry iterations")
                    row = call(key,path,counts[path],"sample-retry",repetition)
                    checksums.add(row["checksum"])
                    retry_count += 1
                groups[path].append(row["ns"]/row["iterations"])
                accepted_count += 1
        require(len(checksums) == 1, "cell checksum differs in calibration/sample/retry/GMP")
        medians = {path:statistics.median(groups[path]) for path in PATHS}
        summaries.append(dict(op=key[0],n=key[1],top=key[2],median_ns=medians,
            candidate_over_baseline=medians["candidate"]/medians["baseline"],
            candidate_over_gmp=medians["candidate"]/medians["gmp"]))
    require(cursor == len(lines), "extra or reordered records after the exact 86-cell schedule")
    require(calibration_count == 258 and accepted_count == 1806, "incomplete registered sample matrix")
    return summaries,dict(cells=86,calibrations=calibration_count,accepted_samples=accepted_count,
                          retained_retries=retry_count,invocations=cursor//3,
                          exact_order=True,stdout_payload_bound=True,exact_argv_bound=True)


def validate_report(report, raw, build, build_sha256):
    require(report["status"] == "pass" and report["seed"] == SEED and report["cpu"] == 8,
            "not a successful registered run")
    require(isinstance(report["run_id"],str) and report["run_id"], "missing run identity")
    require(report["build_sha256"] == build_sha256 and report["build"] == build,
            "embedded build differs from external frozen receipt")
    require(report["minimum_sample_ns"] == MINIMUM_NS and report["repetitions"] == REPETITIONS,
            "sampling constants changed")
    require(report["raw_sha256"] == sha(raw), "raw-file digest mismatch")
    summaries,receipt = validate_rows(raw,build,report["cpu"])
    require(report["summaries"] == summaries, "reported medians/ratios/order differ from recomputed raw")
    return summaries,receipt

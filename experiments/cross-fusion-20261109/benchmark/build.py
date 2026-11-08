#!/usr/bin/env python3
"""Build both benchmarks from separately verified source-bound library pairs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

COMMITS = {"baseline": "2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba",
           "candidate": "d6a17984c758dab825339d0eab8562f21c5fa24b"}
EXPECTED_MAIN = "bf1bc40946967581852dd3b675db8140d757574e"
EXPECTED_NATIVE_TREE = "72dc8a5da2cbb7eddcdd26c219d50770e8b73b06"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def verify_evidence(root, commit):
    summary = load(root / "summary.json")
    if summary["commit"] != commit or not summary["identities_stable"] or summary["proof_summary"][1] != "0":
        raise RuntimeError("missing clean source-bound verification")
    for name in ("source", "tools", "pair"):
        if load(root / (name + "-before.json")) != load(root / (name + "-after.json")):
            raise RuntimeError(name + " identity changed during proof")
    for name in ("rlib", "vir"):
        path = root / ("libverigmp.rlib" if name == "rlib" else "verigmp.vir")
        if sha(path) != summary["library_pair"][name + "_sha256"]:
            raise RuntimeError(name + " differs from verified artifact")
    if sha(root / "source.tar") != summary["source_archive_sha256"]:
        raise RuntimeError("source archive changed")
    sources = load(root / "source-before.json")
    for name, row in sources.items():
        if sha(root / "source-snapshot" / name) != row["sha256"]:
            raise RuntimeError("source snapshot changed: " + name)
    commands = [json.loads(line) for line in (root / "commands.jsonl").read_text().splitlines()]
    gates = [row for row in commands if row["name"] == "library-gate"]
    if len(gates) != 1 or gates[0]["exit_code"] != 0 or gates[0]["timeout"]:
        raise RuntimeError("library gate did not pass")
    gate = gates[0]
    if not all(flag in gate["argv"] for flag in ("--no-cheating", "--compile", "-O")):
        raise RuntimeError("library gate flags are incomplete")
    if sha(root / gate["log"]) != gate["log_sha256"]:
        raise RuntimeError("proof log changed")
    tools = load(root / "tools-before.json")
    for path, row in tools.items():
        if sha(path) != row["sha256"]:
            raise RuntimeError("proof tool changed: " + path)
    return summary, tools


def run(argv):
    return subprocess.run([str(x) for x in argv], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout.decode()


def source_mapping(git, roots, evidence):
    main_tip = run([git, "rev-parse", "refs/heads/main"]).strip()
    remote_tip = run([git, "rev-parse", "refs/remotes/origin/main"]).strip()
    if main_tip != EXPECTED_MAIN or remote_tip != main_tip:
        raise RuntimeError("refresh the pinned main identity before building")
    subprocess.run([git, "merge-base", "--is-ancestor", COMMITS["baseline"], main_tip], check=True)
    trees = {label: run([git, "rev-parse", commit + ":native"]).strip()
             for label, commit in dict(COMMITS, main=main_tip).items()}
    if trees["baseline"] != EXPECTED_NATIVE_TREE or trees["main"] != trees["baseline"]:
        raise RuntimeError("main native tree differs from the proof source")
    mappings = {}
    for label in ("baseline", "candidate"):
        entries = subprocess.run([git, "ls-tree", "-rz", "--full-tree", COMMITS[label], "native"],
                                 check=True, capture_output=True).stdout.split(b"\0")
        manifest = load(roots[label] / "source-before.json")
        rows = {}
        for entry in filter(None, entries):
            info, raw_name = entry.split(b"\t", 1)
            mode, kind, oid = info.decode().split()
            name = raw_name.decode()
            if mode != "100644" or kind != "blob":
                raise RuntimeError("unexpected native tree entry: " + name)
            data = subprocess.run([git, "cat-file", "blob", oid], check=True, capture_output=True).stdout
            digest = hashlib.sha256(data).hexdigest()
            if name not in manifest or digest != manifest[name]["sha256"] or (roots[label] / "source-snapshot" / name).read_bytes() != data:
                raise RuntimeError("proof snapshot does not match committed native blob: " + name)
            rows[name] = dict(git_blob=oid, sha256=digest, bytes=len(data))
        if set(rows) != {name for name in manifest if name.startswith("native/")}:
            raise RuntimeError("native source manifest and tree do not match")
        mappings[label] = rows
    changed = sorted(name for name in set(mappings["baseline"]) | set(mappings["candidate"])
                     if mappings["baseline"].get(name) != mappings["candidate"].get(name))
    if changed != ["native/verified/fast_words.rs"]:
        raise RuntimeError("candidate native source change differs from the planned optimization")
    return dict(main_tip=main_tip, origin_main_tip=remote_tip, native_trees=trees,
                proof_source_commits=COMMITS, source_archives={label: evidence[label][0]["source_archive_sha256"]
                                                               for label in COMMITS},
                source_manifests={label: sha(roots[label] / "source-before.json") for label in COMMITS},
                changed_native_files=changed, files=mappings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-evidence", type=Path, required=True)
    parser.add_argument("--candidate-evidence", type=Path, required=True)
    parser.add_argument("--rustc", type=Path, required=True)
    parser.add_argument("--verus-deps", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    roots = {"baseline": args.baseline_evidence.resolve(), "candidate": args.candidate_evidence.resolve()}
    evidence = {label: verify_evidence(root, COMMITS[label]) for label, root in roots.items()}
    if evidence["baseline"][1] != evidence["candidate"][1]:
        raise RuntimeError("proof tool identities differ")
    rustc = args.rustc.resolve()
    # A rustup proxy is allowed only if its actual compiler is in the frozen tool inventory.
    actual_rustc = Path(run(["rustup", "which", "rustc"]).strip()).resolve()
    tools = evidence["candidate"][1]
    if str(actual_rustc) not in tools or sha(actual_rustc) != tools[str(actual_rustc)]["sha256"]:
        raise RuntimeError("benchmark compiler differs from proof compiler")
    if rustc != actual_rustc and rustc.name != "rustup":
        raise RuntimeError("use the proof compiler or rustup proxy")
    source = Path(__file__).resolve().parent / "bench.rs"
    source_hash = sha(source)
    git = shutil.which("git")
    harness_commit = run([git, "rev-parse", "HEAD"]).strip()
    mapping = source_mapping(git, roots, evidence)
    harness_files = ("bench.rs", "prepare.py", "measure.py", "verify.py", "build.py",
                     "baseline_capture.py", "PROTOCOL.md", "host_monitor.ps1")
    harness = {}
    for name in harness_files:
        path = source.parent / name
        relative = "experiments/cross-fusion-20261109/benchmark/" + name
        if subprocess.run([git, "show", harness_commit + ":" + relative], check=True,
                          capture_output=True).stdout != path.read_bytes():
            raise RuntimeError("harness differs from committed source: " + name)
        harness[str(path)] = sha(path)
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    mapping_path = output / "baseline-main-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    cc = Path(shutil.which("cc")).resolve()
    linker = Path(run([cc, "-print-prog-name=ld"]).strip()).resolve()
    compiler_identity = dict(rustc_path=str(actual_rustc), rustc_sha256=sha(actual_rustc),
                             version=run([args.rustc, "--version", "--verbose"]),
                             sysroot=run([args.rustc, "--print", "sysroot"]).strip(),
                             frozen_tools_sha256=sha(roots["candidate"] / "tools-before.json"),
                             cc_path=str(cc), cc_sha256=sha(cc), cc_version=run([cc, "--version"]),
                             linker_path=str(linker), linker_sha256=sha(linker),
                             linker_version=run([linker, "--version"]))
    build = dict(version=1, harness_commit=harness_commit, harness_files=harness,
                 native_mapping=str(mapping_path), native_mapping_sha256=sha(mapping_path),
                 compiler_identity=compiler_identity, binaries={})
    linked = None
    for label in ("baseline", "candidate"):
        root = roots[label]
        target = output / (label + "-bench")
        link_map = output / (label + "-link.map")
        rlib, vir, receipt = root / "libverigmp.rlib", root / "verigmp.vir", root / "summary.json"
        command = [str(args.rustc), "--edition=2021", "-O", "-C", f"linker={cc}",
                   "-C", f"link-arg=-Wl,-Map={link_map}", str(source), "--extern", f"verigmp={rlib}",
                   "-L", f"dependency={args.verus_deps.resolve()}", "-o", str(target)]
        compile_log = run(command)
        link_inputs = {}
        for name in re.findall(r"^LOAD (/\S+)$", link_map.read_text(), re.M):
            path = Path(name)
            if path.is_file() and not str(path).startswith("/tmp/rustc"):
                link_inputs[str(path)] = sha(path)
        if not link_inputs:
            raise RuntimeError("linker map does not identify permanent link inputs")
        ldd = run(["ldd", target])
        dependencies = {}
        for path in re.findall(r"(?:=>\s+|^\s*)(/\S+)\s+\(0x[0-9a-f]+\)", ldd, re.M):
            dependencies[path] = sha(path)
        if not any("libgmp.so" in path for path in dependencies):
            raise RuntimeError("GMP shared library identity missing")
        if linked is not None and dependencies != linked:
            raise RuntimeError("benchmark binaries resolve different shared libraries")
        linked = dependencies
        (output / (label + "-symbols.txt")).write_text(run(["nm", "-n", "-C", target]))
        (output / (label + "-disassembly.txt")).write_text(run(["objdump", "-d", "-C", "--no-show-raw-insn", target]))
        (output / (label + "-relocations.txt")).write_text(run(["readelf", "-rW", target]))
        build["binaries"][label] = dict(commit=COMMITS[label], same_source_verified=True,
            path=str(target), path_sha256=sha(target), rlib=str(rlib), rlib_sha256=sha(rlib),
            vir=str(vir), vir_sha256=sha(vir), proof_receipt=str(receipt), proof_receipt_sha256=sha(receipt),
            harness=str(source), harness_sha256=source_hash, compiler_identity=compiler_identity,
            command=command, compile_output=compile_log, ldd=ldd, dependencies=dependencies,
            link_map=str(link_map), link_map_sha256=sha(link_map), link_inputs=link_inputs,
            symbols=str(output / (label + "-symbols.txt")),
            symbols_sha256=sha(output / (label + "-symbols.txt")),
            disassembly=str(output / (label + "-disassembly.txt")),
            disassembly_sha256=sha(output / (label + "-disassembly.txt")),
            relocations=str(output / (label + "-relocations.txt")),
            relocations_sha256=sha(output / (label + "-relocations.txt")))
    if sha(source) != source_hash:
        raise RuntimeError("benchmark source changed during compilation")
    if {label: verify_evidence(root, COMMITS[label]) for label, root in roots.items()} != evidence:
        raise RuntimeError("proof identity changed during benchmark build")
    if sha(cc) != compiler_identity["cc_sha256"] or sha(linker) != compiler_identity["linker_sha256"]:
        raise RuntimeError("linker identity changed during benchmark build")
    if any(sha(path) != digest for path, digest in harness.items()):
        raise RuntimeError("harness changed during benchmark build")
    if source_mapping(git, roots, evidence) != mapping:
        raise RuntimeError("main or native source identity changed during benchmark build")
    build["environment"] = {key: os.environ.get(key) for key in
                             ("PATH", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN", "LD_LIBRARY_PATH")}
    path = output / "build.json"
    path.write_text(json.dumps(build, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(build=str(path), sha256=sha(path))))


if __name__ == "__main__":
    main()

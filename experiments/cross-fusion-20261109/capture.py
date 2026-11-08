#!/usr/bin/env python3
"""Capture a same-source Verus/optimized-build and its independent checks."""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile

if len(sys.argv) != 2:
    raise SystemExit("usage: capture.py NEW_OUTPUT_DIRECTORY")
out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
logs = out / "logs"
logs.mkdir()
command_log = out / "commands.jsonl"
checkout = pathlib.Path.cwd()
env = dict(os.environ)
env_record = {key: env.get(key) for key in
              ("PATH", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN", "LD_LIBRARY_PATH", "GIT_DIR", "GIT_WORK_TREE")}
(out / "environment.json").write_text(json.dumps(env_record, indent=2, sort_keys=True) + "\n")


def sha(path):
    with open(path, "rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def record(name, command, cwd, code, log, timeout=False, stdout_destination=None):
    row = {"name": name, "argv": [str(arg) for arg in command], "cwd": str(cwd),
           "exit_code": code, "timeout": timeout, "log": str(log.relative_to(out)),
           "log_sha256": sha(log)}
    if stdout_destination is not None:
        row["stdout_destination"] = str(stdout_destination)
        row["stdout_sha256"] = sha(stdout_destination)
    with command_log.open("a") as target:
        target.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"{name}: exit={code}" + (" timeout" if timeout else ""), flush=True)


def run(name, command, cwd=checkout, timeout=120, expected=0):
    command = [str(arg) for arg in command]
    log = logs / (name + ".log")
    try:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        log.write_bytes(result.stdout)
        record(name, command, cwd, result.returncode, log)
    except subprocess.TimeoutExpired as error:
        log.write_bytes(error.stdout or b"")
        record(name, command, cwd, None, log, timeout=True)
        raise
    if expected is not None and result.returncode != expected:
        raise RuntimeError(f"{name}: expected exit {expected}, got {result.returncode}")
    return result


def manifest(root):
    return {str(path.relative_to(root)): {"sha256": sha(path), "bytes": path.stat().st_size}
            for path in sorted(root.rglob("*")) if path.is_file()}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


git = shutil.which("git")
verus = pathlib.Path(shutil.which("verus")).resolve()
rustc = shutil.which("rustc")
if not all((git, verus, rustc)):
    raise RuntimeError("git, verus and rustc must be on PATH")
head = run("head-before", [git, "rev-parse", "HEAD"]).stdout.decode().strip()
tree = run("tree-before", [git, "rev-parse", head + "^{tree}"]).stdout.decode().strip()
run("selected-git-tree", [git, "ls-tree", "-r", head, "--", "native", "experiments/cross-fusion-20261109"])
archive = out / "source.tar"
archive_command = [git, "archive", "--format=tar", head, "native", "experiments/cross-fusion-20261109"]
archive_log = logs / "source-archive.log"
with archive.open("wb") as target:
    result = subprocess.run(archive_command, cwd=checkout, env=env, stdout=target,
                            stderr=subprocess.PIPE, timeout=120)
archive_log.write_bytes(result.stderr)
record("source-archive", archive_command, checkout, result.returncode, archive_log, stdout_destination=archive)
if result.returncode:
    raise RuntimeError("git archive failed")
snapshot = out / "source-snapshot"
snapshot.mkdir()
with tarfile.open(archive) as source:
    source.extractall(snapshot, filter="data")
harness = snapshot / "experiments/cross-fusion-20261109"
if pathlib.Path(__file__).read_bytes() != (harness / "capture.py").read_bytes():
    raise RuntimeError("collector differs from the committed snapshot")
sources_before = manifest(snapshot)
dump(out / "source-before.json", sources_before)

rustc_actual = pathlib.Path(run("rustc-path", ["rustup", "which", "rustc"]).stdout.decode().strip()).resolve()
sysroot = pathlib.Path(run("rustc-sysroot", [rustc, "--print", "sysroot"]).stdout.decode().strip()).resolve()
version_commands = {"verus-version": [verus, "--version"], "rustc-version": [rustc, "--version", "--verbose"],
                    "z3-version": [verus.parent / "z3", "--version"],
                    "python-version": [sys.executable, "--version"], "git-version": [git, "--version"],
                    "objdump-version": ["objdump", "--version"], "nm-version": ["nm", "--version"],
                    "readelf-version": ["readelf", "--version"], "platform": ["uname", "-a"]}
for name, command in version_commands.items():
    run(name, command)

tool_paths = {pathlib.Path(shutil.which(name)).resolve() for name in
              ("git", "rustup", "rustc", "objdump", "nm", "readelf", "python3", "ldd", "uname")}
tool_paths.add(rustc_actual)
for name in ("verus", "rust_verify", "z3", "vstd.vir", "libvstd.rlib",
             "libverus_builtin.rlib", "libverus_builtin_macros.so", "libverus_state_machines_macros.so"):
    tool_paths.add((verus.parent / name).resolve())
tool_paths.update(path.resolve() for path in (sysroot / "lib").glob("*.so*"))
tool_paths.update(path.resolve() for path in (sysroot / "lib/rustlib/x86_64-unknown-linux-gnu/lib").glob("*.rlib"))
tool_paths.update(path.resolve() for path in (sysroot / "lib/rustlib/x86_64-unknown-linux-gnu/lib").glob("*.so"))
for label, executable in (("verus", verus), ("rust-verify", verus.parent / "rust_verify"),
                          ("z3", verus.parent / "z3"), ("rustc", rustc_actual),
                          ("python", pathlib.Path(sys.executable)), ("objdump", pathlib.Path(shutil.which("objdump"))),
                          ("readelf", pathlib.Path(shutil.which("readelf"))), ("nm", pathlib.Path(shutil.which("nm"))),
                          ("git", pathlib.Path(git))):
    linked = run("ldd-" + label, ["ldd", executable]).stdout.decode(errors="replace")
    for match in re.finditer(r"(?:=>\s+|^\s*)(/\S+)\s+\(0x[0-9a-f]+\)", linked, re.M):
        tool_paths.add(pathlib.Path(match[1]).resolve())


def tool_manifest():
    return {str(path): {"sha256": sha(path), "bytes": path.stat().st_size}
            for path in sorted(tool_paths)}


print("Hashing tool dependencies before verification", flush=True)
tools_before = tool_manifest()
dump(out / "tools-before.json", tools_before)
rlib = out / "libverigmp.rlib"
vir = out / "verigmp.vir"
gate = run("library-gate", [verus, "native/lib.rs", "--crate-name", "verigmp", "--crate-type", "lib",
                           "--export", vir, "--compile", "-O", "-o", rlib,
                           "--no-cheating", "--num-threads", "2"], cwd=snapshot, timeout=600)
matches = re.findall(r"verification results:: (\d+) verified, (\d+) errors", gate.stdout.decode())
if len(matches) != 1 or int(matches[0][0]) == 0 or matches[0][1] != "0":
    raise RuntimeError("library proof did not report a successful verification summary")
pair_before = {"rlib_sha256": sha(rlib), "vir_sha256": sha(vir)}
dump(out / "pair-before.json", pair_before)

runner = out / "oracle-runner"
run("compile-oracle", [rustc, "--edition=2021", "-O", harness / "oracle_runner.rs",
                       "--extern", "verigmp=" + str(rlib), "-L", "dependency=" + str(verus.parent),
                       "-o", runner], cwd=snapshot)
oracle = run("oracle", [sys.executable, harness / "oracle.py", runner], cwd=snapshot, timeout=600)
oracle_data = json.loads(oracle.stdout)
dump(out / "oracle.json", {"identity": {**pair_before, "runner_sha256": sha(runner), "commit": head},
                            "result": oracle_data})
negative = run("negative-alias", [rustc, "--edition=2021", harness / "alias_negative.rs", "--extern",
                                 "verigmp=" + str(rlib), "-L", "dependency=" + str(verus.parent),
                                 "-o", out / "alias-negative"], cwd=snapshot, expected=None)
if negative.returncode == 0 or negative.stdout.decode().count("error[E0502]") != 2:
    raise RuntimeError("expected two Rust E0502 mutable alias rejections")
fast_words_sha = sources_before["native/verified/fast_words.rs"]["sha256"]
run("mutations", [sys.executable, harness / "mutations.py", out / "mutations", head,
                  fast_words_sha, rlib, vir], cwd=snapshot, timeout=600)
run("objdump", ["objdump", "-d", "-C", "--no-show-raw-insn", runner], cwd=snapshot)
run("symbols", ["nm", "-n", "-C", runner], cwd=snapshot)
run("relocations", ["readelf", "-rW", runner], cwd=snapshot)
codegen = run("codegen", [sys.executable, harness / "codegen.py", logs / "objdump.log",
                           logs / "symbols.log", logs / "relocations.log", sha(runner)], cwd=snapshot)
dump(out / "codegen.json", {"identity": {**pair_before, "commit": head}, "result": json.loads(codegen.stdout)})

print("Hashing source and tool dependencies after verification", flush=True)
sources_after = manifest(snapshot)
tools_after = tool_manifest()
dump(out / "source-after.json", sources_after)
dump(out / "tools-after.json", tools_after)
head_after = run("head-after", [git, "rev-parse", "HEAD"]).stdout.decode().strip()
tree_after = run("tree-after", [git, "rev-parse", head_after + "^{tree}"]).stdout.decode().strip()
pair_after = {"rlib_sha256": sha(rlib), "vir_sha256": sha(vir)}
dump(out / "pair-after.json", pair_after)
if sources_before != sources_after or tools_before != tools_after or pair_before != pair_after:
    raise RuntimeError("source, tool or compiled-pair identity changed during collection")
if (head, tree) != (head_after, tree_after):
    raise RuntimeError("worktree commit or tree changed during collection")
dump(out / "summary.json", {"commit": head, "tree": tree, "source_archive_sha256": sha(archive),
                            "fast_words_sha256": fast_words_sha, "library_pair": pair_before,
                            "runner_sha256": sha(runner), "source_files": len(sources_before),
                            "tool_files": len(tools_before), "proof_summary": matches[0],
                            "oracle_cases": oracle_data["cases"], "negative_alias_errors": 2,
                            "semantic_mutations": 7, "identities_stable": True})
artifacts = manifest(out)
dump(out / "artifacts.json", artifacts)
print("Completed: stable source, tools, compiled pair, oracle, mutations and codegen", flush=True)

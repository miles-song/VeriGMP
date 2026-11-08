#!/usr/bin/env python3
"""Bind a fresh baseline proof and optimized library to immutable inputs."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

BASELINE = "2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba"
SCRIPT = "experiments/cross-fusion-20261109/benchmark/baseline_capture.py"


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifest(paths):
    return {str(path): {"sha256": sha(path), "bytes": path.stat().st_size}
            for path in sorted(paths)}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: baseline_capture.py NEW_OUTPUT_DIRECTORY")
    checkout = Path.cwd()
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    logs = out / "logs"
    logs.mkdir()
    env = dict(os.environ)
    dump(out / "environment.json", {key: env.get(key) for key in
         ("PATH", "CARGO_HOME", "RUSTUP_HOME", "RUSTUP_TOOLCHAIN", "LD_LIBRARY_PATH", "GIT_DIR", "GIT_WORK_TREE")})

    def run(name, argv, cwd=checkout, timeout=120, stdout_file=None):
        argv = [str(arg) for arg in argv]
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
            stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
        except subprocess.TimeoutExpired as error:
            stdout, stderr, code, timed_out = error.stdout or b"", error.stderr or b"", None, True
        log = logs / (name + ".log")
        log.write_bytes(stdout + stderr if stdout_file is None else stderr)
        if stdout_file is not None:
            stdout_file.write_bytes(stdout)
        row = dict(name=name, argv=argv, cwd=str(cwd), exit_code=code, timeout=timed_out,
                   started_utc=started, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   log=str(log.relative_to(out)), log_sha256=sha(log))
        if stdout_file is not None:
            row.update(stdout_destination=str(stdout_file), stdout_sha256=sha(stdout_file))
        with (out / "commands.jsonl").open("a") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
        print(f"{name}: exit={code} timeout={timed_out}", flush=True)
        if code != 0 or timed_out:
            raise RuntimeError("command failed: " + name)
        return stdout

    git = shutil.which("git")
    verus = Path(shutil.which("verus")).resolve()
    rustc = shutil.which("rustc")
    head = run("collector-head-before", [git, "rev-parse", "HEAD"]).decode().strip()
    if run("collector-source", [git, "show", head + ":" + SCRIPT]) != Path(__file__).read_bytes():
        raise RuntimeError("collector must match its committed source")
    collector_before = sha(Path(__file__))
    tree = run("baseline-tree", [git, "rev-parse", BASELINE + "^{tree}"]).decode().strip()
    native_tree = run("baseline-native-tree", [git, "rev-parse", BASELINE + ":native"]).decode().strip()
    run("baseline-git-files", [git, "ls-tree", "-r", BASELINE, "--", "native"])
    archive = out / "source.tar"
    run("source-archive", [git, "archive", "--format=tar", BASELINE, "native"], stdout_file=archive)
    archive_before = sha(archive)
    snapshot = out / "source-snapshot"
    snapshot.mkdir()
    with tarfile.open(archive) as source:
        source.extractall(snapshot, filter="data")

    def source_manifest():
        return {str(path.relative_to(snapshot)): row for path, row in
                ((path, {"sha256": sha(path), "bytes": path.stat().st_size})
                 for path in sorted(snapshot.rglob("*")) if path.is_file())}

    sources_before = source_manifest()
    dump(out / "source-before.json", sources_before)
    actual_rustc = Path(run("rustc-path", ["rustup", "which", "rustc"]).decode().strip()).resolve()
    sysroot = Path(run("rustc-sysroot", [rustc, "--print", "sysroot"]).decode().strip()).resolve()
    for name, command in {
        "verus-version": [verus, "--version"], "rustc-version": [rustc, "--version", "--verbose"],
        "z3-version": [verus.parent / "z3", "--version"], "python-version": [sys.executable, "--version"],
        "git-version": [git, "--version"], "objdump-version": ["objdump", "--version"],
        "nm-version": ["nm", "--version"], "readelf-version": ["readelf", "--version"],
        "platform": ["uname", "-a"],
    }.items():
        run(name, command)
    tool_paths = {Path(shutil.which(name)).resolve() for name in
                  ("git", "rustup", "rustc", "objdump", "nm", "readelf", "python3", "ldd", "uname")}
    tool_paths.add(actual_rustc)
    for name in ("verus", "rust_verify", "z3", "vstd.vir", "libvstd.rlib", "libverus_builtin.rlib",
                 "libverus_builtin_macros.so", "libverus_state_machines_macros.so"):
        tool_paths.add((verus.parent / name).resolve())
    tool_paths.update(path.resolve() for path in (sysroot / "lib").glob("*.so*"))
    tool_paths.update(path.resolve() for path in (sysroot / "lib/rustlib/x86_64-unknown-linux-gnu/lib").glob("*.rlib"))
    tool_paths.update(path.resolve() for path in (sysroot / "lib/rustlib/x86_64-unknown-linux-gnu/lib").glob("*.so"))
    for label, executable in (("verus", verus), ("rust-verify", verus.parent / "rust_verify"),
                              ("z3", verus.parent / "z3"), ("rustc", actual_rustc),
                              ("python", Path(sys.executable)), ("objdump", Path(shutil.which("objdump"))),
                              ("readelf", Path(shutil.which("readelf"))), ("nm", Path(shutil.which("nm"))),
                              ("git", Path(git))):
        linked = run("ldd-" + label, ["ldd", executable]).decode(errors="replace")
        for match in re.finditer(r"(?:=>\s+|^\s*)(/\S+)\s+\(0x[0-9a-f]+\)", linked, re.M):
            tool_paths.add(Path(match[1]).resolve())
    tools_before = manifest(tool_paths)
    dump(out / "tools-before.json", tools_before)
    rlib, vir = out / "libverigmp.rlib", out / "verigmp.vir"
    gate = run("library-gate", [verus, "native/lib.rs", "--crate-name", "verigmp", "--crate-type", "lib",
               "--export", vir, "--compile", "-O", "-o", rlib, "--no-cheating", "--num-threads", "2"],
               cwd=snapshot, timeout=900)
    matches = re.findall(rb"verification results:: (\d+) verified, (\d+) errors", gate)
    if len(matches) != 1 or matches[0] != (b"358", b"0"):
        raise RuntimeError("unexpected verification summary")
    pair_before = {"rlib_sha256": sha(rlib), "vir_sha256": sha(vir)}
    dump(out / "pair-before.json", pair_before)
    sources_after = source_manifest()
    tools_after = manifest(tool_paths)
    pair_after = {"rlib_sha256": sha(rlib), "vir_sha256": sha(vir)}
    dump(out / "source-after.json", sources_after)
    dump(out / "tools-after.json", tools_after)
    dump(out / "pair-after.json", pair_after)
    head_after = run("collector-head-after", [git, "rev-parse", "HEAD"]).decode().strip()
    if (sources_before != sources_after or tools_before != tools_after or pair_before != pair_after
            or head != head_after or sha(archive) != archive_before or sha(Path(__file__)) != collector_before):
        raise RuntimeError("identity changed during proof")
    dump(out / "summary.json", dict(commit=BASELINE, tree=tree, native_tree=native_tree,
         collector_commit=head, collector_sha256=collector_before, source_archive_sha256=archive_before,
         source_files=len(sources_before), tool_files=len(tools_before), library_pair=pair_before,
         proof_summary=["358", "0"], identities_stable=True))
    dump(out / "artifacts.json", {str(path.relative_to(out)): row for path, row in
         ((p, {"sha256": sha(p), "bytes": p.stat().st_size}) for p in sorted(out.rglob("*")) if p.is_file())})
    print("Completed baseline proof and source/tool stability checks", flush=True)


if __name__ == "__main__":
    main()

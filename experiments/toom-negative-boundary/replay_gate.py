"""Freeze and replay the runtime-only Toom boundary oracle; no measurements."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FEATURE = Path(__file__).resolve().parent
TOOL_NAMES = ("verus", "rust_verify", "z3", "vstd.vir", "libvstd.rlib",
              "libverus_builtin.rlib", "libverus_builtin_macros.so",
              "libverus_state_machines_macros.so")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): digest(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(*args: str) -> str:
    windows_git = Path("/mnt/c/Program Files/Git/cmd/git.exe")
    executable = str(windows_git) if windows_git.exists() else "git"
    return subprocess.check_output([executable, *args], cwd=ROOT, text=True, timeout=30).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--cargo-home", type=Path, required=True)
    args = parser.parse_args()
    out, deps, cargo_home = args.out.resolve(), args.deps.resolve(), args.cargo_home.resolve()
    if out == ROOT or ROOT in out.parents:
        raise RuntimeError("output must be outside the worktree")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("freeze requires a clean tracked and untracked worktree")
    commit, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    out.mkdir(parents=True, exist_ok=False)
    source = out / "source"
    source.mkdir()
    shutil.copytree(ROOT / "native", source / "native")
    shutil.copytree(FEATURE, source / "experiments" / FEATURE.name,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("worktree changed during freeze")

    native = source / "native"
    feature = source / "experiments" / FEATURE.name
    pin = json.loads((native / "toolchain.json").read_text())
    verifier = deps / "verus" / "verus-x86-linux" / "verus"
    archive = deps / "verus-download" / pin["archive"]
    if digest(archive) != pin["sha256"]:
        raise RuntimeError("pinned verifier archive mismatch")
    with zipfile.ZipFile(archive) as bundle:
        hashes = {}
        for name in TOOL_NAMES:
            expected = hashlib.sha256(bundle.read("verus-x86-linux/" + name)).hexdigest()
            actual = digest(verifier.parent / name)
            if actual != expected:
                raise RuntimeError("pinned verifier component mismatch: " + name)
            hashes[name] = actual
    env = os.environ.copy()
    selected_env = {"CARGO_HOME": str(cargo_home), "RUSTUP_HOME": str(deps / "rustup"),
                    "RUSTUP_TOOLCHAIN": pin["rust_toolchain"],
                    "PATH": str(cargo_home / "bin") + os.pathsep + env["PATH"]}
    env.update(selected_env)
    rustc = cargo_home / "bin" / "rustc"
    report = {"schema": "toom-neg1-runtime-replay-v1", "status": "incomplete",
              "runtime_only": True, "proof_acceptance": False,
              "performance_acceptance": False, "timing_run": False,
              "source_commit": commit, "source_tree": tree,
              "snapshot_sha256": files(source), "archive_sha256": digest(archive),
              "tool_sha256": hashes, "python": sys.version,
              "python_executable": str(Path(sys.executable).resolve()),
              "environment": selected_env, "commands": [], "outcomes": {}}
    save(out / "receipt.json", report)

    def run(name: str, argv: list[str], expected: set[int] = {0}, timeout: int = 120) -> int:
        entry = {"name": name, "argv": list(map(str, argv)), "cwd": str(out),
                 "timeout_seconds": timeout, "started_utc": datetime.now(timezone.utc).isoformat()}
        report["commands"].append(entry)
        save(out / "receipt.json", report)
        try:
            result = subprocess.run(entry["argv"], cwd=out, env=env, capture_output=True, timeout=timeout)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr, code = error.stdout or b"", error.stderr or b"", None
            entry["timed_out"] = True
        for suffix, data in (("stdout", stdout), ("stderr", stderr)):
            path = out / (name + "." + suffix)
            path.write_bytes(data)
            entry[suffix + "_sha256"] = digest(path)
        entry.update(exit_code=code, finished_utc=datetime.now(timezone.utc).isoformat())
        save(out / "receipt.json", report)
        if code not in expected:
            raise RuntimeError(f"{name}: exit {code}, expected {sorted(expected)}")
        return code

    run("verus-version", [str(verifier), "--version"])
    run("rustc-version", [str(rustc), "--version", "--verbose"])
    run("rustc-sysroot", [str(rustc), "--print", "sysroot"])
    version = (out / "verus-version.stdout").read_text() + (out / "verus-version.stderr").read_text()
    if pin["verus_version"] not in version or pin["rust_toolchain"] not in version:
        raise RuntimeError("verifier or rust toolchain version mismatch")
    sysroot = Path((out / "rustc-sysroot.stdout").read_text().strip())
    compiler_files = [sysroot / "bin" / "rustc", rustc.resolve()]
    compiler_files.extend(sorted((sysroot / "lib").glob("librustc_driver*")))
    compiler_files.extend(sorted((sysroot / "lib").glob("libLLVM*")))
    if not all(path.is_file() for path in compiler_files) or len(compiler_files) < 3:
        raise RuntimeError("cannot identify actual Rust compiler and driver")
    report["rust_compiler_sha256"] = {str(path): digest(path) for path in compiler_files}
    save(out / "receipt.json", report)
    fixture = out / "fixture"
    oracle = feature / "oracle.py"
    run("fixture-generate", [sys.executable, "-B", str(oracle), "generate", "--out", str(fixture)])
    run("census", [sys.executable, "-B", str(oracle), "census", "--root", str(fixture),
                   "--report", str(out / "census.json")])
    definitions = json.loads((feature / "mutations.json").read_text())
    variants = [("candidate", None)] + [(m["name"], m) for m in definitions["mutants"]]
    variants.append((definitions["dispatch_policy"]["name"], definitions["dispatch_policy"]))
    original = (native / "verified" / "toom_multiply.rs").read_text()
    for name, mutation in variants:
        folder = out / name
        folder.mkdir()
        shutil.copytree(native, folder / "native")
        changed = folder / "native" / "verified" / "toom_multiply.rs"
        if mutation is not None:
            if original.count(mutation["anchor"]) != 1:
                raise RuntimeError("mutant anchor is not unique: " + name)
            edited = original.replace(mutation["anchor"], mutation["replacement"], 1)
            changed.write_text(edited)
            (folder / "mutation.diff").write_text("".join(difflib.unified_diff(
                original.splitlines(keepends=True), edited.splitlines(keepends=True),
                fromfile="candidate/toom_multiply.rs", tofile=name + "/toom_multiply.rs")))
        lib = folder / "libverigmp.rlib"
        run(name + "-library", [str(verifier), str(folder / "native" / "lib.rs"),
             "--crate-name", "verigmp", "--crate-type", "lib", "--no-verify", "--compile",
             "--num-threads", "2", "-O", "-o", str(lib)])
        runner = folder / "runner"
        run(name + "-runner-build", [str(rustc), "--edition=2021", "-O",
             str(feature / "runner.rs"), "-L", "dependency=" + str(verifier.parent),
             "--extern", "verigmp=" + str(lib), "-o", str(runner)])
        oracle_report = folder / "oracle-report.json"
        expected_exit = {2} if mutation is not None and name != definitions["dispatch_policy"]["name"] else {0}
        run(name + "-oracle", [sys.executable, "-B", str(oracle), "verify", "--root", str(fixture),
             "--runner", str(runner), "--report", str(oracle_report), "--raw-dir", str(folder / "raw")],
            expected=expected_exit)
        result = json.loads(oracle_report.read_text())
        if expected_exit == {2} and (result["status"] != "semantic-mismatch" or not result["mismatches"]):
            raise RuntimeError("semantic mutant lacked a numerical mismatch: " + name)
        report["outcomes"][name] = {"oracle_status": result["status"],
                                    "source_sha256": digest(changed),
                                    "runner_sha256": digest(runner),
                                    "library_sha256": digest(lib),
                                    "oracle_report_sha256": digest(oracle_report),
                                    "mutation_diff_sha256": digest(folder / "mutation.diff") if mutation else None}
        save(out / "receipt.json", report)
    report["status"] = "runtime-only-pass"
    report["artifact_sha256"] = {k: v for k, v in files(out).items() if k != "receipt.json"}
    save(out / "receipt.json", report)
    print(json.dumps({"status": report["status"], "receipt": str(out / "receipt.json")}, indent=2))


if __name__ == "__main__":
    main()

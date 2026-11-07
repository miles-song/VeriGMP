#!/usr/bin/env python3
"""Source-bound refinement, runtime-oracle and semantic-mutation gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from layout_mutations import MUTATIONS, SOURCE, check_anchors, mutate
from layout_oracle import check as check_oracle
from verus_logs import self_check as check_verus_classifier
from verus_logs import strict_semantic_rejection

ROOT = Path(__file__).resolve().parents[2]
FEATURE = Path(__file__).resolve().parent
FATAL = re.compile(
    r"(?i)\bunknown\b|\brlimit\b|resource\s+limit|timed?\s*out|\btimeout\b|"
    r"time\s*limit|failed\s+to\s+typecheck|type[- ]?checking?\s+(?:failed|error)|"
    r"mismatched\s+types|internal\s+(?:compiler\s+)?error|panic(?:ked|s|ed)?|"
    r"error\[E\d+\]|(?:could\s+not|failed\s+to)\s+(?:load|compile)|"
    r"out\s+of\s+memory|segmentation\s+fault|LLVM\s+ERROR"
)
POSITIVE = re.compile(r"(?m)^verification results:: ([1-9][0-9]*) verified, 0 errors$")


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
            windows_root = mounted_root[1].upper() + ":/" + mounted_root[2]
            return [str(windows_git), "-C", windows_root]
        gitdir = Path("/mnt") / match[1].lower() / match[2].replace("\\", "/")
        return ["git", f"--git-dir={gitdir}", f"--work-tree={ROOT}"]
    return ["git", "-C", str(ROOT)]


def git(*args):
    return subprocess.run(git_adapter() + list(args), check=True, capture_output=True,
                          text=True, timeout=60).stdout.strip()


def run(command, log_name, cwd, env, output, timeout=900, input_bytes=None):
    command = list(map(str, command))
    try:
        result = subprocess.run(command, cwd=cwd, env=env, input=input_bytes,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout)
    except subprocess.TimeoutExpired as error:
        (output / (log_name + ".stdout.log")).write_bytes(error.stdout or b"")
        (output / (log_name + ".stderr.log")).write_bytes(error.stderr or b"")
        raise RuntimeError("process timed out: " + log_name) from error
    stdout = result.stdout or b""
    stderr = result.stderr or b""
    (output / (log_name + ".stdout.log")).write_bytes(stdout)
    (output / (log_name + ".stderr.log")).write_bytes(stderr)
    return result.returncode, (stdout + stderr).decode(errors="replace"), sha(stdout), sha(stderr)


def source_inventory():
    names = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "native").rglob("*.rs"))]
    names += [
        "AGENTS.md", "native/toolchain.json", "native/proof-status.json", "native/lib.rs",
        "README.md", "README.zh-CN.md", "docs/packed-convolution.md",
        "experiments/packed-convolution/layout_oracle.py",
        "experiments/packed-convolution/layout_mutations.py",
        "experiments/packed-convolution/verus_logs.py",
        "experiments/packed-convolution/layout_verify.py",
    ]
    return sorted(set(names))


def positive(returncode, text):
    summaries = POSITIVE.findall(text)
    if returncode != 0 or len(summaries) != 1 or FATAL.search(text):
        raise RuntimeError("missing unique complete successful Verus summary")
    if re.search(r"(?im)^error(?:\[[^\]]*\])?:", text):
        raise RuntimeError("Verus success output contains an error diagnostic")
    return int(summaries[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError("use a fresh persistent evidence directory outside the checkout")
    output.mkdir(parents=True)
    report = dict(
        status="running", scope="packed-layout runtime refinement; no product composition or speed claim",
        benchmark_run=False, gmp_parity=False, backend_replacement=False,
        source_git={}, toolchain={}, oracle={}, mutants=[], commands=[],
        codegen_no_verification_overhead="pending separate optimized-codegen comparison",
    )

    def save():
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n",
                                                  encoding="utf-8")

    save()
    try:
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise RuntimeError("pinned Rust/Verus layout gate requires x86_64 Linux/WSL")
        if git("status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError("commit the complete feature snapshot before running this gate")
        head = git("rev-parse", "HEAD")
        sources = {name: (ROOT / name).read_bytes() for name in source_inventory()}
        if (ROOT / SOURCE).read_bytes() == b"":
            raise RuntimeError("packed layout source is empty")
        layout_text = sources[SOURCE].decode("utf-8")
        report["source_git"] = dict(head=head, branch=git("branch", "--show-current"),
                                    source_sha256={name: sha(data) for name, data in sources.items()})
        report["classifier_self_check"] = check_verus_classifier()
        report["mutation_anchor_self_check"] = check_anchors(layout_text)
        forbidden = re.compile(
            r"\b(?:assume|admit|axiom)\s*\(|external_body|external_fn_specification|"
            r"verifier::trusted|verify\s*=\s*false|\bunsafe\b|extern\s+\"C\""
        )
        for name, data in sources.items():
            if name.startswith("native/") and name.endswith(".rs") and forbidden.search(data.decode()):
                raise RuntimeError("proof escape or FFI in verified Rust source: " + name)

        snapshot = output / "source"
        for name, data in sources.items():
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        deps = args.deps_root.resolve()
        pin = json.loads(sources["native/toolchain.json"])
        verifier = deps / "verus/verus-x86-linux/verus"
        rustup = deps / "cargo/bin/rustup"
        env = dict(os.environ, CARGO_HOME=str(deps / "cargo"), RUSTUP_HOME=str(deps / "rustup"),
                   RUSTUP_TOOLCHAIN=pin["rust_toolchain"], PYTHONDONTWRITEBYTECODE="1")
        env["PATH"] = str(deps / "cargo/bin") + os.pathsep + env.get("PATH", "")

        code, verus_version, _, _ = run([verifier, "--version"], "verus-version", snapshot,
                                        env, output)
        if code or pin["verus_version"] not in verus_version or pin["rust_toolchain"] not in verus_version:
            raise RuntimeError("Verus version does not match pinned toolchain")
        code, rust_version, _, _ = run(
            [rustup, "run", pin["rust_toolchain"], "rustc", "-vV"],
            "rustc-version", snapshot, env, output)
        if code or "release: 1.99.1" not in rust_version or "host: x86_64-unknown-linux-gnu" not in rust_version:
            raise RuntimeError("Rust compiler does not match pinned toolchain")
        report["toolchain"] = dict(verus=verus_version, rustc=rust_version,
                                   verifier_sha256=file_sha(verifier), rustup_sha256=file_sha(rustup))

        library = output / "libverigmp.rlib"
        metadata = output / "verigmp.vir"
        command = [verifier, snapshot / "native/lib.rs", "--crate-type", "lib", "--crate-name", "verigmp",
                   "--no-cheating", "--compile", "-O", "--export", metadata, "-o", library]
        code, text, out_sha, err_sha = run(command, "library-build", snapshot, env, output)
        report["commands"].append(dict(name="library-build", returncode=code, stdout_sha256=out_sha,
                                       stderr_sha256=err_sha, argv=list(map(str, command))))
        report["library_verified_items"] = positive(code, text)
        report["library_sha256"] = dict(rlib=file_sha(library), metadata=file_sha(metadata))
        save()

        oracle_dir = output / "oracle"
        report["oracle"] = check_oracle(oracle_dir)
        runner_source = oracle_dir / "runtime-cases.rs"
        alias_source = oracle_dir / "alias-negative.rs"
        rustc = [rustup, "run", pin["rust_toolchain"], "rustc"]
        runtime_binary = output / "packed-layout-runtime"
        command = rustc + [runner_source, "--edition=2024", "-L", f"dependency={output}",
                           "-L", f"dependency={verifier.parent}", "--extern", f"verigmp={library}",
                           "-o", runtime_binary]
        code, text, out_sha, err_sha = run(command, "runtime-build", output, env, output)
        report["commands"].append(dict(name="runtime-build", returncode=code,
                                       stdout_sha256=out_sha, stderr_sha256=err_sha,
                                       argv=list(map(str, command))))
        if code or FATAL.search(text):
            raise RuntimeError("could not compile the source-bound Rust runtime oracle client")
        code, text, out_sha, err_sha = run([runtime_binary], "runtime-oracle", output, env, output)
        report["commands"].append(dict(name="runtime-oracle", returncode=code,
                                       stdout_sha256=out_sha, stderr_sha256=err_sha,
                                       argv=[str(runtime_binary)]))
        if code or FATAL.search(text):
            raise RuntimeError("runtime oracle client failed")
        report["runtime_oracle"] = dict(status="pass", executable_sha256=file_sha(runtime_binary),
                                        cases=report["oracle"]["valid_cases"],
                                        error_cases=report["oracle"]["error_cases"])

        command = rustc + [alias_source, "--edition=2024", "-L", f"dependency={output}",
                           "-L", f"dependency={verifier.parent}", "--extern", f"verigmp={library}",
                           "-o", output / "alias-negative"]
        code, text, out_sha, err_sha = run(command, "alias-negative", output, env, output)
        diagnostics = re.findall(r"(?m)^error\[([^\]]+)\]: (.*)$", text)
        if code != 1 or len(diagnostics) != 1 or diagnostics[0][0] != "E0502" or FATAL.search(text):
            raise RuntimeError("alias-overlap fixture was not rejected uniquely by the borrow checker")
        report["alias_negative"] = dict(status="pass", diagnostic=diagnostics[0][0],
                                         stdout_sha256=out_sha, stderr_sha256=err_sha)

        for name, function, before, after in MUTATIONS:
            mutant_root = output / "mutants" / name
            for source_name, data in sources.items():
                if source_name.startswith("native/"):
                    target = mutant_root / source_name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            mutant_path = mutant_root / SOURCE
            mutant_path.write_text(mutate(layout_text, function, before, after), encoding="utf-8")
            command = [verifier, mutant_root / "native/lib.rs", "--crate-type", "lib",
                       "--verify-module", "packed_layout", "--multiple-errors", "0"]
            code, text, out_sha, err_sha = run(command, "mutant-" + name, mutant_root, env, output)
            rejected = strict_semantic_rejection(text, code, "packed_layout")
            report["commands"].append(dict(name="mutant-" + name, returncode=code,
                                           stdout_sha256=out_sha, stderr_sha256=err_sha,
                                           argv=list(map(str, command))))
            report["mutants"].append(dict(name=name, source_sha256=file_sha(mutant_path),
                                          rejected_by_logical_vc=rejected))
            save()
            if not rejected:
                raise RuntimeError("mutation was not rejected by a unique complete logical VC: " + name)

        if any((ROOT / name).read_bytes() != data for name, data in sources.items()):
            raise RuntimeError("source changed during layout gate")
        report["status"] = "pass_runtime_refinement_candidate"
    except Exception as error:
        report.update(status="error", error=f"{type(error).__name__}: {error}")
    save()
    print(json.dumps({key: report[key] for key in
                      ("status", "error", "library_verified_items", "runtime_oracle",
                       "alias_negative", "mutants", "codegen_no_verification_overhead") if key in report},
                     indent=2))
    return 0 if report["status"] == "pass_runtime_refinement_candidate" else 1


if __name__ == "__main__":
    raise SystemExit(main())

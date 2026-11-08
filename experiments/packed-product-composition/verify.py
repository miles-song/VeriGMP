#!/usr/bin/env python3
"""Fixed-source actual-call proof, exact oracle, strict mutants and erasure gate."""
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
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
FEATURE = "experiments/packed-product-composition"
from oracle import generate
sys.path.insert(0, str(ROOT / "experiments/packed-convolution"))
from layout_oracle import check as layout_oracle
from layout_verify import git_adapter, positive, file_sha
from verus_logs import strict_semantic_rejection, self_check, FATAL_DIAGNOSTIC
from negative_checks import (MODEL, CONSUMER, MUTATIONS, alias_call, invalid_call,
                             classifier_check, full_semantic_rejection)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError("use a fresh persistent evidence directory outside this checkout")
    output.mkdir(parents=True)
    report = dict(status="running", scope="equal-length canonical exact packed product",
                  benchmark_run=False, production_runtime_changed=False,
                  bit_cost_proved=False, peak_space_proved=False, solver_integration=False,
                  commands=[], mutants=[], invalid_calls=[], alias_checks=[])

    def save():
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def run(command, name, cwd=output, timeout=900):
        command = list(map(str, command))
        try:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            (output / (name + ".stdout.log")).write_bytes(error.stdout or b"")
            (output / (name + ".stderr.log")).write_bytes(error.stderr or b"")
            report["commands"].append(dict(name=name, argv=command, cwd=str(cwd), timeout=True))
            save()
            raise RuntimeError("timeout is a gate failure: " + name) from error
        (output / (name + ".stdout.log")).write_bytes(result.stdout)
        (output / (name + ".stderr.log")).write_bytes(result.stderr)
        text = (result.stdout + result.stderr).decode(errors="replace")
        report["commands"].append(dict(name=name, argv=command, cwd=str(cwd),
            returncode=result.returncode, stdout_sha256=sha(result.stdout),
            stderr_sha256=sha(result.stderr), timeout=False))
        save()
        return result.returncode, text

    def ordinary(command, name, cwd=output):
        code, text = run(command, name, cwd)
        if code or re.search(r"(?m)^error(?:\[[^\]]*\])?:", text):
            raise RuntimeError("ordinary compilation/execution failed: " + name)
        return text

    save()
    try:
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise RuntimeError("this pinned acceptance gate requires x86_64 Linux/WSL")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        git = lambda *argv: subprocess.run(git_adapter() + list(argv), check=True,
                                           capture_output=True, timeout=60).stdout
        if git("status", "--porcelain", "--untracked-files=all").strip():
            raise RuntimeError("commit the feature inputs before fixed-source acceptance")
        head = git("rev-parse", "HEAD").decode().strip()
        names = [path.relative_to(ROOT).as_posix() for path in (ROOT / "native").rglob("*.rs")]
        names += [f"{FEATURE}/{path.name}" for path in (ROOT / FEATURE).iterdir()
                  if path.suffix in (".py", ".rs", ".md")]
        names += ["AGENTS.md", "LICENSE", "native/toolchain.json", "native/proof-status.json",
                  "README.md", "README.zh-CN.md", "docs/packed-convolution.md",
                  "docs/packed-product-composition.md",
                  "experiments/packed-convolution/layout_oracle.py",
                  "experiments/packed-convolution/layout_verify.py",
                  "experiments/packed-convolution/layout_mutations.py",
                  "experiments/packed-convolution/verus_logs.py"]
        sources = {name: (ROOT / name).read_bytes() for name in sorted(set(names))}
        for name, data in sources.items():
            if git("show", f"{head}:{name}") != data:
                raise RuntimeError("source differs from HEAD: " + name)
        report["source_git"] = dict(head=head, branch=git("branch", "--show-current").decode().strip(),
            root=str(ROOT), git_command=git_adapter(), source_sha256={n: sha(d) for n, d in sources.items()})
        forbidden = re.compile(r"\b(?:assume|admit|axiom)\s*\(|external_body|external_fn_specification|"
                               r"verifier::trusted|verify\s*=\s*false|\bunsafe\b|extern\s+\"C\"")
        for name in (MODEL, CONSUMER):
            if forbidden.search(sources[name].decode()):
                raise RuntimeError("proof escape/FFI in feature source: " + name)
        for name, source, before, after in MUTATIONS:
            if sources[source].decode().count(before) != 1 or before == after:
                raise RuntimeError("mutation anchor is not unique: " + name)
        report["classifier_self_checks"] = [self_check(), classifier_check()]
        for readme in ("README.md", "README.zh-CN.md"):
            if "docs/packed-product-composition.md" not in sources[readme].decode():
                raise RuntimeError("missing synchronized composition documentation link")
        if not any("specs/packed_product.rs" in m["files"] and m["status"] == "model_proved"
                   for m in json.loads(sources["native/proof-status.json"])["modules"]):
            raise RuntimeError("missing precise model proof status")
        report["documentation_check"] = "pass (scoped links and status; no repository-wide checker exists)"
        snapshot = output / "source"
        for name, data in sources.items():
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        deps = args.deps_root.resolve()
        pin = json.loads(sources["native/toolchain.json"])
        archive = deps / "verus-download" / pin["archive"]
        if file_sha(archive) != pin["sha256"]:
            raise RuntimeError("pinned Verus archive hash mismatch")
        verifier = deps / "verus/verus-x86-linux/verus"
        tools = {}
        with zipfile.ZipFile(archive) as bundle:
            for name in ("verus", "rust_verify", "z3", "vstd.vir", "libvstd.rlib",
                         "libverus_builtin.rlib", "libverus_builtin_macros.so",
                         "libverus_state_machines_macros.so"):
                installed = verifier.parent / name
                with bundle.open("verus-x86-linux/" + name) as stream:
                    expected = hashlib.file_digest(stream, "sha256").hexdigest()
                if file_sha(installed) != expected:
                    raise RuntimeError("installed tool differs from archive: " + name)
                tools[str(installed)] = expected
        rustup = deps / "cargo/bin/rustup"
        env.update(CARGO_HOME=str(deps / "cargo"), RUSTUP_HOME=str(deps / "rustup"),
                   RUSTUP_TOOLCHAIN=pin["rust_toolchain"])
        env["PATH"] = str(deps / "cargo/bin") + os.pathsep + env.get("PATH", "")
        version = ordinary([verifier, "--version"], "verus-version")
        if pin["verus_version"] not in version or pin["rust_toolchain"] not in version:
            raise RuntimeError("Verus version does not match pin")
        rustc = [rustup, "run", pin["rust_toolchain"], "rustc"]
        rust_version = ordinary(rustc + ["-vV"], "rustc-version")
        if "release: 1.99.1" not in rust_version or "host: x86_64-unknown-linux-gnu" not in rust_version:
            raise RuntimeError("Rust compiler does not match pin")
        sysroot = Path(ordinary(rustc + ["--print", "sysroot"], "rustc-sysroot").strip())
        actual_tools = [rustup, sysroot / "bin/rustc", Path(sys.executable)]
        actual_tools += list((sysroot / "lib").glob("librustc_driver*.so"))
        actual_tools += list((sysroot / "lib").glob("libLLVM*.so*"))
        actual_tools += [Path(shutil.which(name)) for name in ("objdump", "objcopy")]
        tools.update({str(path): file_sha(path) for path in actual_tools})
        report["toolchain"] = dict(verus_version=version, rustc_version=rust_version,
            archive_sha256=pin["sha256"], actual_file_sha256=tools, python_version=sys.version,
            kernel=platform.platform())

        library, metadata = output / "libverigmp.rlib", output / "verigmp.vir"
        report["library_verified_items"] = positive(*run([verifier, snapshot / "native/lib.rs",
            "--crate-type", "lib", "--crate-name", "verigmp", "--no-cheating", "--compile", "-O",
            "--export", metadata, "-o", library], "library-proof-release", snapshot))
        imports = ["--import", f"verigmp={metadata}", "--extern", f"verigmp={library}"]
        consumer_lib, consumer_meta = output / "libpacked_product_consumer.rlib", output / "consumer.vir"
        consumer_command = [verifier, snapshot / CONSUMER, "--crate-type", "lib", "--crate-name",
                            "packed_product_consumer", "--no-cheating", *imports]
        report["consumer_verified_items"] = positive(*run(consumer_command + ["--compile", "-O",
            "--export", consumer_meta, "-o", consumer_lib], "consumer-proof-release", snapshot))
        report["exports_sha256"] = {path.name: file_sha(path)
                                     for path in (library, metadata, consumer_lib, consumer_meta)}
        dependencies = ["--edition=2024", "-O", "-L", f"dependency={output}", "-L",
                        f"dependency={verifier.parent}", "--extern", f"verigmp={library}",
                        "--extern", f"packed_product_consumer={consumer_lib}"]
        report["oracle"] = generate(output / "oracle")
        runtime = output / "runtime"
        ordinary(rustc + [snapshot / FEATURE / "runtime.rs", *dependencies, "-o", runtime], "runtime-build")
        runtime_text = ordinary([runtime, output / "oracle/cases.bin"], "runtime-oracle")
        report["runtime_oracle"] = dict(status="pass", stdout=runtime_text,
                                        executable_sha256=file_sha(runtime), cases=report["oracle"]["cases"])
        report["layout_oracle"] = layout_oracle(output / "layout-oracle")
        layout_runtime = output / "layout-runtime"
        ordinary(rustc + [output / "layout-oracle/runtime-cases.rs", *dependencies, "-o", layout_runtime],
                 "layout-runtime-build")
        ordinary([layout_runtime], "layout-runtime-oracle")
        report["layout_oracle"]["runtime_executed"] = True
        report["layout_oracle"]["executable_sha256"] = file_sha(layout_runtime)

        for kind, diagnostic in (("input", "E0502"), ("output", "E0499")):
            path = output / ("alias-" + kind + ".rs")
            path.write_text(alias_call(kind), encoding="utf-8")
            code, text = run(rustc + [path, *dependencies, "-o", output / ("alias-" + kind)], "alias-" + kind)
            errors = re.findall(r"(?m)^error\[([^\]]+)\]: (.*)$", text)
            clean = re.sub(r"(?m)^error\[" + diagnostic + r"\]:.*$", "", text, count=1)
            passed = code == 1 and len(errors) == 1 and errors[0][0] == diagnostic
            passed = passed and FATAL_DIAGNOSTIC.search(clean) is None
            report["alias_checks"].append(dict(kind=kind, status="pass" if passed else "fail",
                                               expected_diagnostic=diagnostic, fixture_sha256=file_sha(path)))
            if not passed:
                raise RuntimeError("borrow fixture did not uniquely reject overlap: " + kind)

        client_imports = imports + ["--import", f"packed_product_consumer={consumer_meta}",
                                   "--extern", f"packed_product_consumer={consumer_lib}"]
        for kind, anchor in (("scratch", "old(scratch)@.len() >= 12"),
                             ("guard", "packed_product::guard_domain"),
                             ("output", "old(output)@.len() == 2")):
            path = output / ("invalid-" + kind + ".rs")
            path.write_text(invalid_call(kind), encoding="utf-8")
            code, text = run([verifier, path, "--crate-type", "lib", "--crate-name", "invalid_call",
                              "--no-cheating", *client_imports], "invalid-" + kind)
            passed = full_semantic_rejection(text, code) and anchor in text
            report["invalid_calls"].append(dict(kind=kind, status="pass" if passed else "fail",
                                                expected_precondition=anchor, fixture_sha256=file_sha(path)))
            if not passed:
                raise RuntimeError("invalid call did not reject its intended precondition: " + kind)

        for name, source, before, after in MUTATIONS:
            mutant_root = output / "mutants" / name
            mutant_path = mutant_root / source
            mutant_path.parent.mkdir(parents=True, exist_ok=True)
            if source == MODEL:
                shutil.copytree(snapshot / "native", mutant_root / "native", dirs_exist_ok=True)
            mutant_path.write_text(sources[source].decode().replace(before, after), encoding="utf-8")
            if source == MODEL:
                command = [verifier, mutant_root / "native/lib.rs", "--crate-type", "lib",
                           "--no-cheating", "--verify-module", "packed_product", "--multiple-errors", "0"]
            else:
                command = [verifier, mutant_path, "--crate-type", "lib", "--crate-name", "consumer_mutant",
                           "--no-cheating", *imports]
            code, text = run(command, "mutant-" + name, mutant_root)
            rejected = (strict_semantic_rejection(text, code, "packed_product") if source == MODEL
                        else full_semantic_rejection(text, code))
            report["mutants"].append(dict(name=name, source=source, before=before, after=after,
                source_sha256=file_sha(mutant_path), status="pass" if rejected else "fail"))
            if not rejected:
                raise RuntimeError("mutant lacks a complete strict logical rejection: " + name)

        consumer_obj, control_obj = output / "consumer.o", output / "control.o"
        report["codegen_verified_items"] = positive(*run(consumer_command + ["--compile", "-O", "--emit=obj",
            "-C", "codegen-units=1", "-o", consumer_obj], "consumer-codegen", snapshot))
        ordinary(rustc + [snapshot / FEATURE / "control.rs", "--crate-type", "lib", "--crate-name",
            "packed_product_consumer", *dependencies, "--emit=obj", "-C", "codegen-units=1", "-o", control_obj],
            "control-codegen")
        bodies, relocations, symbols = [], [], []
        for label, obj in (("consumer", consumer_obj), ("control", control_obj)):
            table = ordinary(["objdump", "-t", "-C", obj], label + "-symbols")
            matches = re.findall(r"(?m)^([0-9a-f]+)\s+g\s+F\s+(\.text\.\S+)\s+([0-9a-f]+)\s+"
                                 r"packed_product_consumer::consume$", table)
            if len(matches) != 1 or int(matches[0][0], 16) != 0:
                raise RuntimeError("cannot identify the complete consume symbol section")
            _, section, length_hex = matches[0]
            body_path = output / (label + "-body.bin")
            ordinary(["objcopy", "--dump-section", f"{section}={body_path}", obj], label + "-dump-section")
            body = body_path.read_bytes()
            if len(body) != int(length_hex, 16):
                raise RuntimeError("dumped section is not the complete symbol length")
            reloc = ordinary(["objdump", "-r", "--section=" + section, obj], label + "-relocations")
            rows = re.findall(r"(?m)^([0-9a-f]+)\s+(R_\S+)\s+(\S+.*)$", reloc)
            if len(rows) != 4 or not all(int(offset, 16) < len(body) for offset, _, _ in rows):
                raise RuntimeError("unexpected/incomplete external call relocation table")
            if (sum("pack_coefficients" in target for _, _, target in rows) != 2
                    or sum("toom_multiply4full" in target for _, _, target in rows) != 1
                    or sum("extract_coefficients" in target for _, _, target in rows) != 1):
                raise RuntimeError("unexpected calls in consumer body")
            bodies.append(body)
            relocations.append(rows)
            symbols.append(dict(object_sha256=file_sha(obj), symbol="packed_product_consumer::consume",
                                section=section, full_symbol_bytes=len(body), body_sha256=sha(body),
                                relocations=rows))
        if bodies[0] != bodies[1] or relocations[0] != relocations[1]:
            raise RuntimeError("proof client differs from the ordinary efficient control")
        report["erasure"] = dict(status="pass", complete_symbol_bytes_equal=True,
                                  complete_relocations_equal=True, symbols=symbols)
        for name, data in sources.items():
            if (ROOT / name).read_bytes() != data:
                raise RuntimeError("source changed during fixed-source acceptance: " + name)
        if git("rev-parse", "HEAD").decode().strip() != head or git("status", "--porcelain").strip():
            raise RuntimeError("worktree identity changed during acceptance")
        report["status"] = "pass"
        report["remaining"] = ["general unequal/truncated polynomial product consumers",
            "composed worst-case bit cost and peak live-space theorem",
            "SAT descriptor provenance, creation precision, lift/reduction and integration",
            "production strategy and overall GMP performance target"]
    except Exception as error:
        report["status"] = "fail"
        report["failure"] = repr(error)
        raise
    finally:
        save()
    print(json.dumps(dict(status=report["status"], source=head,
        library_verified=report["library_verified_items"], consumer_verified=report["consumer_verified_items"],
        oracle_cases=report["oracle"]["cases"], strict_mutants=len(report["mutants"]),
        report_sha256=file_sha(output / "verification.json")), indent=2))


if __name__ == "__main__":
    main()

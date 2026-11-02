"""Validate the scoped fresh gate's recorded execution, without rerunning Verus."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import types
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


SCOPES = {
    "dyadic": (478, 2688, 102, "dyadic_producer"),
    "interpolation": (514, 336, 115, "interpolation"),
}
FAILURES = [
    "solver returned unknown", "rlimit", "failed to typecheck",
    "failed to load metadata", "could not compile crate", "internal compiler error",
    "verification timed out", "out of memory", "segmentation fault",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(name: str) -> str:
    path = PurePosixPath(name)
    require(bool(name) and not path.is_absolute() and ".." not in path.parts
            and "\\" not in name and ":" not in name and str(path) == name,
            f"unsafe evidence path: {name}")
    return name


def directory_reader(root: Path) -> Callable[[str], bytes]:
    root = root.resolve()

    def read(name: str) -> bytes:
        path = (root / relative(name)).resolve()
        require(path.is_relative_to(root), f"evidence path escapes directory: {name}")
        return path.read_bytes()

    return read


def audit_report(name: str, scope: Path, read: Callable[[str], bytes]) -> dict:
    """Bind a raw report to current inputs, logs, commands and compiled outputs."""
    verified, cases, source_count, stem = SCOPES[name]
    report_bytes = read("verification.json")
    report = json.loads(report_bytes)
    require(report["status"] == "pass" and report["benchmark_run"] is False
            and report["production_modified"] is False, f"{name}: incomplete or wrong-scope report")
    sources = report["source_sha256"]
    extra = [f"check_{stem}.py", f"{stem}_oracle.py", f"{stem}_codegen.py", "origin.json", "scope.json"]
    if name == "dyadic":
        extra.append("prepare_dyadic_gate.py")
    expected = {p.relative_to(scope).as_posix() for p in (scope / "candidate/native").rglob("*") if p.is_file()}
    expected.update(extra)
    require(set(sources) == expected and len(sources) == source_count, f"{name}: source set differs")
    for rel, wanted in sources.items():
        captured = read("inputs/" + relative(rel))
        require(digest(captured) == wanted == digest((scope / rel).read_bytes()), f"{name}: source mismatch: {rel}")
        if rel.endswith(".rs"):
            require(not re.search(r"\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)",
                                  captured.decode()), f"{name}: proof escape: {rel}")
    origin = json.loads(read("inputs/origin.json"))
    for rel, wanted in origin["inherited_native_sha256"].items():
        require(sources[rel] == wanted, f"{name}: inherited source mismatch: {rel}")

    # Only the already source-bound local classifier is compiled; supplied code is never executed.
    tree = ast.parse((scope / f"check_{stem}.py").read_bytes())
    selected = [node for node in tree.body if
                isinstance(node, ast.FunctionDef) and node.name in {"fatal_diagnostic", "strict_vc"} or
                isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "FATAL_DIAGNOSTIC" for t in node.targets)]
    classifier = {"re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<source-bound diagnostic classifier>", "exec"), classifier)
    mutants = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "MUTANTS" for t in node.targets))
    commands = {row["log"]: row for row in report["commands"]}
    logs = {"toolchain.log", "rustc-path.log", "rustc.log", "rustc-linked.log", "library.log",
            "runner-build.log", "runner-linked.log", "oracle.log", "codegen-build.log"}
    logs.update(f"invalid-{i:02}.log" for i in range(12))
    logs.update(m[0] + ".log" for m in mutants)
    require(set(commands) == logs and len(commands) == len(report["commands"]), f"{name}: command set differs")
    for log, command in commands.items():
        require(command["status"] == "completed" and type(command["returncode"]) is int,
                f"{name}: command did not complete: {log}")
        require(digest(read(relative(log))) == command["log_sha256"], f"{name}: log mismatch: {log}")
    text = lambda log: read(log).decode("utf-8")
    verifier = commands["toolchain.log"]["argv"][0]
    library = commands["library.log"]["argv"]
    suffix = "inputs/candidate/native/lib.rs"
    require(library[1].endswith(suffix), f"{name}: library input is not the captured snapshot")
    prefix = library[1][:-len(suffix)]
    native = prefix + "inputs/candidate/native/"
    expected_commands = {
        "library.log": [verifier, native + "lib.rs", "--crate-name", "producer_candidate", "--crate-type", "lib",
                        "--export", prefix + "candidate.vir", "--compile", "-O", "-o", prefix + "libcandidate.rlib"],
        "runner-build.log": [verifier, native + f"toom8_{stem}_runner.rs", "--compile", "-O", "-o", prefix + "oracle-runner"],
        "codegen-build.log": [verifier, native + f"toom8_{stem}_codegen.rs", "--compile", "-O", "--emit=asm", "-o", prefix + "codegen.s"],
    }
    for log, key in [("library.log", "library_verified"), ("runner-build.log", "runner_verified"), ("codegen-build.log", "codegen_verified")]:
        diagnostic = text(log)
        require(commands[log]["argv"] == expected_commands[log], f"{name}: compile command differs: {log}")
        require(commands[log]["returncode"] == 0 and report[key] == verified
                and re.findall(r"verification results:: (\d+) verified, (\d+) errors", diagnostic) == [(str(verified), "0")]
                and "partial verification" not in diagnostic and not classifier["fatal_diagnostic"](diagnostic)
                and not re.search(r"(?im)^error(?:\[|:)", diagnostic), f"{name}: full verification failed: {log}")
    for log in ["oracle.log", *(f"invalid-{i:02}.log" for i in range(12))]:
        require(commands[log]["argv"] == [prefix + "oracle-runner"], f"{name}: runner command differs: {log}")

    pin = json.loads(read("inputs/candidate/native/toolchain.json"))
    rustc = text("rustc-path.log").strip()
    tool_commands = {"toolchain.log": [verifier, "--version"],
                     "rustc-path.log": ["rustup", "which", "--toolchain", pin["rust_toolchain"], "rustc"],
                     "rustc.log": [rustc, "-vV"], "rustc-linked.log": ["ldd", rustc],
                     "runner-linked.log": ["ldd", prefix + "oracle-runner"]}
    for log, argv in tool_commands.items():
        require(commands[log]["argv"] == argv and commands[log]["returncode"] == 0, f"{name}: tool command differs: {log}")
    require(report["toolchain"] == text("toolchain.log") and pin["verus_version"] in report["toolchain"]
            and pin["rust_toolchain"] in report["toolchain"] and report["rustc"] == text("rustc.log")
            and "release: " + pin["rust_toolchain"].split("-")[0] in report["rustc"], f"{name}: tool version mismatch")
    tools, runtime = report["toolchain_file_sha256"], report["runtime_library_sha256"]
    expected_tools = {"verus", "rust_verify", "z3", "vstd.vir", "libvstd.rlib", "libverus_builtin.rlib",
                      "libverus_builtin_macros.so", "libverus_state_machines_macros.so", "rustc", "rustup", "python3.12"}
    tool_names = {PurePosixPath(p).name for p in tools}
    for log in ["rustc-linked.log", "runner-linked.log"]:
        require("not found" not in text(log), f"{name}: unresolved runtime library")
        for path in re.findall(r"(?:=>\s+|\s)(/\S+)\s+\(", text(log)):
            linked = PurePosixPath(path).name
            # ldd prints SONAME links; the gate hashes their resolved versioned files.
            matches = {candidate for candidate in tool_names if candidate == linked or candidate.startswith(linked + ".")}
            require(len(matches) == 1, f"{name}: linked tool identity missing: {linked}")
            expected_tools.update(matches)
    require(len(tools) == 21 and tool_names == expected_tools
            and verifier in tools and rustc in tools, f"{name}: tool identity set differs")
    require(len(runtime) == 3 and all(tools.get(p) == h for p, h in runtime.items())
            and {PurePosixPath(p).name for p in runtime} == {"ld-linux-x86-64.so.2", "libc.so.6", "libgcc_s.so.1"},
            f"{name}: runtime identity set differs")
    require(all(re.fullmatch(r"[0-9a-f]{64}", h) for h in tools.values()), f"{name}: malformed tool identity")

    def local_module(module_name: str) -> types.ModuleType:
        module = types.ModuleType(module_name)
        module.__file__ = str(scope / (module_name + ".py"))
        exec(compile((scope / (module_name + ".py")).read_bytes(), module.__file__, "exec"), module.__dict__)
        return module

    oracle = local_module(stem + "_oracle")
    rows, counts = oracle.cases()
    inputs = ("\n".join(row[0] for row in rows) + "\n").encode()
    outputs = ("\n".join(row[1] for row in rows) + "\n").encode()
    require(len(rows) == cases == report["oracle"]["cases"] and counts == report["oracle"]["counts"]
            and digest(inputs) == report["oracle"]["input_sha256"] and digest(outputs) == report["oracle"]["output_sha256"]
            and read("oracle.log") == outputs and commands["oracle.log"]["returncode"] == 0,
            f"{name}: independent oracle mismatch")
    require([row["command"] for row in report["invalid"]] == oracle.invalid() and len(report["invalid"]) == 12,
            f"{name}: invalid-input set differs")
    for i, row in enumerate(report["invalid"]):
        log = f"invalid-{i:02}.log"
        require(row["returncode"] == commands[log]["returncode"] == 101 and "panicked at" in text(log)
                and row["log_sha256"] == commands[log]["log_sha256"], f"{name}: invalid input accepted: {i}")
    require(report["strict_classifier_selfcheck"] == "pass" and report["appended_failure_fixtures_rejected"] == FAILURES,
            f"{name}: strict classifier evidence differs")
    require(len(report["mutations"]) == len(mutants), f"{name}: mutation set differs")
    source = read(f"inputs/candidate/native/verified/toom8_{stem}.rs").decode()
    for row, (mutant, before, after) in zip(report["mutations"], mutants):
        log = mutant + ".log"
        command = commands[log]
        require((row["name"], row["before"], row["after"]) == (mutant, before, after)
                and source.count(before) == 1 and digest(source.replace(before, after).encode()) == row["source_sha256"]
                and row["log_sha256"] == command["log_sha256"] and row["semantically_rejected"] is True,
                f"{name}: mutation source/log mismatch: {mutant}")
        require(command["argv"] == [verifier, native + f"toom8_{stem}_runner.rs", "--verify-module", f"toom8_{stem}", "--multiple-errors", "0"]
                and classifier["strict_vc"](text(log), command["returncode"])
                and all(not classifier["strict_vc"](text(log) + "\n" + failure, command["returncode"]) for failure in FAILURES),
                f"{name}: nonsemantic mutation rejection: {mutant}")
    artifacts = report["artifact_sha256"]
    require(set(artifacts) == {"libcandidate.rlib", "candidate.vir", "oracle-runner", "codegen.s"}, f"{name}: artifact pair missing")
    for rel, wanted in artifacts.items():
        require(digest(read(rel)) == wanted, f"{name}: artifact mismatch: {rel}")
    assembly = text("codegen.s")
    require(local_module(stem + "_codegen").inspect(assembly) == report["codegen"], f"{name}: codegen inspection differs")
    require(not re.search(r"toom8_(newton_spec|dyadic_producer_spec|normalization_spec|convolution)", assembly),
            f"{name}: proof symbols remain in assembly")
    require(report["executed_snapshot_binding"] == {
        "checker": "captured bytes compiled and executed before workload setup", "oracle": "captured bytes compiled and executed",
        "codegen_inspector": "captured bytes compiled and executed", "origin": "captured bytes parsed"},
        f"{name}: executed-input binding missing")
    return {"status": "pass", "report_sha256": digest(report_bytes), "source_inputs": len(sources),
            "verified_items_per_entry": verified, "oracle_cases": cases, "invalid_commands": 12,
            "semantic_mutants": len(mutants), "tool_files": len(tools), "runtime_libraries": len(runtime),
            "toolchain": report["toolchain"], "rustc": report["rustc"], "artifact_sha256": artifacts,
            "started_utc": report["started_utc"], "finished_utc": report["finished_utc"],
            "codegen": report["codegen"], "current_installed_tool_bytes_checked": False}


def audit_fresh(repo: Path, bundle: Path, reports: dict[str, Path] | None = None) -> dict:
    identity = {}
    if reports is not None:
        require(set(reports) == set(SCOPES), "both raw execution reports are required")
        gates = {name: audit_report(name, repo / "experiments/toom8-primitives" / name,
                                   directory_reader(path.parent)) for name, path in reports.items()}
        mode = "supplied raw execution reports"
    else:
        manifest = json.loads((bundle / "manifest.json").read_bytes())
        require(manifest["status"] == "fresh_scoped_verification_pass_pending_independent_review"
                and all(manifest[key] is False for key in ["benchmark_run", "whole_toom8_kernel_accepted",
                                                          "solver_consumer_accepted", "backend_promotion"]),
                "fresh receipt exceeds the recorded acceptance scope")
        archive = bundle / "evidence.zip"
        require(digest(archive.read_bytes()) == manifest["archive_sha256"]
                and archive.stat().st_size == manifest["archive_bytes"], "fresh archive hash/size mismatch")
        with zipfile.ZipFile(archive) as saved:
            members = manifest["archive_members"]
            require(len(saved.namelist()) == len(set(saved.namelist())) and set(saved.namelist()) == set(members),
                    "fresh archive member set differs")
            for rel, wanted in members.items():
                require(digest(saved.read(relative(rel))) == wanted, f"fresh archive member mismatch: {rel}")
            gates = {name: audit_report(name, repo / "experiments/toom8-primitives" / name,
                                       lambda rel, n=name: saved.read(n + "/" + relative(rel))) for name in SCOPES}
        for name, result in gates.items():
            expected_receipt = {
                "report_sha256": result["report_sha256"], "source_input_count": result["source_inputs"],
                "tool_file_count": result["tool_files"], "runtime_library_count": result["runtime_libraries"],
                "verified_items_per_entry": result["verified_items_per_entry"], "oracle_cases": result["oracle_cases"],
                "invalid_commands": result["invalid_commands"], "semantic_mutants": result["semantic_mutants"],
                "started_utc": result["started_utc"], "finished_utc": result["finished_utc"],
            }
            require(expected_receipt == manifest["gates"][name], f"{name}: receipt report mismatch")
        require(set(manifest["gates"]) == set(SCOPES)
                and re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]), "fresh receipt source identity missing")
        identity = {"capture_source_commit": manifest["source_commit"], "archive_sha256": manifest["archive_sha256"],
                    "archive_bytes": manifest["archive_bytes"], "verifier_platform": manifest["verifier_platform"]}
        mode = "frozen fresh execution archive"
    return {"status": "pass", "mode": mode, **identity, "gates": gates, "verification_rerun": False,
            "runner_reexecuted": False, "independent_acceptance": False,
            "tool_identity_scope": "Recorded hashes and version/linkage logs; current installed tool binaries are not reread",
            "codegen_scope": "Textual optimized assembly inspection; length/slice guards remain; no timing or machine-code equivalence claim"}

"""Audit the scoped dyadic-recovery consumer and its current acceptance gates.

This checks source, historical archives and the dated Verus/Rust execution
registered in scope.json. Supplied archives and raw reports must have those
registered identities. It does not rerun the verifier or runner.
Audit discrepancies fail the command; missing performance and solver acceptance
remain explicit promotion blockers after a successful scoped audit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from fresh_evidence import audit_fresh, digest, relative, require


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INTERPOLATION = REPO / "experiments" / "toom8-primitives" / "interpolation"
DYADIC = REPO / "experiments" / "toom8-primitives" / "dyadic"
FRESH = HERE / "evidence" / "fresh-20261103"

U64_BITS = 64
BASE = 1 << U64_BITS
MASK = BASE - 1


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(read(path))


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def last_json(stdout: str) -> Any:
    """Decode the last JSON object printed by an archive audit."""
    starts = [match.start() for match in re.finditer(r"\{", stdout)]
    for start in reversed(starts):
        try:
            return json.loads(stdout[start:])
        except json.JSONDecodeError:
            continue
    raise RuntimeError("archive audit did not print a JSON object")


def run_archive_audit(path: Path) -> dict[str, Any]:
    command = [sys.executable, str(path)]
    try:
        completed = subprocess.run(
            command,
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "blocked", "command": command, "error": str(exc)}
    result: dict[str, Any] = {
        "status": "pass" if completed.returncode == 0 else "fail",
        "returncode": completed.returncode,
        "command": command,
    }
    if completed.returncode == 0:
        try:
            result["report"] = last_json(completed.stdout)
            if result["report"].get("status") != "pass":
                result["status"] = "fail"
                result["error"] = "archive audit did not report pass"
        except RuntimeError as exc:
            result["status"] = "fail"
            result["error"] = str(exc)
    else:
        result["stderr_tail"] = completed.stderr[-2000:]
    return result


def source_gate() -> dict[str, Any]:
    """Check that generic proof exports feed an actual runtime consumer."""
    lib = read(INTERPOLATION / "candidate" / "native" / "lib.rs")
    interpolation = read(
        INTERPOLATION / "candidate" / "native" / "verified" / "toom8_interpolation.rs"
    )
    dyadic = read(
        INTERPOLATION / "candidate" / "native" / "verified" / "toom8_dyadic_producer.rs"
    )
    normalization = read(
        INTERPOLATION / "candidate" / "native" / "verified" / "toom8_normalization.rs"
    )
    newton = read(INTERPOLATION / "candidate" / "native" / "verified" / "toom8_newton.rs")

    exports = [
        "toom8_newton_spec",
        "toom8_newton",
        "toom8_convolution",
        "toom8_dyadic_producer_spec",
        "toom8_dyadic_producer",
        "toom8_normalization_spec",
        "toom8_normalization",
        "toom8_even",
        "toom8_seventh_spec",
        "toom8_seventh",
        "toom8_interpolation",
    ]
    export_checks = {
        name: bool(re.search(rf"\bpub\s+mod\s+{re.escape(name)}\b", lib))
        for name in exports
    }

    def has_inline_consumer(source: str, name: str) -> bool:
        pattern = rf"#\[inline\(always\)\][\s\S]{{0,160}}\bpub\s+fn\s+{name}\b"
        return bool(re.search(pattern, source))

    consumer_checks = {
        "interpolate_is_runtime_fn": bool(re.search(r"\bpub\s+fn\s+interpolate\b", interpolation)),
        "dyadic_pair_is_runtime_fn": bool(re.search(r"\bpub\s+fn\s+dyadic_pair\b", dyadic)),
        "dyadic_pair_inline": has_inline_consumer(dyadic, "dyadic_pair"),
        "newton_even_runtime_fn": bool(re.search(r"\bpub\s+fn\s+even\b", newton)),
        "newton_odd_runtime_fn": bool(re.search(r"\bpub\s+fn\s+odd\b", newton)),
    }

    def body_after(source: str, marker: str) -> str:
        start = source.find(marker)
        if start < 0:
            return ""
        return source[start:]

    interpolation_body = body_after(interpolation, "pub fn interpolate")
    with_endpoints_body = interpolation[: interpolation.find("pub fn interpolate")]
    even_body = body_after(
        read(INTERPOLATION / "candidate" / "native" / "verified" / "toom8_even.rs"),
        "pub fn with_endpoints",
    )
    ordered_calls = [
        "toom4_multiply::full",
        "with_endpoints(",
    ]
    positions = [interpolation_body.find(call) for call in ordered_calls]
    interpolation_ordered = all(position >= 0 for position in positions) and positions == sorted(positions)
    endpoint_calls = [
        "toom8_even::with_endpoints",
        "toom8_seventh::prepare_seventh",
        "toom8_newton::odd",
    ]
    endpoint_positions = [with_endpoints_body.find(call) for call in endpoint_calls]
    endpoint_ordered = all(position >= 0 for position in endpoint_positions) and endpoint_positions == sorted(endpoint_positions)
    even_normalization = [
        even_body.find("toom8_normalization::with_endpoints"),
        even_body.find("toom8_newton::even"),
    ]
    call_chain = {
        "calls": ordered_calls,
        "first_positions": positions,
        "interpolate_ordered": interpolation_ordered,
        "endpoint_calls": endpoint_calls,
        "endpoint_positions": endpoint_positions,
        "endpoint_ordered": endpoint_ordered,
        "dyadic_pair_to_normalization": (
            "toom8_dyadic_producer::dyadic_pair" in normalization
            and "toom8_normalization::with_endpoints" in even_body
        ),
        "even_normalization_before_newton": all(position >= 0 for position in even_normalization)
        and even_normalization == sorted(even_normalization),
    }

    all_exports = all(export_checks.values())
    all_consumers = all(consumer_checks.values())
    call_chain_pass = all(
        call_chain[key]
        for key in (
            "interpolate_ordered",
            "endpoint_ordered",
            "dyadic_pair_to_normalization",
            "even_normalization_before_newton",
        )
    )
    return {
        "status": "pass" if all_exports and all_consumers and call_chain_pass else "fail",
        "generic_exports": export_checks,
        "runtime_consumers": consumer_checks,
        "call_chain": call_chain,
        "source_scope": "saved interpolation candidate; no production module is modified",
    }


def erasure_gate() -> dict[str, Any]:
    """Inspect saved optimized assembly for proof-only symbols and helpers."""
    assembly_path = INTERPOLATION / "evidence" / "codegen.s"
    assembly = read(assembly_path)
    inspector = load_module(INTERPOLATION / "interpolation_codegen.py", "interpolation_codegen")
    try:
        inspected = inspector.inspect(assembly)
        inspect_status = "pass"
        error = None
    except Exception as exc:  # pragma: no cover - error payload is part of the report
        inspected = None
        inspect_status = "fail"
        error = str(exc)

    proof_patterns = [
        r"toom8_newton_spec",
        r"toom8_dyadic_producer_spec",
        r"toom8_normalization_spec",
        r"toom8_convolution",
    ]
    proof_symbol_hits = {
        pattern: sorted(set(re.findall(pattern, assembly))) for pattern in proof_patterns
    }
    proof_symbols_absent = all(not hits for hits in proof_symbol_hits.values())
    roots_present = all(
        root in assembly for root in ("verified_interpolation_24", "verified_interpolation_48")
    )
    static_pass = inspect_status == "pass" and proof_symbols_absent and roots_present
    return {
        "status": "pass" if static_pass else "fail",
        "mode": "saved optimized assembly inspection",
        "static_proof_symbols_absent": proof_symbols_absent,
        "proof_symbol_hits": proof_symbol_hits,
        "roots_present": roots_present,
        "reachable_code_inspection": inspected,
        "fresh_compilation": False,
        "error": error,
        "limitation": "The saved assembly is not a fresh Verus/Rust compilation and is not a machine-code equivalence proof.",
    }


def words(encoded: str) -> list[int]:
    if encoded == "-":
        return []
    values = [int(item) for item in encoded.split(",")]
    if any(value < 0 or value > MASK for value in values):
        raise ValueError("word outside u64 range")
    return values


def value(words_: list[int]) -> int:
    return sum(word << (U64_BITS * index) for index, word in enumerate(words_))


def digits(number: int, width: int) -> list[int]:
    return [(number >> (U64_BITS * index)) & MASK for index in range(width)]


def independent_layout(command: str) -> list[int]:
    """Recompute the fifteen-coefficient output order without importing its oracle."""
    fields = command.split("|")
    if len(fields) != 6 or fields[0] != "interpolate":
        raise ValueError("malformed interpolation command")
    k = int(fields[1])
    threshold = int(fields[2])
    a = words(fields[3])
    b = words(fields[4])
    extra = int(fields[5])
    if k < 0 or threshold < 24 or extra not in (0, 1, 17) or len(a) != len(b):
        raise ValueError("unsupported interpolation command")
    n = len(a)
    if not (7 * k <= n <= 8 * k):
        raise ValueError("invalid block shape")
    blocks_a = [value(a[index * k : min((index + 1) * k, n)]) for index in range(8)]
    blocks_b = [value(b[index * k : min((index + 1) * k, n)]) for index in range(8)]
    coefficients = [
        sum(blocks_a[index] * blocks_b[degree - index] for index in range(8) if 0 <= degree - index < 8)
        for degree in range(15)
    ]
    block_width = 2 * (k + 1)
    h = n - 7 * k
    output: list[int] = digits(coefficients[0], 2 * k)
    for coefficient_index in (2, 4, 6, 8, 10, 12, 1, 3, 5, 7, 9, 11, 13):
        output.extend(digits(coefficients[coefficient_index], block_width))
    output.extend(digits(coefficients[14], 2 * h))
    return output


def independent_mapping_gate() -> dict[str, Any]:
    oracle = load_module(INTERPOLATION / "interpolation_oracle.py", "interpolation_oracle")
    rows, counts = oracle.cases()
    checked = 0
    for command, expected_text in rows:
        expected = [int(item) for item in expected_text.split()]
        actual = independent_layout(command)
        if actual != expected:
            raise AssertionError(f"coefficient layout mismatch for {command[:80]}")
        checked += 1
    return {
        "status": "pass",
        "cases": checked,
        "counts": counts,
        "layout": "low, six even coefficients, seven odd coefficients, high",
        "independent_from_runner": True,
        "independent_from_verus": True,
    }


def m7_m8_gate(consumer_repo: Path | None) -> dict[str, Any]:
    scope = load_json(HERE / "scope.json")
    receipt_bytes = (HERE / relative(scope["consumer_receipt"])).read_bytes()
    require(digest(receipt_bytes) == scope["consumer_receipt_sha256"], "consumer receipt hash mismatch")
    receipt = json.loads(receipt_bytes)
    head = receipt["head"]
    status_hash = receipt["file_sha256"]["native/proof-status.json"]
    require(receipt["repository"] == "VeriCount" and receipt["solver_consumer_accepted"] is False
            and receipt["compiled_dependency_checked"] is False, "wrong consumer receipt scope")
    if consumer_repo is not None:
        consumer_repo = consumer_repo.resolve()

        def git(*args: str, cwd: Path = consumer_repo) -> str:
            return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.PIPE).strip()

        head = git("rev-parse", "HEAD")
        for rel, wanted in receipt["file_sha256"].items():
            if rel != "native/proof-status.json":
                require(digest((consumer_repo / relative(rel)).read_bytes()) == wanted, f"VeriCount source mismatch: {rel}")
        status_bytes = (consumer_repo / "native/proof-status.json").read_bytes()
        status_hash = digest(status_bytes)
        status = json.loads(status_bytes)
        modules = {m["id"]: {"status": m["status"], "remaining": m["remaining"]}
                   for m in status["modules"] if m["id"] in ("M7", "M8")}
        authority = {key: status["trusted_backend"][key] for key in receipt["trusted_backend_authority"]}
        require(modules == receipt["modules"] and status["arithmetic_dependency"] == receipt["arithmetic_dependency"]
                and authority == receipt["trusted_backend_authority"], "VeriCount M7/M8 or backend authority differs")
        gitlink = git("ls-tree", "HEAD", "third_party/VeriGMP").split()
        require(len(gitlink) == 4 and gitlink[:2] == ["160000", "commit"]
                and gitlink[2] == receipt["verigmp_gitlink"], "VeriCount gitlink mismatch")
        require(git("rev-parse", "HEAD", cwd=consumer_repo / "third_party/VeriGMP") == receipt["verigmp_gitlink"],
                "VeriCount submodule worktree differs from gitlink")
        matches = []
        scan = receipt["candidate_reference_scan"]
        for root in scan["roots"]:
            for path in (consumer_repo / relative(root)).rglob("*.rs"):
                if re.search(scan["pattern"], read(path), re.I):
                    matches.append(path.relative_to(consumer_repo).as_posix())
        require(sorted(matches) == scan["rust_matches"], "VeriCount candidate-reference scan differs")
    return {
        "status": "pass",
        "mode": "live source/status binding" if consumer_repo else "frozen source/status receipt",
        "receipt": "evidence/fresh-20261103/consumer-VeriCount.json",
        "repository": receipt["repository"],
        "head": head,
        "receipt_head": receipt["head"],
        "proof_status_sha256": status_hash,
        "receipt_proof_status_sha256": receipt["file_sha256"]["native/proof-status.json"],
        "verigmp_gitlink": receipt["verigmp_gitlink"],
        "m7": receipt["modules"]["M7"],
        "m8": receipt["modules"]["M8"],
        "trusted_backend": receipt["trusted_backend"],
        "candidate_rust_reference_matches": receipt["candidate_reference_scan"]["rust_matches"],
        "compiled_dependency_checked": False,
        "actual_solver_consumer": False,
        "promotion_effect": "Source/status observation only; no solver consumer acceptance or pin change",
    }


def performance_gate() -> dict[str, Any]:
    target = load_json(REPO / "native" / "performance-target.json")
    benchmarks = read(REPO / "docs" / "benchmarks.md")
    return {
        "status": "blocked",
        "benchmark_run": False,
        "target_status": target.get("status"),
        "gmp_performance_parity_established": target.get("gmp_performance_parity_established", False),
        "solver_acceptance": target.get("solver_acceptance", {}),
        "historical_docs_confirm_unmet_target": "The target remains unmet." in benchmarks,
        "reason": "No performance measurements for this dyadic/interpolation slice; the registered library target remains unmet and solver trace acceptance is separate.",
    }


def git_identity() -> dict[str, Any]:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"], cwd=REPO, capture_output=True, text=True, check=False
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        branch, commit = "unknown", "unknown"
    return {"branch": branch, "head": commit}


def audit(fresh_evidence: Path = FRESH, consumer_repo: Path | None = None,
          reports: dict[str, Path] | None = None) -> dict[str, Any]:
    def checked(operation: Any) -> dict[str, Any]:
        try:
            return operation()
        except Exception as exc:
            return {"status": "fail", "error": f"{type(exc).__name__}: {exc}"}

    source = checked(source_gate)
    erasure = checked(erasure_gate)
    mapping = checked(independent_mapping_gate)
    m7_m8 = checked(lambda: m7_m8_gate(consumer_repo))
    fresh = checked(lambda: audit_fresh(REPO, fresh_evidence, reports))
    performance = checked(performance_gate)
    archives = {
        "interpolation": run_archive_audit(INTERPOLATION / "audit.py"),
        "dyadic": run_archive_audit(DYADIC / "audit.py"),
    }
    audit_checks = {"source_consumer": source, "saved_erasure": erasure, "independent_mapping": mapping,
                    "consumer_status_binding": m7_m8, "fresh_execution_evidence": fresh, **archives}
    if performance["status"] == "fail":
        audit_checks["performance_status_read"] = performance
    failures = [name for name, result in audit_checks.items() if result["status"] != "pass"]
    scoped_pass = not failures
    return {
        "status": "scoped_progress" if scoped_pass else "fail",
        "scope": "Generic dyadic proof exports, actual interpolation candidate, same-source fresh execution evidence and independent coefficient layout",
        "identity": git_identity(),
        "audit_failures": failures,
        "archive_audits": archives,
        "source_consumer": source,
        "proof_erasure": erasure,
        "independent_mapping": mapping,
        "m7_m8_contract": m7_m8,
        "fresh_execution_evidence": fresh,
        "performance": performance,
        "gates": {
            "scoped_audit": scoped_pass,
            "semantic_mapping": mapping["status"] == "pass" and source["status"] == "pass",
            "static_proof_erasure": erasure["status"] == "pass",
            "historical_archive_integrity": all(item.get("status") == "pass" for item in archives.values()),
            "fresh_verus_evidence": fresh["status"] == "pass",
            "fresh_runner_evidence": fresh["status"] == "pass",
            "consumer_status_binding": m7_m8["status"] == "pass",
            "verification_rerun_in_this_audit": False,
            "runner_reexecuted_in_this_audit": False,
            "performance": False,
            "independent_review_for_promotion": False,
            "m7_m8_solver_consumer": False,
            "promotion": False,
        },
        "blockers": [
            "Independent acceptance of this scoped feature is pending; the retained fresh gates were root-executed.",
            "No performance measurements for this slice; overall GMP parity and the registered performance target remain unestablished.",
            "No accepted dyadic solver consumer; VeriCount M7 is spec_only and M8 is conditional_composition in the frozen receipt.",
        ],
        "promotion": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-evidence", type=Path, help="Copy of the registered manifest.json and evidence.zip")
    parser.add_argument("--dyadic-report", type=Path, help="Registered dyadic verification.json beside its captured inputs, logs and artifacts")
    parser.add_argument("--interpolation-report", type=Path, help="Registered interpolation verification.json beside its captured inputs, logs and artifacts")
    parser.add_argument("--consumer-repo", type=Path, help="Optionally bind the frozen status receipt to a local VeriCount checkout")
    args = parser.parse_args()
    if bool(args.dyadic_report) != bool(args.interpolation_report):
        parser.error("supply both --dyadic-report and --interpolation-report")
    if args.dyadic_report and args.fresh_evidence:
        parser.error("choose either a fresh archive or the pair of raw reports")
    reports = None
    if args.dyadic_report:
        if args.dyadic_report.name != "verification.json" or args.interpolation_report.name != "verification.json":
            parser.error("raw reports must be named verification.json")
        reports = {"dyadic": args.dyadic_report, "interpolation": args.interpolation_report}
    report = audit(args.fresh_evidence or FRESH, args.consumer_repo, reports)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["gates"]["scoped_audit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

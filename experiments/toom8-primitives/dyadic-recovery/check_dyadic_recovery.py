"""Audit the scoped dyadic-recovery consumer and its current acceptance gates.

This is a source/evidence audit. It intentionally does not present the saved
Verus logs or assembly as a fresh proof or benchmark. The script checks the
actual generic exports and call chain, replays the coefficient-to-buffer layout
with an independent integer implementation, and records the gates that still
block promotion to a production or solver backend.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INTERPOLATION = REPO / "experiments" / "toom8-primitives" / "interpolation"
DYADIC = REPO / "experiments" / "toom8-primitives" / "dyadic"
SAT_REPO = REPO.parent / "sat-counting-lab-src"
SAT_STATUS = SAT_REPO / "native" / "proof-status.json"

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


def m7_m8_gate() -> dict[str, Any]:
    if not SAT_STATUS.exists():
        return {"status": "blocked", "error": f"missing {SAT_STATUS}"}
    status = load_json(SAT_STATUS)
    modules = {module.get("id"): module for module in status.get("modules", [])}
    m7 = modules.get("M7", {})
    m8 = modules.get("M8", {})
    rust_hits: list[str] = []
    if SAT_REPO.exists():
        for path in (SAT_REPO / "native").rglob("*.rs"):
            text = read(path).lower()
            if "toom8" in text or "dyadic_pair" in text or "dyadic recovery" in text:
                rust_hits.append(str(path.relative_to(SAT_REPO)))
    expected = m7.get("status") == "spec_only" and m8.get("status") == "conditional_composition"
    return {
        "status": "pass" if expected else "fail",
        "m7": {"status": m7.get("status"), "remaining": m7.get("remaining")},
        "m8": {"status": m8.get("status"), "remaining": m8.get("remaining")},
        "sat_rust_consumer_hits": rust_hits,
        "actual_solver_consumer": bool(rust_hits),
        "promotion_effect": "M7/M8 remain outside this arithmetic archive; no solver pin is changed",
    }


def toolchain_gate() -> dict[str, Any]:
    native = {name: shutil.which(name) for name in ("rustc", "cargo", "verus")}
    wsl = shutil.which("wsl")
    wsl_tools: dict[str, str | None] = {}
    if wsl:
        for name in ("rustc", "cargo", "verus"):
            try:
                result = subprocess.run(
                    [wsl, "bash", "-lc", f"command -v {name}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                wsl_tools[name] = result.stdout.strip() or None
            except (OSError, subprocess.TimeoutExpired):
                wsl_tools[name] = None
    available = {name: bool(path) for name, path in native.items()}
    return {
        "native": native,
        "wsl": wsl_tools,
        "fresh_verus_run": False,
        "fresh_rust_runner_run": False,
        "fresh_toolchain_available": all(available.values()) or all(bool(wsl_tools.get(name)) for name in available),
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
        "reason": "No local rustc/cargo/verus toolchain and no fresh GMP comparison run are available in this checkout.",
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


def audit() -> dict[str, Any]:
    source = source_gate()
    erasure = erasure_gate()
    mapping = independent_mapping_gate()
    m7_m8 = m7_m8_gate()
    tools = toolchain_gate()
    performance = performance_gate()
    archives = {
        "interpolation": run_archive_audit(INTERPOLATION / "audit.py"),
        "dyadic": run_archive_audit(DYADIC / "audit.py"),
    }
    blockers = [
        "Fresh Verus/Rust verification and compiled runner execution were not available in the local Windows/WSL environment.",
        "No fresh GMP benchmark was run; the registered performance target remains unmet.",
        "The SAT consumer has no dyadic-recovery pin; M7 is spec_only and M8 is conditional_composition.",
    ]
    if tools["fresh_toolchain_available"]:
        blockers[0] = "This audit does not invoke a fresh Verus/Rust run; run the pinned gate separately before promotion."
    return {
        "status": "scoped_progress",
        "scope": "Generic dyadic proof exports, actual interpolation consumer, static erasure and independent coefficient-layout evidence",
        "identity": git_identity(),
        "archive_audits": archives,
        "source_consumer": source,
        "proof_erasure": erasure,
        "independent_mapping": mapping,
        "m7_m8_contract": m7_m8,
        "toolchain": tools,
        "performance": performance,
        "gates": {
            "semantic_mapping": mapping["status"] == "pass" and source["status"] == "pass",
            "static_proof_erasure": erasure["status"] == "pass",
            "historical_archive_integrity": all(item.get("status") == "pass" for item in archives.values()),
            "fresh_verus": False,
            "fresh_runner": False,
            "performance": False,
            "independent_review_for_promotion": False,
            "m7_m8_solver_consumer": False,
            "promotion": False,
        },
        "blockers": blockers,
        "promotion": False,
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

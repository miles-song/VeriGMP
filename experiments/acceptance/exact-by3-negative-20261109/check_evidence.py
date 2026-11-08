#!/usr/bin/env python3
"""Offline checker for the exact-by3 E1 evidence-only NO-GO archive.

The checker reads only the committed archives and repository metadata.  It never
launches a benchmark, compiler, Verus, emulator, or external process other than
the read-only git commands used for the evidence-only path audit.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


PRIMARY = [
    (1, 512, 63), (1, 513, 63), (1, 1023, 63), (1, 1024, 63),
    (1, 1025, 63), (1, 2048, 63), (1, 4096, 63),
    (2, 511, 63), (2, 512, 63), (2, 513, 63), (2, 1023, 63),
    (2, 1024, 63), (2, 1025, 63), (2, 2048, 63), (2, 4096, 63),
]
RUN_NAMES = ("run1", "run2")


def fail(message: str) -> None:
    raise AssertionError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def close(actual: float, expected: float, label: str, tol: float = 1e-12) -> None:
    require(math.isclose(actual, expected, rel_tol=tol, abs_tol=tol),
            f"{label}: {actual!r} != {expected!r}")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_zip_member(zf: zipfile.ZipFile, name: str) -> bytes:
    try:
        return zf.read(name)
    except KeyError as exc:
        fail(f"missing archive member: {name}")
        raise exc


def archive_digest(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha_bytes(data)


def load_json_member(zf: zipfile.ZipFile, name: str) -> Any:
    return json.loads(read_zip_member(zf, name).decode("utf-8"))


def member_digest(zf: zipfile.ZipFile, name: str) -> tuple[int, str]:
    data = read_zip_member(zf, name)
    return len(data), sha_bytes(data)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def check_repo_scope(package: Path, manifest: dict[str, Any]) -> None:
    repo = package
    while repo != repo.parent and not (repo / ".git").exists():
        repo = repo.parent
    require((repo / ".git").exists(), "repository root is not discoverable")
    base = manifest["base"]["commit"]
    base_tree = manifest["base"]["tree"]
    current = run_git(repo, "rev-parse", "HEAD")
    require(run_git(repo, "rev-parse", f"{base}^{{tree}}") == base_tree,
            "base commit tree does not match manifest")
    names = run_git(repo, "diff", "--name-only", base, current).splitlines()
    prefix = manifest["package_path"].rstrip("/") + "/"
    require(names, "evidence commit has no changed paths")
    require(all(name.startswith(prefix) for name in names),
            f"non-evidence path changed: {names}")
    require(not run_git(repo, "diff", "--name-only", base, current, "--", "native"),
            "native path changed")
    require(not run_git(repo, "diff", "--name-only", base, current, "--", "Cargo.toml", "Cargo.lock"),
            "build manifest changed")


def check_archive_members(
    zf: zipfile.ZipFile,
    expected: dict[str, dict[str, Any]],
    label: str,
) -> None:
    names = [info.filename for info in zf.infolist()]
    require(len(names) == len(expected), f"{label}: member count mismatch")
    require(set(names) == set(expected), f"{label}: member set mismatch")
    for name, spec in expected.items():
        info = zf.getinfo(name)
        require(info.file_size == spec["bytes"], f"{label}/{name}: byte count mismatch")
        require(sha_bytes(zf.read(name)) == spec["sha256"], f"{label}/{name}: sha256 mismatch")


def count_raw(raw: bytes) -> dict[str, Any]:
    counts: dict[tuple[str, str], int] = {}
    paths: set[tuple[int, int, int, str]] = set()
    repetitions: dict[int, int] = {}
    lines = raw.splitlines()
    for line in lines:
        row = json.loads(line)
        key = (row.get("kind"), row.get("record"))
        counts[key] = counts.get(key, 0) + 1
        paths.add((row["op"], row["n"], row["top"], row["path"]))
        repetitions[row["repetition"]] = repetitions.get(row["repetition"], 0) + 1
    return {"lines": len(lines), "counts": counts, "paths": paths, "repetitions": repetitions}


def geomean(values: list[float]) -> float:
    return math.exp(sum(math.log(value) for value in values) / len(values))


def check_run(
    zf: zipfile.ZipFile,
    run_name: str,
    spec: dict[str, Any],
    build_sha: str,
    primary: list[tuple[int, int, int]],
) -> dict[str, Any]:
    dir_name = "exact-by3-run-1" if run_name == "run1" else "exact-by3-run-2"
    base = f"window/measurement-E1-01/{dir_name}"
    measurement_name = f"{base}/measurement.json"
    raw_name = f"{base}/raw.jsonl"
    measurement = load_json_member(zf, measurement_name)
    raw = read_zip_member(zf, raw_name)
    require(measurement["status"] == "pass", f"{run_name}: status is not pass")
    require(measurement["build_sha256"] == build_sha, f"{run_name}: build sha mismatch")
    require(measurement["raw_sha256"] == spec["raw_sha256"], f"{run_name}: raw sha mismatch")
    require(sha_bytes(raw) == spec["raw_sha256"], f"{run_name}: raw bytes mismatch")
    summaries = measurement["summaries"]
    require(len(summaries) == 86, f"{run_name}: summary count is not 86")
    keys = {(row["op"], row["n"], row["top"]) for row in summaries}
    require(len(keys) == 86, f"{run_name}: summary keys are not unique")
    raw_stats = count_raw(raw)
    require(raw_stats["lines"] == 6192, f"{run_name}: raw line count is not 6192")
    require(raw_stats["paths"] == {(op, n, top, path) for op, n, top in keys for path in ("baseline", "candidate", "gmp")},
            f"{run_name}: raw path set mismatch")
    require(raw_stats["counts"] == {
        ("calibration", "invocation"): 258,
        ("calibration", "outcome"): 258,
        ("calibration", "result"): 258,
        ("sample", "invocation"): 1806,
        ("sample", "outcome"): 1806,
        ("sample", "result"): 1806,
    }, f"{run_name}: raw record count mismatch")
    require(raw_stats["repetitions"] == {-1: 774, 0: 774, 1: 774, 2: 774, 3: 774, 4: 774, 5: 774, 6: 774},
            f"{run_name}: repetition count mismatch")
    by_key = {(row["op"], row["n"], row["top"]): row for row in summaries}
    primary_values = [by_key[key]["candidate_over_baseline"] for key in primary]
    primary_geomean = geomean(primary_values)
    all_cell_max = max(row["candidate_over_baseline"] for row in summaries)
    close(primary_geomean, spec["primary_geomean"], f"{run_name}: primary geomean")
    close(all_cell_max, spec["all_cell_max"], f"{run_name}: all-cell max")
    return {
        "primary_geomean": primary_geomean,
        "all_cell_max": all_cell_max,
        "raw_sha256": spec["raw_sha256"],
        "raw_lines": raw_stats["lines"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    package = args.package.resolve()
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["schema"] == "verigmp-exact-by3-negative-evidence-v1", "schema mismatch")
    require(manifest["verdict"] == "NO-GO", "archive is not marked NO-GO")
    require(manifest["disposition"] == "evidence-only", "archive disposition is not evidence-only")
    check_repo_scope(package, manifest)

    raw_path = package / "raw-window.zip"
    astra_path = package / "astra-evidence.zip"
    raw_bytes, raw_sha = archive_digest(raw_path)
    astra_bytes, astra_sha = archive_digest(astra_path)
    require(raw_bytes == manifest["archives"]["raw_window"]["bytes"], "raw archive byte count mismatch")
    require(raw_sha == manifest["archives"]["raw_window"]["sha256"], "raw archive sha mismatch")
    require(astra_bytes == manifest["archives"]["astra_evidence"]["bytes"], "Astra archive byte count mismatch")
    require(astra_sha == manifest["archives"]["astra_evidence"]["sha256"], "Astra archive sha mismatch")

    with zipfile.ZipFile(raw_path) as raw_zip, zipfile.ZipFile(astra_path) as astra_zip:
        check_archive_members(raw_zip, manifest["raw_members"], "raw-window")
        check_archive_members(astra_zip, manifest["astra_members"], "astra-evidence")
        plan = load_json_member(raw_zip, "window/plan.json")
        root_grant = load_json_member(raw_zip, "window/root-go-E1.json")
        host = load_json_member(raw_zip, "window/measurement-E1-01/host-receipt.json")
        adjudication = load_json_member(astra_zip, "astra/e1-adjudication.json")

        ids = manifest["identities"]
        require(sha_bytes(read_zip_member(raw_zip, "window/plan.json")) == ids["plan_sha256"], "plan sha mismatch")
        require(sha_bytes(read_zip_member(raw_zip, "window/root-go-E1.json")) == ids["root_grant_sha256"], "root grant sha mismatch")
        require(sha_bytes(read_zip_member(raw_zip, "window/measurement-E1-01/host-receipt.json")) == ids["host_receipt_sha256"], "host receipt sha mismatch")
        require(sha_bytes(read_zip_member(astra_zip, "astra/e1-adjudication.json")) == ids["astra_adjudication_sha256"], "Astra adjudication sha mismatch")
        require(adjudication["verdict"] == "NO-GO", "Astra verdict is not NO-GO")
        require(adjudication["checks_failed"] == [], "Astra structural checks are not empty")
        require(adjudication["reviewer_executed_timing"] is False, "reviewer timing unexpectedly executed")
        require(adjudication["reviewer_executed_calibration"] is False, "reviewer calibration unexpectedly executed")
        require(adjudication["raw_gate"]["raw_integrity"] == "pass", "raw integrity is not pass")
        require(host["avd_restored"] is True, "AVD restore was not recorded")
        require(host["benchmark_launched"] is True, "host receipt does not record benchmark launch")
        require(host["pause_method"] == "adb_pause_plus_authorized_exact_held_handle_ntsuspend", "pause method mismatch")
        require(len(host["commands"]) == 14 and all(c["returncode"] == 0 for c in host["commands"]), "host command receipt mismatch")
        require(all(r["status"] == "resumed" and r["nt_status"] == 0 for r in host["resume"]), "host resume receipt mismatch")
        for receipt in host["preflight_receipts"]:
            member = "window/measurement-E1-01/" + Path(receipt["path"]).name
            require(member in manifest["raw_members"], f"preflight member missing: {member}")
            require(manifest["raw_members"][member]["sha256"] == receipt["sha256"], f"preflight sha mismatch: {member}")

        require(plan["source"]["head"] == ids["source_head"], "plan source head mismatch")
        require(plan["source"]["tree"] == ids["source_tree"], "plan source tree mismatch")
        require(plan["source"]["native_tree"] == ids["native_tree"], "plan native tree mismatch")
        require(plan["build"]["sha256"] == ids["build_sha256"], "plan build sha mismatch")
        require(plan["protocol"]["authoritative"]["sha256"] == ids["protocol_sha256"], "plan protocol sha mismatch")
        require(root_grant["explicit_root_go"] is True, "root grant is not explicit")
        require(root_grant["timing_authorized"] is True, "historical root grant not recorded")

        for run_name, spec in manifest["runs"].items():
            check_run(raw_zip, run_name, spec, ids["build_sha256"], PRIMARY)
        gate = adjudication["raw_gate"]
        for run_name in RUN_NAMES:
            close(gate[run_name]["primary_geomean"], manifest["runs"][run_name]["primary_geomean"], f"{run_name}: adjudication primary")
            close(gate[run_name]["all_cell_max"], manifest["runs"][run_name]["all_cell_max"], f"{run_name}: adjudication max")
        close(gate["control_drift_geomean"], manifest["gates"]["control_drift_geomean"], "control drift geomean")
        close(gate["control_drift_range"][0], manifest["gates"]["control_drift_min"], "control drift min")
        close(gate["control_drift_range"][1], manifest["gates"]["control_drift_max"], "control drift max")
        require(gate["run1"]["primary_pass"] is False and gate["run2"]["primary_pass"] is False, "primary gate is not a two-run failure")
        require(gate["run1"]["all_cell_pass"] is False and gate["run2"]["all_cell_pass"] is True, "all-cell gate result changed")
        require(gate["control_drift_pass"] is False, "control drift gate is not a failure")

    print("PASS exact-by3 E1 evidence-only archive")
    print(f"  package={package}")
    print(f"  verdict={manifest['verdict']} raw_sha={raw_sha} astra_sha={astra_sha}")
    print("  checked=50 raw members, 16 Astra members, 2 runs, 86 cells/run, 6192 raw records/run")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

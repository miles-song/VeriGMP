"""Audit optimized candidate assembly without timing it."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def functions(assembly: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in re.finditer(
        r"(?ms)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,", assembly)}


def calls(body: str) -> list[str]:
    return sorted(set(re.findall(r"(?m)^\s*(?:callq?|jmp)\s+([^\s]+)", body)))


def audit(assembly_path: Path, source_path: Path) -> dict:
    assembly = assembly_path.read_text(errors="replace")
    source = source_path.read_text()
    bodies = functions(assembly)
    roots = [name for name in ("verified_product", "verified_square") if name in bodies]
    report = {
        "status": "inspection-only",
        "assembly_sha256": hashlib.sha256(assembly_path.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "candidate_source_guard": "if k==threshold && ax[k]==0 && bx[k]==0" in source,
        "candidate_branch_source_line": next((i for i, line in enumerate(source.splitlines(), 1)
                                               if "if k==threshold && ax[k]==0 && bx[k]==0" in line), None),
        "roots": roots,
        "functions": sorted(bodies),
        "instruction_counts": {
            "conditional_branches": len(re.findall(r"(?m)^\s*(?:cmp|test|j[a-z]+)\b", assembly)),
            "calls": len(re.findall(r"(?m)^\s*callq?\b", assembly)),
            "bounds_panics": len(re.findall(r"panic_bounds_check", assembly)),
            "general_division": len(re.findall(r"(?m)^\s*i?div[bwlq]?\s", assembly)),
        },
        "reachable_calls": {name: calls(bodies[name]) for name in roots},
        "interpretation": "Static assembly facts only; source-to-assembly build provenance must be established separately.",
    }
    if not report["candidate_source_guard"]:
        raise RuntimeError("candidate guard anchor missing from source")
    if set(roots) != {"verified_product", "verified_square"}:
        raise RuntimeError("expected assembly roots are missing")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.assembly, args.source)
    with args.out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

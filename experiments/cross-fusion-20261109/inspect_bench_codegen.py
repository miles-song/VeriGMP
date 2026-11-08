#!/usr/bin/env python3
"""Check actual benchmark dispatch paths in both linked x86-64 executables."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(row, candidate):
    for key in ("path", "symbols", "disassembly", "relocations"):
        if sha(row[key]) != row[key + "_sha256"]:
            raise RuntimeError("binary or inspection input changed: " + key)
    symbols = Path(row["symbols"]).read_text()
    disassembly = Path(row["disassembly"]).read_text()
    relocations = Path(row["relocations"]).read_text()
    symbol_map = {int(m[1], 16): m[2] for m in re.finditer(
        r"^([0-9a-f]+) [A-Za-z] ((?:verigmp|bench)::[^\n]+)$", symbols, re.M)}
    relocation_map = {int(m[1], 16): symbol_map.get(int(m[2], 16)) for m in re.finditer(
        r"^([0-9a-f]+)\s+\S+\s+R_X86_64_RELATIVE\s+([0-9a-f]+)$", relocations, re.M)}
    names = ["bench::main", "bench::apply", "verigmp::arithmetic::mul_mod",
             "verigmp::arithmetic::square_mod", "verigmp::fast_multiply::low",
             "verigmp::fast_multiply::full", "verigmp::fast_words::combine_cross",
             "verigmp::square_low::low", "verigmp::toom_square::full",
             "verigmp::square::full", "verigmp::toom_low::low"]
    addresses, bodies, calls = {}, {}, {}
    for name in names:
        match = re.search(r"^([0-9a-f]+) <" + re.escape(name) + r">:\n(.*?)(?=^[0-9a-f]+ <|\Z)",
                          disassembly, re.M | re.S)
        if not match:
            raise RuntimeError("missing code body: " + name)
        addresses[name] = "0x" + match[1]
        bodies[name] = match[2]
        calls[name] = []
        for line in match[2].splitlines():
            indirect = re.search(r"^\s*([0-9a-f]+):\s+(?:call|jmp)\s+\*.*?#\s*([0-9a-f]+)", line)
            direct = re.search(r"^\s*([0-9a-f]+):\s+(?:call|jmp)\s+[0-9a-f]+\s+<([^>+]+)>", line)
            if indirect:
                target = relocation_map.get(int(indirect[2], 16))
                site = indirect[1]
            elif direct:
                target, site = direct[2], direct[1]
            else:
                continue
            if target in names:
                calls[name].append(dict(site="0x" + site, target=target))
    required = [("bench::main", "bench::apply")]
    required += [("bench::apply", "verigmp::" + name) for name in
                 ("arithmetic::mul_mod", "arithmetic::square_mod", "fast_multiply::full", "square::full")]
    required += [("verigmp::" + caller, "verigmp::" + callee) for caller, callee in
                 (("arithmetic::mul_mod", "fast_multiply::low"),
                  ("arithmetic::mul_mod", "toom_low::low"),
                  ("fast_multiply::low", "fast_multiply::full"),
                  ("fast_multiply::full", "fast_words::combine_cross"),
                  ("arithmetic::square_mod", "square_low::low"),
                  ("square_low::low", "toom_square::full"),
                  ("toom_square::full", "square::full"))]
    if not candidate:
        required.append(("verigmp::square::full", "verigmp::fast_words::combine_cross"))
    for caller, callee in required:
        if not any(call["target"] == callee for call in calls[caller]):
            raise RuntimeError("missing linked call edge: " + caller + " -> " + callee)
    instructions = {}
    for name in ("verigmp::fast_words::combine_cross", "verigmp::square::full"):
        instructions[name] = {}
        for instruction in ("adc", "not", "sub"):
            instructions[name][instruction] = ["0x" + address for address in re.findall(
                r"^\s*([0-9a-f]+):\s+" + instruction + r"\s", bodies[name], re.M)]
    if not instructions["verigmp::fast_words::combine_cross"]["adc"]:
        raise RuntimeError("missing carry instructions in combine_cross")
    if candidate and any(not instructions[name][op] for name in instructions for op in ("adc", "not")):
        raise RuntimeError("candidate fusion instructions absent from combine_cross or inlined square")
    if not candidate and not instructions["verigmp::fast_words::combine_cross"]["sub"]:
        raise RuntimeError("baseline subtract pass absent")
    if "$0x200" not in bodies["verigmp::arithmetic::mul_mod"]:
        raise RuntimeError("512-limb default multiplication boundary not found")
    return dict(binary_sha256=row["path_sha256"], addresses=addresses, required_edges=required,
                calls=calls, instructions=instructions,
                square_cross="inlined instruction evidence" if candidate else "direct call")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: inspect_bench_codegen.py BUILD_JSON OUTPUT_JSON")
    build_path, output = map(Path, sys.argv[1:])
    if output.exists():
        raise RuntimeError("refusing to overwrite inspection report")
    build = json.loads(build_path.read_text())
    script = Path(__file__).resolve()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    relative = "experiments/cross-fusion-20261109/inspect_bench_codegen.py"
    if subprocess.run(["git", "show", commit + ":" + relative], check=True, capture_output=True).stdout != script.read_bytes():
        raise RuntimeError("inspection source differs from its commit")
    result = dict(status="pass", build_sha256=sha(build_path), inspector_commit=commit,
                  inspector_sha256=sha(script),
                  baseline=inspect(build["binaries"]["baseline"], False),
                  candidate=inspect(build["binaries"]["candidate"], True))
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(report=str(output), sha256=sha(output), status=result["status"])))


if __name__ == "__main__":
    main()

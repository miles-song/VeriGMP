#!/usr/bin/env python3
"""Check selected x86-64 paths in a linked executable and retain their addresses."""
import json
import pathlib
import re
import sys

if len(sys.argv) != 5:
    raise SystemExit("usage: codegen.py DISASSEMBLY SYMBOLS RELOCATIONS RUNNER_SHA256")
disassembly, symbols, relocations = (pathlib.Path(path).read_text() for path in sys.argv[1:4])
symbol_map = {int(m[1], 16): m[2] for m in re.finditer(
    r"^([0-9a-f]+) [A-Za-z] (verigmp::[^\n]+)$", symbols, re.M)}
relocation_map = {int(m[1], 16): symbol_map.get(int(m[2], 16)) for m in re.finditer(
    r"^([0-9a-f]+)\s+\S+\s+R_X86_64_RELATIVE\s+([0-9a-f]+)$", relocations, re.M)}
names = ["arithmetic::mul_mod", "arithmetic::square_mod", "fast_multiply::low",
         "fast_multiply::full", "fast_words::combine_cross", "square_low::low",
         "toom_square::full", "square::full", "toom_low::low"]
bodies = {}
edges = {}
addresses = {}
for short in names:
    name = "verigmp::" + short
    match = re.search(r"^([0-9a-f]+) <" + re.escape(name) + r">:\n(.*?)(?=^[0-9a-f]+ <|\Z)",
                      disassembly, re.M | re.S)
    if not match:
        raise RuntimeError(f"missing code body: {name}")
    addresses[short] = "0x" + match[1]
    bodies[short] = match[2]
    slots = [int(m, 16) for m in re.findall(
        r"\b(?:call|jmp)\s+\*[^\n]*?\s#\s*([0-9a-f]+)", match[2])]
    targets = [relocation_map[slot] for slot in slots if relocation_map.get(slot)]
    targets += re.findall(r"\b(?:call|jmp)\s+[0-9a-f]+\s+<(verigmp::[^>+]+)>", match[2])
    edges[short] = sorted(set(target.removeprefix("verigmp::") for target in targets))

required = [("arithmetic::mul_mod", "fast_multiply::low"),
            ("arithmetic::mul_mod", "toom_low::low"),
            ("fast_multiply::low", "fast_multiply::full"),
            ("fast_multiply::full", "fast_words::combine_cross"),
            ("arithmetic::square_mod", "square_low::low"),
            ("square_low::low", "toom_square::full"),
            ("toom_square::full", "square::full")]
for caller, callee in required:
    if callee not in edges[caller]:
        raise RuntimeError(f"missing direct or relocation-resolved edge {caller} -> {callee}")
for function in ("fast_words::combine_cross", "square::full"):
    for instruction in ("adc", "not"):
        if not re.search(r"\b" + instruction + r"\s", bodies[function]):
            raise RuntimeError(f"missing {instruction} in {function}")
if "$0x200" not in bodies["arithmetic::mul_mod"]:
    raise RuntimeError("missing 512-limb multiplication dispatch comparison")
print(json.dumps({"runner_sha256": sys.argv[4], "symbol_addresses": addresses,
                  "resolved_edges": edges, "required_edges": required,
                  "observations": ["512-limb multiply dispatch comparison",
                                   "adc and not in combine_cross and square::full"]},
                 indent=2, sort_keys=True))

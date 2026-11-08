"""Independent fixtures and guard census for the Toom -1 boundary candidate.

The expected product is computed only from Python arbitrary integers.  The
Rust runner is a separate executable that calls the source under test and
returns words; it never receives an expected product.  This module has no
timing or calibration code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

WORD_BITS = 64
BASE = 1 << WORD_BITS
WORD_MASK = BASE - 1
MAGIC = b"VGMPBN01"
SEEDS = (0x20261109, 0x2026110A, 0x2026110B, 0x2026110C)
DEFAULT_NS = tuple(range(737, 747))
FORCED_NS = tuple(range(573, 578))
PRIMARY_NS = tuple(range(740, 744))


def integer(words: list[int]) -> int:
    value = 0
    for index, word in enumerate(words):
        value |= int(word) << (WORD_BITS * index)
    return value


def limbs(value: int, count: int) -> list[int]:
    return [(value >> (WORD_BITS * i)) & WORD_MASK for i in range(count)]


def split_blocks(words: list[int], k: int) -> tuple[list[int], list[int], list[int]]:
    assert len(words) >= 2 * k
    return words[:k], words[k:2 * k], words[2 * k:]


def negative_value_and_high(words: list[int], k: int) -> tuple[int, int, bool]:
    """Return signed -1 value, its magnitude high word, and its sign."""
    a0, a1, a2 = split_blocks(words, k)
    signed = integer(a0) + integer(a2) - integer(a1)
    magnitude = abs(signed)
    return signed, magnitude >> (WORD_BITS * k), signed < 0


def deterministic_words(seed: int, n: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.getrandbits(WORD_BITS) for _ in range(n)]


def boundary_blocks(inner_n: int, high_zero: bool, negative: bool) -> list[int]:
    """Construct a prefix with a known -1 high word.

    For high_zero, both positive and negative evaluations are represented.  A
    non-zero high word requires a positive carry because negative() reverses a
    subtraction into a k+1-limb magnitude with a zero high limb.
    """
    k = (inner_n + 2) // 3
    h = inner_n - 2 * k
    assert h <= k
    a0 = [0] * k
    a1 = [0] * k
    a2 = [0] * h
    if high_zero:
        if negative:
            a1[0] = 1
        else:
            a0[0] = 2
            a1[0] = 1
    else:
        assert not negative
        a0 = [WORD_MASK] * k
        a2[0] = 1
    words = a0 + a1 + a2
    signed, high, observed_negative = negative_value_and_high(words, k)
    assert observed_negative == negative
    assert (high == 0) == high_zero
    assert signed != 0
    return words


def outer_prefix(n: int, words: list[int], seed: int) -> list[int]:
    """Embed an inner Toom prefix into a default low-product operand."""
    h = (n // 40) * 9 + ((n % 40) * 9) // 40
    inner_n = n - h
    assert len(words) == inner_n
    tail = deterministic_words(seed ^ 0x6A09E667F3BCC909, h)
    return words + tail


def expected(op: int, a: list[int], b: list[int], top: int, shared: bool) -> list[int]:
    product = integer(a) * integer(a if op in (2, 3) or shared else b)
    if op == 0:
        return limbs(product, 2 * len(a))
    modulus = 1 << (WORD_BITS * (len(a) - 1) + top)
    return limbs(product % modulus, len(a))


def append_case(cases: list[dict], op: int, a: list[int], b: list[int], *,
                threshold: int, top: int, low: int, split: int,
                extra: int, shared: bool, label: str, seed: int | None = None) -> None:
    assert len(a) == len(b) and len(a) > 0
    output = expected(op, a, b, top, shared)
    cases.append({
        "id": len(cases), "op": op, "n": len(a), "threshold": threshold,
        "top": top, "low": low, "split": split, "extra": extra,
        "shared": shared, "label": label, "seed": seed,
        "a": a, "b": b, "expected": output,
    })


def build_cases() -> list[dict]:
    cases: list[dict] = []
    for seed in SEEDS:
        for n in FORCED_NS:
            a = deterministic_words(seed ^ (n << 8) ^ 0x1111, n)
            b = deterministic_words(seed ^ (n << 16) ^ 0x2222, n)
            append_case(cases, 0, a, b, threshold=192, top=64, low=128,
                        split=2, extra=(n & 3), shared=False,
                        label=f"forced-random-n{n}", seed=seed)
        for n in DEFAULT_NS:
            a = deterministic_words(seed ^ (n << 8) ^ 0x3333, n)
            b = deterministic_words(seed ^ (n << 16) ^ 0x4444, n)
            append_case(cases, 1, a, b, threshold=192, top=63, low=128,
                        split=2, extra=(n & 3), shared=False,
                        label=f"default-random-n{n}", seed=seed)
            append_case(cases, 2, a, b, threshold=192, top=63, low=128,
                        split=2, extra=17, shared=True,
                        label=f"default-shared-n{n}", seed=seed)

    # Four TT/TF/FT/FF high-word combinations at each primary shape.  The
    # high-zero side is exercised with both signed evaluations; a high-false
    # side necessarily has a positive carry in negative().
    for n in PRIMARY_NS:
        h = (n // 40) * 9 + ((n % 40) * 9) // 40
        inner_n = n - h
        for high_a, high_b in ((True, True), (True, False),
                               (False, True), (False, False)):
            for neg_a, neg_b in ((False, False), (True, False),
                                 (False, True), (True, True)):
                if (not high_a and neg_a) or (not high_b and neg_b):
                    continue
                a0 = boundary_blocks(inner_n, high_a, neg_a)
                b0 = boundary_blocks(inner_n, high_b, neg_b)
                a = outer_prefix(n, a0, 0xA5A5 ^ n ^ (int(high_a) << 8))
                b = outer_prefix(n, b0, 0x5A5A ^ n ^ (int(high_b) << 8))
                label = (f"guard-a{'T' if high_a else 'F'}-b"
                         f"{'T' if high_b else 'F'}-sign-{int(neg_a)}{int(neg_b)}-n{n}")
                append_case(cases, 1, a, b, threshold=192, top=63, low=128,
                            split=2, extra=23, shared=False, label=label)

    # Regression patterns cover zero, all-one, alternating carry chains, and a
    # legal shared square at both sides of the dispatch boundary.
    for n in (573, 574, 575, 576, 577, 739, 740, 741, 742, 743, 744, 745, 746):
        zero = [0] * n
        ones = [WORD_MASK] * n
        carry = [WORD_MASK if i % 2 == 0 else 0 for i in range(n)]
        append_case(cases, 0 if n <= 577 else 1, zero, ones,
                    threshold=192, top=63 if n > 577 else 64, low=128,
                    split=2, extra=31, shared=False, label=f"zero-one-n{n}")
        append_case(cases, 0 if n <= 577 else 1, carry, carry,
                    threshold=192, top=63 if n > 577 else 64, low=128,
                    split=2, extra=37, shared=True, label=f"alternating-square-n{n}")
    # Keep modular edge bits separate from full multiplication: top is ignored
    # by op 0. Op 2 deliberately carries a different, unused b in the fixture.
    for n in (739, 740, 743, 744):
        a = deterministic_words(0xB001 ^ n, n)
        b = deterministic_words(0xB002 ^ n, n)
        for top in (1, 64):
            append_case(cases, 1, a, b, threshold=192, top=top, low=128,
                        split=2, extra=0, shared=False,
                        label=f"mul-mod-top{top}-n{n}")
            append_case(cases, 2, a, b, threshold=192, top=top, low=128,
                        split=2, extra=11, shared=True,
                        label=f"mul-mod-shared-top{top}-n{n}")

    # These outer square sizes place the first cross-product full multiply at
    # each inner n in 573..577 (square_low uses 11/36 splits twice).
    for n in (2697, 2704, 2707, 2714, 2717):
        a = deterministic_words(0x5A0A ^ n, n)
        for top in (1, 63, 64):
            append_case(cases, 3, a, a, threshold=192, top=top, low=64,
                        split=1, extra=13, shared=True,
                        label=f"square-mod-cross-top{top}-n{n}")
    return cases


def corpus_manifest(cases: list[dict]) -> dict:
    return {
        "format": "VGMPBN01",
        "python": sys.version,
        "word_bits": WORD_BITS,
        "seeds": [hex(seed) for seed in SEEDS],
        "forced_full_n": list(FORCED_NS),
        "default_n": list(DEFAULT_NS),
        "primary_n": list(PRIMARY_NS),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "case_count": len(cases),
        "definition": "expected values are Python arbitrary integer products and power-of-two reductions",
    }


def serialize_cases(cases: list[dict]) -> tuple[bytes, bytes, bytes]:
    raw = bytearray(MAGIC + struct.pack("<Q", len(cases)))
    rows = []
    expected_raw = bytearray(MAGIC + struct.pack("<Q", len(cases)))
    for case in cases:
        raw.extend(struct.pack("<9Q", case["id"], case["op"], case["n"],
                               case["threshold"], case["top"], case["low"],
                               case["split"], case["extra"], int(case["shared"])))
        expected_raw.extend(struct.pack("<Q", case["id"]))
        for key in ("a", "b"):
            vector = case[key]
            raw.extend(struct.pack("<Q", len(vector)))
            raw.extend(struct.pack("<" + "Q" * len(vector), *vector))
        output = case["expected"]
        expected_raw.extend(struct.pack("<Q", len(output)))
        expected_raw.extend(struct.pack("<" + "Q" * len(output), *output))
        rows.append({k: case[k] for k in ("id", "op", "n", "threshold", "top",
                                          "low", "split", "extra", "shared",
                                          "label", "seed")})
    rows_raw = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
    return bytes(raw), bytes(expected_raw), rows_raw


def write_fixture(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=False)
    cases = build_cases()
    raw, expected_raw, rows_raw = serialize_cases(cases)
    (root / "cases.bin").write_bytes(raw)
    (root / "expected.bin").write_bytes(expected_raw)
    (root / "cases.jsonl").write_bytes(rows_raw)
    manifest = corpus_manifest(cases)
    manifest.update({
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "expected_sha256": hashlib.sha256(expected_raw).hexdigest(),
        "cases_jsonl_sha256": hashlib.sha256(rows_raw).hexdigest(),
    })
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def checked_cases(root: Path) -> list[dict]:
    cases = build_cases()
    raw, expected_raw, rows_raw = serialize_cases(cases)
    manifest = json.loads((root / "manifest.json").read_text())
    for name, data, field in (("cases.bin", raw, "fixture_sha256"),
                              ("expected.bin", expected_raw, "expected_sha256"),
                              ("cases.jsonl", rows_raw, "cases_jsonl_sha256")):
        if (root / name).read_bytes() != data or manifest[field] != hashlib.sha256(data).hexdigest():
            raise RuntimeError(f"fixture regeneration mismatch: {name}")
    if manifest["generator_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise RuntimeError("fixture generator identity mismatch")
    return cases


def verify_output(root: Path, runner: Path, report_path: Path, raw_dir: Path) -> dict:
    cases = checked_cases(root)
    fixture = root / "cases.bin"
    raw_dir.mkdir(parents=True, exist_ok=False)
    result = subprocess.run([str(runner), str(fixture)], capture_output=True, text=True, check=False, timeout=120)
    (raw_dir / "oracle.stdout").write_text(result.stdout)
    (raw_dir / "oracle.stderr").write_text(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Rust oracle failed: {result.stderr[-1000:]}")
    actual: dict[int, list[int]] = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if not fields:
            continue
        case_id = int(fields[0])
        if case_id in actual:
            raise RuntimeError(f"duplicate oracle row {case_id}")
        actual[case_id] = [int(word) for word in fields[1:]]
    if set(actual) != set(range(len(cases))):
        raise RuntimeError("Rust oracle omitted or added fixture rows")
    mismatches = []
    for case in cases:
        if actual[case["id"]] != case["expected"]:
            mismatches.append({"id": case["id"], "label": case["label"]})
    invalid = subprocess.run([str(runner), "--invalid"], capture_output=True, text=True, check=False, timeout=120)
    (raw_dir / "invalid.stdout").write_text(invalid.stdout)
    (raw_dir / "invalid.stderr").write_text(invalid.stderr)
    if invalid.returncode != 0 or invalid.stdout.strip() != "invalid-boundary-pass cases=7":
        raise RuntimeError(f"invalid boundary gate failed: {invalid.stdout} {invalid.stderr}")
    report = {
        "status": "semantic-mismatch" if mismatches else "pass",
        "cases": len(cases),
        "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "invalid_output": invalid.stdout.strip(),
        "mismatches": mismatches,
        "expected_definition": "Python arbitrary integers only",
    }
    with report_path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(report, indent=2) + "\n")
    return report


def census(root: Path, report_path: Path) -> dict:
    cases = checked_cases(root)
    rows = []
    for case in cases:
        n = case["n"]
        if case["op"] == 0:
            scope = "full"
            a = case["a"]
            b = a if case["shared"] else case["b"]
            inner_n, threshold = n, case["threshold"]
        elif case["op"] in (1, 2):
            if n < 512:
                raise RuntimeError("census needs a separate model for the fast mul_mod path")
            scope = "mul_mod_shared" if case["op"] == 2 or case["shared"] else "mul_mod"
            h = n * 9 // 40
            inner_n, threshold = n - h, 192
            a = case["a"][:inner_n]
            b = a if case["op"] == 2 or case["shared"] else case["b"][:inner_n]
        elif case["op"] == 3:
            scope = "square_mod_cross"
            h = n * 11 // 36
            if n <= 64 or h <= 64:
                raise RuntimeError("census needs a separate model for the short square path")
            inner_n, threshold = h - h * 11 // 36, 192
            a = case["a"][n - h:n - h + inner_n]
            b = case["a"][:inner_n]
        else:
            raise RuntimeError(f"unsupported operation {case['op']}")
        if inner_n <= threshold:
            continue
        k = (inner_n + 2) // 3
        signed_a, high_a, neg_a = negative_value_and_high(a, k)
        signed_b, high_b, neg_b = negative_value_and_high(b, k)
        both = high_a == 0 and high_b == 0
        rows.append({"id": case["id"], "op": case["op"], "scope": scope,
                     "n": n, "inner_n": inner_n, "k": k, "threshold": threshold,
                     "label": case["label"], "top": case["top"] if case["op"] else None,
                     "high_a_zero": high_a == 0, "high_b_zero": high_b == 0,
                     "negative_a": neg_a, "negative_b": neg_b,
                     "signed_a_hex": hex(signed_a), "signed_b_hex": hex(signed_b),
                     "candidate_guard": k == threshold and both,
                     "broadened_guard": both})
    counts: dict[str, dict] = {}
    for row in rows:
        key = row["scope"]
        group = counts.setdefault(key, {"rows": 0, "TT": 0, "TF": 0, "FT": 0, "FF": 0,
                                        "candidate_guard": 0, "broadened_only": 0,
                                        "by_threshold": {}})
        pair = ("T" if row["high_a_zero"] else "F") + ("T" if row["high_b_zero"] else "F")
        group["rows"] += 1
        group[pair] += 1
        group["candidate_guard"] += int(row["candidate_guard"])
        group["broadened_only"] += int(row["broadened_guard"] and not row["candidate_guard"])
        stratum = "k_eq_threshold" if row["k"] == row["threshold"] else "k_ne_threshold"
        strata = group["by_threshold"].setdefault(stratum, {"TT": 0, "TF": 0, "FT": 0, "FF": 0})
        strata[pair] += 1
    report = {
        "status": "pass",
        "source": "independent Python model of first reachable full multiply, not a recursive or runtime trace",
        "rows": len(rows),
        "scope_counts": counts,
        "rows_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
    }
    with report_path.open("x", encoding="utf-8") as f:
        f.write(json.dumps({"report": report, "rows": rows}, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--out", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--runner", type=Path, required=True)
    verify.add_argument("--report", type=Path, required=True)
    verify.add_argument("--raw-dir", type=Path, required=True)
    count = sub.add_parser("census")
    count.add_argument("--root", type=Path, required=True)
    count.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        print(json.dumps(write_fixture(args.out), indent=2))
    elif args.command == "verify":
        report = verify_output(args.root, args.runner, args.report, args.raw_dir)
        print(json.dumps(report, indent=2))
        if report["status"] != "pass":
            raise SystemExit(2)
    else:
        print(json.dumps(census(args.root, args.report), indent=2))


if __name__ == "__main__":
    main()

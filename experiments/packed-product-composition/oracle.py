#!/usr/bin/env python3
"""Independent arbitrary-integer fixtures for the actual packed-product client."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

MASK = (1 << 64) - 1
PRECISIONS = (1, 7, 17, 29, 30, 31, 53, 63, 64, 65, 70, 95,
              126, 127, 128, 129, 255, 257, 521, 1025, 2049, 4097)


def limbs(p):
    return (p - 1) // 64 + 1


def words(value, length):
    assert 0 <= value < 1 << (64 * length)
    return [(value >> (64 * i)) & MASK for i in range(length)]


def byte_words(values):
    return b"".join(struct.pack("<Q", value) for value in values)


def values(n, p, pattern, rng):
    if n == 0:
        return []
    maximum = (1 << p) - 1
    if pattern == "random":
        return [rng.getrandbits(p) for _ in range(n)]
    if pattern == "maximum":
        return [maximum] * n
    if pattern == "zero":
        return [0] * n
    if pattern == "alternating":
        return [maximum if i % 2 == 0 else 0 for i in range(n)]
    if pattern == "impulse":
        return [maximum if i == n // 2 else 0 for i in range(n)]
    raise ValueError(pattern)


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0x5041434B50524F44)
    shapes = []
    for p in PRECISIONS:
        for n in (0, 1, 2, 3, 7, 17, 33):
            for padding in (0, 1):
                shapes.append((n, p, padding, "random", 0))
        for pattern in ("maximum", "zero", "alternating", "impulse"):
            shapes.append((9, p, 2, pattern, 3))
    # Consecutive counts straddle a guard-bit jump at an exact slot-word edge.
    for p, counts in ((30, (16, 17)), (62, (16, 17)), (126, (16, 17)),
                      (29, (64, 65)), (61, (64, 65)), (125, (64, 65)),
                      (31, (4, 5)), (63, (4, 5)), (95, (4, 5)), (127, (4, 5))):
        for n in counts:
            for padding in (0, 1, 3):
                shapes.append((n, p, padding, "maximum", 0))
    for p in (7, 17, 53):
        for n in (65, 127, 257, 1024):
            shapes.append((n, p, 0, "random", 0))
    for p in (129, 257, 521, 1025, 2049, 4097):
        shapes.append((65, p, 1, "random", 0))
    # Zero count permits the widest machine precision without giant allocation.
    shapes += [(0, MASK, 0, "zero", 0), (0, MASK, MASK - limbs(MASK), "zero", 0)]

    rows = []
    fixture = output / "cases.bin"
    with fixture.open("wb") as stream:
        stream.write(b"VGMPPRD1" + struct.pack("<Q", len(shapes)))
        for case_id, (n, p, padding, pattern, extra_guard) in enumerate(shapes):
            g = (n - 1).bit_length() if n else 0
            q = 2 * p + g + extra_guard if n else p
            slot = max(limbs(p), limbs(q)) + padding
            a = values(n, p, pattern, rng)
            # Unequal operands catch accidental replacement of product by square.
            b_pattern = "random" if pattern in ("alternating", "impulse") else pattern
            b = values(n, p, b_pattern, rng)
            left = [word for value in a for word in words(value, limbs(p))]
            right = [word for value in b for word in words(value, limbs(p))]
            packed_left = [word for value in a for word in words(value, slot)]
            packed_right = [word for value in b for word in words(value, slot)]
            integer_left = sum(value << (64 * slot * i) for i, value in enumerate(a))
            integer_right = sum(value << (64 * slot * i) for i, value in enumerate(b))
            integer_product = integer_left * integer_right
            product = words(integer_product, 2 * n * slot)

            # Define the expected polynomial solely by finite coefficient sums.
            coefficients = [0] * (2 * n)
            for i, ai in enumerate(a):
                for j, bj in enumerate(b):
                    coefficients[i + j] += ai * bj
            assert not n or coefficients[-1] == 0
            assert all(0 <= value < 1 << q for value in coefficients)
            # Independent whole-integer product must agree with every slot.
            assert all((integer_product >> (64 * slot * k))
                       & ((1 << (64 * slot)) - 1) == value
                       for k, value in enumerate(coefficients))
            expected = [word for value in coefficients for word in words(value, limbs(q))]
            vectors = (left, right, packed_left, packed_right, product, expected)
            scratch_extra = case_id % 4
            stream.write(struct.pack("<6Q", case_id, n, p, q, slot, scratch_extra))
            for vector in vectors:
                stream.write(struct.pack("<Q", len(vector)))
                stream.write(byte_words(vector))
            rows.append(dict(id=case_id, n=n, p=p, q=q, slot=slot, guard_bits=g,
                             extra_guard_bits=extra_guard, padding=padding, pattern=pattern,
                             right_pattern=b_pattern, scratch_extra=scratch_extra,
                             vector_lengths=[len(vector) for vector in vectors],
                             vector_sha256=[hashlib.sha256(byte_words(vector)).hexdigest()
                                            for vector in vectors], zero_tail=True))
    with (output / "cases.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    return dict(status="pass", cases=len(rows), maximum_nonempty_precision=max(PRECISIONS),
                maximum_count=max(row["n"] for row in rows), precisions=list(PRECISIONS),
                largest_empty_precision=MASK, binary_sha256=hashlib.file_digest(
                    fixture.open("rb"), "sha256").hexdigest(),
                expected_definition="independent finite coefficient sums with Python integers",
                intermediate_check="independent whole-integer product and all exact radix slots",
                runtime_executed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    print(json.dumps(generate(parser.parse_args().output), indent=2))

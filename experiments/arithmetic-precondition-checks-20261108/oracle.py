"""Independent exact-integer fixtures for the single changed kernel and callers."""
import hashlib
import itertools
import json
from pathlib import Path
import random
import struct

MAX = (1 << 64) - 1
SEED = 0x434845434B46554C
SIZES = (*range(1, 35), 47, 48, 49, 63, 64, 65, 95, 96, 97, 127, 128, 129,
         191, 192, 193, 255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 2048, 4096)


def integer(words):
    return sum(word << (64 * i) for i, word in enumerate(words))


def limbs(value, n):
    return [(value >> (64 * i)) & MAX for i in range(n)]


def generate(output, key_shapes):
    output = Path(output)
    output.mkdir(exist_ok=False)
    rng = random.Random(SEED)
    cases = []
    def add(op, a, b, threshold=24, top=64, shared=False):
        n = len(a)
        value = integer(a) * integer(a if shared or op == 4 else b)
        length = 2*n if op <= 1 else n
        if op > 1:
            value %= 1 << (64*(n-1)+top)
        cases.append((op, n, threshold, top, len(cases) % 4, shared, a, b, limbs(value, length)))
    for n in SIZES:
        h = n//2
        k = n-h
        random_pair = ([rng.getrandbits(64) for _ in range(n)],
                       [rng.getrandbits(64) for _ in range(n)])
        equal_half = [rng.getrandbits(64) for _ in range(h)]
        equal = equal_half + [0]*(k-h) + equal_half
        pairs = [random_pair, ([MAX]*n, [MAX]*n), ([0]*n, [MAX]*n), (equal, equal)]
        for sign_a, sign_b in itertools.product((False, True), repeat=2):
            a = [0]*k+[MAX]*h if sign_a else [MAX]*k+[0]*h
            b = [0]*k+[MAX]*h if sign_b else [MAX]*k+[0]*h
            pairs.append((a, b))
        for a, b in pairs:
            for threshold in (8, 24, 64):
                add(0, a, b, threshold)
        add(0, *random_pair, MAX)  # Largest threshold: public leaf path.
        add(0, *random_pair, 24, shared=True)  # Legal aliased shared inputs.
    # Actual Toom/full and default modular consumers of the changed worker.
    for n, top in key_shapes:
        pairs = [([rng.getrandbits(64) for _ in range(n)],
                  [rng.getrandbits(64) for _ in range(n)]), ([MAX]*n, [MAX]*n),
                 ([0]*n, [MAX]*n)]
        for a, b in pairs:
            for op in (1, 2, 3, 4):
                add(op, a, b, 24 if op == 1 else 192, top)
        a, b = pairs[0]
        add(3, a, b, 192, top, shared=True)
    raw = output / "cases.bin"
    rows = []
    with raw.open("wb") as stream:
        stream.write(b"VGMPCHK1" + struct.pack("<Q", len(cases)))
        for i, (op, n, threshold, top, extra, shared, a, b, expected) in enumerate(cases):
            stream.write(struct.pack("<7Q", i, op, n, threshold, top, extra, shared))
            hashes = []
            for vector in (a, b, expected):
                data = struct.pack("<"+str(len(vector))+"Q", *vector)
                stream.write(struct.pack("<Q", len(vector)) + data)
                hashes.append(hashlib.sha256(data).hexdigest())
            rows.append(dict(id=i, op=op, n=n, threshold=threshold, top=top, extra=extra,
                             shared=shared, left_right_expected_sha256=hashes))
    with (output / "cases.jsonl").open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True)+"\n")
    return dict(cases=len(cases), seed=SEED, max_limbs=max(SIZES),
                raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                definition="Python arbitrary integers, independent exact product and power-of-two modulus",
                operations={0:"fast_full", 1:"toom_full", 2:"fast_default", 3:"default_mul", 4:"default_square"})

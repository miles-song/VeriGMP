#!/usr/bin/env python3
"""Check the linked library against independently evaluated Python integers."""
import collections
import hashlib
import json
import random
import subprocess
import sys

B = 1 << 64
MASK = B - 1
SEED = 20261109
rng = random.Random(SEED)
cases = []
expected = []
counts = collections.Counter()


def number(words):
    return sum(word << (64 * i) for i, word in enumerate(words))


def limbs(value, n):
    return [(value >> (64 * i)) & MASK for i in range(n)]


def add_cross(z0, z2, d, plus, alias=False):
    n, m = len(z0), len(z2)
    assert len(d) == n and m <= n
    if alias:
        assert z2 == z0[n - m:]
    total = number(z0) + number(z2) + (number(d) if plus else -number(d))
    if not 0 <= total < 2 * B**n:
        return False
    args = [int(alias), n, m, int(plus), *d, *z0]
    if not alias:
        args.extend(z2)
    cases.append("cross " + " ".join(map(str, args)))
    expected.append([total // B**n, *limbs(total, n)])
    counts["cross"] += 1
    counts["plus" if plus else "minus"] += 1
    counts["alias" if alias else "separate"] += 1
    counts["empty" if n == 0 else "tail" if m < n else "full_prefix"] += 1
    return True


for plus in (False, True):
    add_cross([], [], [], plus)
    add_cross([MASK, 0], [MASK, 0], [MASK if plus else 0, 0], plus)
    add_cross([MASK, MASK, 0], [MASK], [MASK if plus else 0, MASK if plus else 0, 0], plus)
    add_cross([MASK], [MASK], [0], plus)
    add_cross([MASK], [1], [0], plus)
    add_cross([1], [0], [0 if plus else 1], plus)
    if plus:
        add_cross([MASK], [MASK], [1], plus)
    if not plus:
        add_cross([0, 1], [], [1, 0], plus)

lengths = [0, 1, 2, 3, 4, 8, 9, 16, 17, 31, 32, 33, 64, 65, 127, 128, 129]
for _ in range(6000):
    n = rng.choice(lengths)
    m = rng.choice([0, n, rng.randrange(n + 1)])
    alias = rng.randrange(3) == 0
    z0 = [rng.choice([0, MASK, rng.getrandbits(64)]) for _ in range(n)]
    z2 = z0[n - m:] if alias else [rng.choice([0, MASK, rng.getrandbits(64)]) for _ in range(m)]
    d = [rng.choice([0, MASK, rng.getrandbits(64)]) for _ in range(n)]
    add_cross(z0, z2, d, bool(rng.randrange(2)), alias)


def add_product(op, a, b, parameter):
    n = len(a)
    same_input = op in ("square", "default_square", "full_same", "default_same")
    full = op in ("full", "full_same", "square")
    result = number(a) * number(a if same_input else b)
    if not full:
        result %= 1 << (64 * (n - 1) + parameter)
    args = [n, parameter, *a]
    if not same_input:
        args.extend(b)
    cases.append(op + " " + " ".join(map(str, args)))
    expected.append(limbs(result, 2 * n if full else n))
    counts[op] += 1


for n in [1, 7, 8, 9, 10, 15, 16, 17, 23, 24, 25, 31, 32, 33, 47, 48, 49, 63, 64, 65, 95, 96, 97, 127, 128, 129]:
    k = n - n // 2
    patterns = [
        ([0] * n, [MASK] * n),
        ([MASK] * n, [MASK] * n),
        ([MASK] * k + [0] * (n - k), [0] * k + [MASK] * (n - k)),
        ([0] * k + [MASK] * (n - k), [MASK] * k + [0] * (n - k)),
        ([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(64) for _ in range(n)]),
    ]
    for a, b in patterns:
        for threshold in [8, 24]:
            add_product("full", a, b, threshold)
            add_product("square", a, a, threshold)
            add_product("full_same", a, a, threshold)
        for top in [1, 63, 64]:
            add_product("default_mul", a, b, top)
            add_product("default_square", a, a, top)
            add_product("default_same", a, a, top)

for n in [191, 192, 193, 255, 256, 257, 511, 512, 513, 1023, 1024, 1025]:
    a = [rng.getrandbits(64) for _ in range(n)]
    b = [rng.getrandbits(64) for _ in range(n)]
    for top in [1, 64]:
        add_product("default_mul", a, b, top)
        add_product("default_square", a, a, top)
        add_product("default_same", a, a, top)

payload = ("\n".join(cases) + "\n").encode()
result = subprocess.run([sys.argv[1]], input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
lines = result.stdout.splitlines()
assert len(lines) == len(expected), (len(lines), len(expected), result.stderr.decode())
for index, (actual, wanted) in enumerate(zip(lines, expected)):
    parsed = [int(x) for x in actual.split()]
    assert parsed == wanted, (index, cases[index], parsed, wanted)
print(json.dumps({"seed": SEED, "counts": dict(counts), "cases": len(cases),
                  "input_sha256": hashlib.sha256(payload).hexdigest(),
                  "output_sha256": hashlib.sha256(result.stdout).hexdigest()}, sort_keys=True))

"""Integer meanings for generic scaled subtraction; no executable-output oracle."""
from collections import Counter
import random

SEED = 20261110
B = 1 << 64
MASK = B - 1

def words(value, count):
    return [(value >> (64 * i)) & MASK for i in range(count)]

def record(word, n, m, dst, rhs):
    assert 0 <= m <= n and 0 <= word <= MASK
    assert 0 <= rhs < 1 << (64 * m)
    assert word * rhs <= dst < 1 << (64 * n)
    command = 'subscaled ' + ' '.join(map(str, [word, n, m, *words(dst, n), *words(rhs, m)]))
    return command, ' '.join(map(str, words(dst - word * rhs, n)))

def cases():
    rng = random.Random(SEED)
    rows = []
    lengths = [0, 1, 2, 3, 4, 7, 8, 9, 23, 24, 25, 63, 64, 65, 127, 128, 129, 255, 256, 257, 511, 512, 513, 1024, 4096]
    multipliers = [0, 1, 2, 3, 4, 16, 64, (1 << 32) - 1, 1 << 32, 1 << 63, MASK - 1, MASK]
    for n in lengths:
        capacity = (1 << (64 * n)) - 1
        for m in sorted({0, n, n // 2, max(0, n - 1)}):
            rhs_capacity = (1 << (64 * m)) - 1
            for word in multipliers:
                bound = min(rhs_capacity, capacity // word) if word else rhs_capacity
                values = [0, min(1, bound), bound, max(0, bound - 1), rng.randrange(bound + 1)]
                for index, rhs in enumerate(values):
                    available = capacity - word * rhs
                    residue = [0, min(1, available), available, available // 2, rng.randrange(available + 1)][index]
                    rows.append(record(word, n, m, word * rhs + residue, rhs))
    # The first limb makes combined carry MAX; the next multiplication has
    # high == word == MAX and low == 0, so the subtraction borrow must be zero.
    rows.append(record(MASK, 3, 2, MASK * B * B, B * B - 1))
    for n in [2, 3, 9, 65, 257, 1024, 4096]:
        # Long borrow into padded zero limbs, and long full-word combined carry.
        rows.append(record(1, n, 1, B ** (n - 1), 1))
        rhs = B ** (n - 1) - 1
        rows.append(record(MASK, n, n - 1, MASK * B ** (n - 1), rhs))
    return rows

def invalid():
    return ['subscaled', 'subscaled 1 0', 'subscaled 1 0 1 1',
            'subscaled 1 1 1 0 1', 'subscaled 18446744073709551615 1 1 0 18446744073709551615',
            'subscaled 1 1 0', 'subscaled 1 0 0 0', 'subscaled 1 1 2 0 0 0']

def summary():
    rows = cases()
    return {'seed': SEED, 'cases': len(rows), 'max_limbs': 4096,
            'by_operation': dict(Counter(command.split()[0] for command, _ in rows)),
            'invalid_commands': len(invalid()),
            'coverage': 'Full-u64 multipliers including zero/MAX; empty destination and RHS; equal/short/padded RHS; exact zero/max output; carry==word==MAX with next high==word; long borrow/carry chains; canaries and immutable RHS'}

if __name__ == '__main__':
    import json
    print(json.dumps(summary(), indent=2))

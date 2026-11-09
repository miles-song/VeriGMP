"""Independent integer cases; executes no clocks or benchmark commands."""
import hashlib
import json
from pathlib import Path
import random

MASK = (1 << 64) - 1
SHAPES = (1, 2, 7, 8, 9, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25,
          29, 30, 31, 39, 40, 41, 43, 44, 45, 46, 47, 48, 63, 64, 65,
          127, 128, 129, 191, 192, 193, 255, 256, 257, 511, 512, 513,
          1023, 1024, 1025, 2047, 2048, 2049, 4095, 4096, 4097)


def words(value, n):
    return ','.join(f'{(value >> (64 * i)) & MASK:016x}' for i in range(n))


def cases(candidate):
    rng = random.Random(0xF17ED51A20261109)
    for n in SHAPES:
        for pattern in ('zero', 'max', 'alternating', 'onehot', 'random'):
            if pattern == 'zero':
                a, b = 0, 0
            elif pattern == 'max':
                a = b = (1 << (64 * n)) - 1
            elif pattern == 'alternating':
                a = sum((MASK if i % 2 else 0) << (64 * i) for i in range(n))
                b = sum((0 if i % 2 else MASK) << (64 * i) for i in range(n))
            elif pattern == 'onehot':
                a, b = 1 << rng.randrange(64 * n), 1 << rng.randrange(64 * n)
            else:
                a, b = rng.getrandbits(64 * n), rng.getrandbits(64 * n)
            for top in (1, 32, 63, 64):
                for op in ('mul', 'square', 'gmp_mul', 'gmp_square'):
                    answer = a * (a if 'square' in op else b)
                    answer %= 1 << (64 * (n - 1) + top)
                    yield dict(n=n, pattern=pattern, top=top, threshold=192, op=op, a=a, b=b, answer=answer, q=n)
            for op, threshold in [('full', 192), ('forced', 24), ('forced', 8)]:
                yield dict(n=n, pattern=pattern, top=64, threshold=threshold, op=op, a=a, b=b, answer=a*b, q=2*n)
            if n in (15, 20, 22, 23):
                for op in (('direct', 'control', 'base') if candidate else ('control', 'base')):
                    yield dict(n=n, pattern=pattern, top=64, threshold=24, op=op, a=a, b=b, answer=a*b, q=2*n)


def check(binary, output, run, candidate):
    rows = list(cases(candidate))
    source = ''.join(f'{i} {r["op"]} {r["top"]} {r["threshold"]} 7 {words(r["a"],r["n"])} {words(r["b"],r["n"])}\n'
                     for i, r in enumerate(rows)).encode()
    (output / 'input.txt').write_bytes(source)
    r = run('oracle', [str(binary)], source, 60)
    assert r['returncode'] == 0, 'ordinary runner failed'
    answers = (output / 'oracle.stdout').read_text().splitlines()
    assert len(answers) == len(rows), (len(answers), len(rows))
    for i, (line, row) in enumerate(zip(answers, rows)):
        assert line == f'{i} ' + words(row['answer'], row['q']), (i, row['n'], row['op'], row['pattern'])
    report = dict(status='pass', cases=len(rows), shape_count=len(SHAPES), patterns=['zero','max','alternating','onehot','random'],
                  top_values=[1,32,63,64], imported_actual_native=True, benchmark_samples=0,
                  oracle='Python unbounded integer multiplication and exact power-of-two remainder; GMP comparator separately checked',
                  buffer_checks='dirty output; input frames; exact passed scratch capacity; outer dst/scratch canaries and seven-word unborrowed scratch suffix',
                  raw={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [output/'input.txt', output/'oracle.stdout', output/'oracle.stderr']})
    (output / 'oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

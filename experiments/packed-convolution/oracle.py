"""Independent Python integer checks for the mathematical packing contract."""
import itertools
import json
import random


def convolution(a, b):
    out = [0] * (len(a) + len(b))
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def pack(a, radix):
    return sum(x * radix**i for i, x in enumerate(a))


def check(output):
    records = output / 'oracle-cases.jsonl'
    count = 0
    fixtures = []
    with records.open('w', encoding='utf-8') as stream:
        def case(incoming_a, incoming_b, p, d, word_aligned=False):
            nonlocal count
            modulus = 1 << p
            full_a = [x % modulus for x in incoming_a]
            full_b = [x % modulus for x in incoming_b]
            a, b = full_a[:d], full_b[:d]
            shorter = min(len(a), len(b))
            guard = (shorter - 1).bit_length() if shorter else 0
            width = 2 * p + guard
            if word_aligned:
                width = 64 * ((width + 63) // 64)
            radix = 1 << width
            coefficients = convolution(a, b)
            packed_product = pack(a, radix) * pack(b, radix)
            assert packed_product == pack(coefficients, radix)
            assert all(0 <= x < radix for x in coefficients)
            expected = convolution(full_a, full_b)[:d]
            expected += [0] * (d - len(expected))
            extracted = [(packed_product >> (width * k)) % modulus for k in range(d)]
            assert extracted == [x % modulus for x in expected]
            if not a or not b or not d:
                assert packed_product == 0
            stream.write(json.dumps(dict(a=incoming_a, b=incoming_b, p=p, d=d,
                word_aligned=word_aligned, w=width, coefficients=coefficients,
                extracted=extracted, packed_product_hex=hex(packed_product))) + '\n')
            count += 1
            if (len(fixtures) < 8 and p == 2 and len(a) == 2 and len(b) == 2
                    and all(a) and all(b)):
                fixtures.append(dict(a=a, b=b, radix=radix, k=1,
                                     coefficient=coefficients[1], product=packed_product))

        for p in (1, 2):
            vectors = [list(a) for n in range(4)
                       for a in itertools.product(range(1 << p), repeat=n)]
            for a in vectors:
                for b in vectors:
                    case(a, b, p, max(len(a), len(b)))
        for p in (1, 2, 3, 31, 32, 33, 63, 64, 65, 127, 128, 129, 255):
            modulus = 1 << p
            for n, m in ((0, 0), (0, 3), (1, 1), (1, 7), (3, 5), (8, 8), (17, 4)):
                for d in (0, 1, 2, 3, max(n, m), n + m + 3):
                    for aligned in (False, True):
                        case([modulus - 1] * n, [modulus - 1] * m, p, d, aligned)
                        case(([-modulus - 1, -1, modulus, modulus + 1] * ((n + 3) // 4))[:n],
                             ([modulus + 2, 0, -2, 1] * ((m + 3) // 4))[:m], p, d, aligned)
        rng = random.Random(0x4B524F4E)
        for _ in range(500):
            p = rng.choice((1, 7, 63, 64, 65, 127, 129, 255))
            a = [rng.randrange(-(1 << (p + 1)), 1 << (p + 1)) for _ in range(rng.randrange(18))]
            b = [rng.randrange(-(1 << (p + 1)), 1 << (p + 1)) for _ in range(rng.randrange(18))]
            case(a, b, p, rng.randrange(36), bool(rng.randrange(2)))

    # General integer product identity is also valid for signed coefficients.
    signed_cases = 0
    for radix in (-3, 0, 1, 3, 17):
        for a, b in (([-3, 4], [5, -7, 2]), ([], [-1]), ([1], [2])):
            assert pack(convolution(a, b), radix) == pack(a, radix) * pack(b, radix)
            signed_cases += 1
    # A concrete undersized-slot counterexample must exhibit actual carry damage.
    a = b = [3, 3]
    wrong_radix = 16
    assert convolution(a, b)[1] == 18
    assert (pack(a, wrong_radix) * pack(b, wrong_radix) // wrong_radix**2) % 4 != 9 % 4
    fixtures += [dict(a=[3, 3], b=[3, 3], radix=32, k=1, coefficient=18, product=9801),
                 dict(a=[-3, 4], b=[5, -7, 2], radix=17, k=1,
                      coefficient=41, product=pack([-3, 4], 17)*pack([5, -7, 2], 17))]
    for p in (63, 64, 65, 127, 128, 129):
        a, b = [(1 << p) - 1, 2], [3, (1 << p) - 1]
        radix = 1 << (64 * ((2 * p + 1 + 63) // 64))
        fixtures.append(dict(a=a, b=b, radix=radix, k=1,
            coefficient=convolution(a, b)[1], product=pack(a, radix)*pack(b, radix)))
    fixture_source = ['extern crate packed_model;', 'use vstd::prelude::*;',
                      'use packed_model::packed_convolution::*;', 'verus! {']
    for i, item in enumerate(fixtures):
        def seq(values):
            return 'seq![' + ','.join(str(x) + 'int' for x in values) + ']'
        sa, sb = seq(item['a']), seq(item['b'])
        fixture_source += [f'proof fn oracle_{i}() {{',
            f'    assert(coefficient({sa},{sb},{item["k"]})=={item["coefficient"]}int) by(compute);',
            f'    assert(packed({sa},{item["radix"]}int)*packed({sb},{item["radix"]}int)=={item["product"]}int) by(compute);',
            '}']
    fixture_source.append('}')
    (output / 'oracle-fixtures.rs').write_text('\n'.join(fixture_source) + '\n', encoding='utf-8')
    return dict(canonical_cases=count, signed_identity_cases=signed_cases,
                model_fixture_count=len(fixtures), undersized_radix_counterexample=True,
                seed='0x4b524f4e', runtime_implementation_tested=False)

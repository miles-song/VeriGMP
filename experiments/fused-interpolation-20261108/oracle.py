"""Independent Python integer fixtures; this module runs no native code or timing."""
import hashlib
import itertools
import json
from pathlib import Path
import random
import struct

MAX = (1 << 64) - 1
SEED = 20261108
DIRECT_SIZES = (0, 1, 2, 3, 4, 7, 8, 9, 15, 16, 17, 24, 25, 63, 64, 65,
                127, 128, 129, 511, 512, 513, 1023, 1024, 1025, 2048, 4096)
FULL_SIZES = (1, 2, 7, 8, 9, 23, 24, 25, 31, 32, 33, 47, 48, 49, 63, 64, 65,
              127, 128, 129, 191, 192, 193, 255, 256, 257, 511, 512, 513,
              1023, 1024, 1025, 2048, 4096)


def integer(words):
    return sum(word << (64*i) for i, word in enumerate(words))


def limbs(value, count):
    assert 0 <= value < 1 << (64*count)
    return [(value >> (64*i)) & MAX for i in range(count)]


def minimal(value):
    return limbs(value, (value.bit_length()+63)//64)


def cases(key_shapes):
    rng = random.Random(SEED)
    # row = (operation, parameter, top, extra_workspace, shared_input, vectors)
    for n, shift in itertools.product(DIRECT_SIZES, (1, 4)):
        bound = (1 << (64*n)) - 1
        for m in sorted({0, max(0, n-1), n}):
            limit = min((1 << (64*m))-1, bound >> shift)
            values = {0, limit, rng.randrange(limit+1)}
            if limit:
                values.add(1)
                values.add(min(limit, (1 << (64*max(1, m-1)))-1))
            for rhs in sorted(values):
                shifted = rhs << shift
                destinations = {shifted, bound, shifted+rng.randrange(bound-shifted+1)}
                if n and (1 << (64*(n-1))) >= shifted:
                    destinations.add(1 << (64*(n-1)))
                for dst in sorted(destinations):
                    yield 0, shift, 0, 0, False, [limbs(dst,n), limbs(rhs,m), limbs(dst-shifted,n)]
    for n in DIRECT_SIZES:
        cap = ((1 << (64*n))-1)//64
        coefficients = [[0]*5, [cap//15*(i+1) for i in range(5)],
                        [cap//2, cap//2, 0, 0, 0]]
        coefficients += [[cap if i == j else 0 for i in range(5)] for j in range(5)]
        coefficients += [[rng.randrange(cap//5+1) for _ in range(5)] for _ in range(3)]
        for c in coefficients:
            assert 64*sum(c) < 1 << (64*n)
            signed = c[0]-c[1]+c[2]-c[3]+c[4]
            signs = (False,True) if signed == 0 else (signed < 0,)
            for negative in signs:
                # Alternate minimal/padded z0/z4, including empty zero slices.
                z0 = minimal(c[0]) if n % 2 else limbs(c[0],n)
                z4 = limbs(c[4],n) if n % 2 else minimal(c[4])
                values = [z0, limbs(c[1],n), limbs(c[2],n), limbs(c[3],n), z4,
                          limbs(sum(c),n), limbs(abs(signed),n),
                          limbs(sum((1 << i)*x for i,x in enumerate(c)),n),
                          limbs(c[1],n), limbs(c[2],n), limbs(c[3],n)]
                yield 1, int(negative), 0, 0, False, values
    for n, top in key_shapes:
        a = [rng.getrandbits(64) for _ in range(n)]
        b = [rng.getrandbits(64) for _ in range(n)]
        for left, right in ((a,b), ([MAX]*n,[MAX]*n), ([0]*n,[MAX]*n)):
            for op in (2,3):
                value = integer(left)*integer(left if op == 3 else right)
                expected = value % (1 << (64*(n-1)+top))
                for extra in (0,3):
                    yield op, 0, top, extra, False, [left, right, limbs(expected,n)]
        value = integer(a)**2 % (1 << (64*(n-1)+top))
        yield 2, 0, top, n % 4, True, [a, b, limbs(value,n)]
    for n in FULL_SIZES:
        pairs = [([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(64) for _ in range(n)]),
                 ([MAX]*n,[MAX]*n), ([0]*n,[MAX]*n)]
        if n in (25,193,511,512,513):
            k = (n+2)//3
            signs = ([MAX]*k+[0]*(n-k), [0]*k+[MAX]*k+[0]*(n-2*k))
            pairs += list(itertools.product(signs,repeat=2))
        for a,b in pairs:
            for op in (4,5,6):
                value = integer(a)*integer(a if op == 5 else b)
                for extra in (0,3):
                    yield op, 24, 64, extra, False, [a,b,limbs(value,2*n)]
    for n in (1,25,511,512,513):
        a = [rng.getrandbits(64) for _ in range(n)]
        b = [rng.getrandbits(64) for _ in range(n)]
        for top, op in itertools.product(range(1,65),(2,3)):
            value = integer(a)*integer(a if op == 3 else b) % (1 << (64*(n-1)+top))
            yield op, 0, top, 0, False, [a,b,limbs(value,n)]


def generate(output, key_shapes):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = list(cases(key_shapes))
    counts = {}
    with (output/"cases.bin").open("wb") as raw, (output/"cases.jsonl").open("w") as manifest:
        raw.write(b"VGMPFSH1"+struct.pack("<Q",len(rows)))
        for i,(op,param,top,extra,shared,vectors) in enumerate(rows):
            counts[op] = counts.get(op,0)+1
            raw.write(struct.pack("<7Q",i,op,param,top,extra,shared,len(vectors)))
            digests = []
            for vector in vectors:
                data = struct.pack("<"+str(len(vector))+"Q",*vector)
                raw.write(struct.pack("<Q",len(vector))+data)
                digests.append(hashlib.sha256(data).hexdigest())
            manifest.write(json.dumps(dict(id=i,op=op,param=param,top=top,extra=extra,shared=shared,
                lengths=list(map(len,vectors)),vector_sha256=digests),sort_keys=True)+"\n")
    return dict(cases=len(rows),seed=SEED,operations=counts,
                definition="Python arbitrary integers from inputs; no executable-output-derived expectations",
                sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())})


def static_witnesses(key_shapes):
    """Small Python model sanity check and counterexamples; no native/proof claim."""
    killed = {name:False for name in ("wrong-shift","lost-shift-carry","lost-borrow")}
    checked = 0
    for op,shift,_,_,_,vectors in cases(key_shapes):
        if op != 0 or len(vectors[0]) > 129:
            continue
        a,b,expected = vectors
        for mutant in (None,*killed):
            out = []
            carry = borrow = 0
            actual_shift = 1 if mutant == "wrong-shift" and shift == 4 else shift
            for i,x in enumerate(a):
                word = b[i] if i < len(b) else 0
                total = (word << actual_shift) | carry
                shifted = total & MAX
                carry = 0 if mutant == "lost-shift-carry" else total >> 64
                difference = x-shifted-borrow
                out.append(difference & MAX)
                borrow = 0 if mutant == "lost-borrow" else int(difference < 0)
            if mutant is None:
                assert out == expected
            elif out != expected:
                killed[mutant] = True
        checked += 1
    assert all(killed.values())
    return dict(status="pass",small_helper_model_cases=checked,model_mutant_counterexamples=killed,
                native_code_executed=False,verus_executed=False)

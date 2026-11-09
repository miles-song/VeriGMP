"""Independent Python-integer oracle. No performance samples or Verus runs."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess

MASK = (1 << 64) - 1


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(words):
    return sum(word << (64 * i) for i, word in enumerate(words))


def encode(words):
    return ",".join(f"{word:016x}" for word in words)


def cases():
    alphabet = (0, 1, MASK, MASK - 1, 1 << 63)
    for n in (1, 2):
        for values in itertools.product(alphabet, repeat=2 * n):
            a, b = list(values[:n]), list(values[n:])
            yield a, b, n
            yield a, b, 2 * n
    rng = random.Random(0xC011A20261109)
    sizes = (1, 2, 7, 8, 9, 13, 14, 15, 16, 19, 20, 21, 23, 24, 25,
             31, 32, 33, 35, 45, 46, 47, 63, 64, 65, 95, 96, 97, 114, 115, 116, 127, 128)
    for n in sizes:
        patterns = [([0] * n, [MASK] * n), ([MASK] * n, [MASK] * n),
                    ([1] * n, [MASK - 1] * n),
                    ([MASK if i % 2 else 0 for i in range(n)], [0 if i % 2 else MASK for i in range(n)]),
                    ([0] * (n - 1) + [1], [1] + [0] * (n - 1))]
        for _ in range(12):
            a = [rng.getrandbits(64) for _ in range(n)]
            b = [rng.getrandbits(64) for _ in range(n)]
            patterns.extend(((a, b), (a, a)))
        for a, b in patterns:
            for q in sorted({1, n, 2 * n - 1, 2 * n}):
                yield a, b, q
    for r, s in ((1, 128), (128, 1), (7, 13), (13, 7), (24, 25), (31, 128), (128, 127)):
        for _ in range(20):
            a = [rng.getrandbits(64) for _ in range(r)]
            b = [rng.getrandbits(64) for _ in range(s)]
            for q in sorted({1, min(r, s), max(r, s), r + s - 1, r + s}):
                yield a, b, q


def run(binary, output):
    output.mkdir(parents=True, exist_ok=False)
    requests, expected = [], {}
    for a, b, q in cases():
        operations = ["column"]
        if len(a) == len(b) and q in (len(a), 2 * len(a)):
            operations += ["column_low", "row_low"] if q == len(a) else ["column_full", "row_full"]
        for op in operations:
            case_id = str(len(requests))
            requests.append(f"{case_id} {op} {q} {encode(a)} {encode(b)}\n")
            value = number(a) * number(b) % (1 << (64 * q))
            expected[case_id] = encode([(value >> (64 * i)) & MASK for i in range(q)])
    input_bytes = "".join(requests).encode()
    (output / "inputs.txt").write_bytes(input_bytes)
    result = subprocess.run([str(binary)], input=input_bytes, capture_output=True, timeout=60)
    (output / "stdout.txt").write_bytes(result.stdout)
    (output / "stderr.txt").write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(f"oracle driver exit {result.returncode}: retained stderr")
    seen = set()
    for line in result.stdout.decode().splitlines():
        case_id, actual = line.split()
        if case_id in seen or expected.get(case_id) != actual:
            raise AssertionError(f"oracle mismatch or duplicate at {case_id}")
        seen.add(case_id)
    assert seen == set(expected)
    invalid = []
    for request in ("x column 1 0 0\n", "x column 3 1 1\n",
                    "x column 1 " + encode([1] * 129) + " 1\n",
                    "x column_full 3 1 1\n", "x column_low 1 1,1 1,1\n"):
        # Empty-domain rejection uses the parser for q=0, not a disguised valid zero.
        if request == "x column 1 0 0\n":
            request = "x column 0 0 0\n"
        probe = subprocess.run([str(binary)], input=request.encode(), capture_output=True, timeout=5)
        assert probe.returncode != 0
        index = len(invalid)
        (output / f"invalid-{index}.stderr").write_bytes(probe.stderr)
        invalid.append(dict(input=request, returncode=probe.returncode))
    report = dict(status="pass_unverified_integer_oracle", cases=len(expected), invalid=invalid,
                  binary_sha256=digest(binary),
                  artifacts={name: digest(output / name) for name in ("inputs.txt", "stdout.txt", "stderr.txt")},
                  source_sha256={name: digest(Path(__file__).parent / name)
                                 for name in ("column.rs", "runner.rs", "oracle.py")},
                  guard_and_input_frames="Driver checks both sentinel words and both immutable input copies after each case.",
                  proof_claim=False, performance_samples=0)
    (output / "oracle.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status=report["status"], cases=len(expected), invalid=len(invalid))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.binary.resolve(), args.output.resolve())

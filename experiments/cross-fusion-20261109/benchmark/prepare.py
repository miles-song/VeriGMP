#!/usr/bin/env python3
"""Create the immutable benchmark inputs and matrix without executing timing."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

FULL_SIZES = (1, 2, 7, 8, 9, 23, 24, 25, 31, 32, 33, 47, 48, 49, 63, 64, 65,
              127, 128, 129, 191, 192, 193, 255, 256, 257, 511, 512, 513,
              1023, 1024, 1025, 2048, 4096)
KEY_SHAPES = ((1, 1), (1, 64), (2, 1), *[(n, 63) for n in
              (23, 24, 25, 63, 64, 65, 127, 128, 129, 191, 192, 193, 255,
               256, 257, 511, 512, 513, 1023, 1024, 1025, 2048, 4096)])
CORNER_SIZES = (24, 25, 64, 65, 191, 192, 193, 511, 512, 513, 1024, 2048, 4096)
PATTERN_SIZES = (25, 49, 129, 193, 257, 512, 513, 2048, 4096)
FULL_OPS = ("mul_full24", "square_full24", "mul_full192", "square_full192")
DEFAULT_OPS = ("mul_mod", "square_mod")
SEED = "cross-fusion-20261109-v1"


def make_input(n, pattern):
    data = hashlib.shake_256(f"{SEED}:{n}:{pattern}".encode()).digest(16 * n)
    a = list(struct.unpack(f"<{n}Q", data[:8 * n]))
    b = list(struct.unpack(f"<{n}Q", data[8 * n:]))
    if pattern == "same":
        b = a.copy()
    elif pattern in ("aligned", "opposed"):
        k = (n + 1) // 2
        a = [2**64 - 1] * k + [0] * (n - k)
        b = a.copy() if pattern == "aligned" else [0] * k + [2**64 - 1] * (n - k)
    elif pattern == "zero":
        a = [0] * n
    elif pattern == "max":
        a = b = [2**64 - 1] * n
    elif pattern != "random":
        raise ValueError(pattern)
    return struct.pack(f"<{2*n}Q", *(a + b))


def matrix():
    cells = set()
    for op in FULL_OPS:
        cells.update((op, n, 64, "random") for n in FULL_SIZES)
    for op in DEFAULT_OPS:
        cells.update((op, n, top, "random") for n, top in KEY_SHAPES)
        cells.update((op, n, top, "random") for n in CORNER_SIZES for top in (1, 64))
    for n in PATTERN_SIZES:
        for pattern in ("same", "aligned", "opposed", "zero", "max"):
            cells.update((op, n, 64, pattern) for op in FULL_OPS[:2])
            cells.update((op, n, 63, pattern) for op in DEFAULT_OPS)
    return sorted(cells)


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    (out / "inputs").mkdir()
    files = {}
    cells = []
    for op, n, top, pattern in matrix():
        name = f"inputs/{n}-{pattern}.bin"
        if name not in files:
            data = make_input(n, pattern)
            (out / name).write_bytes(data)
            files[name] = hashlib.sha256(data).hexdigest()
        cells.append(dict(op=op, n=n, top=top, pattern=pattern,
                          alias=pattern == "same" and op.startswith("mul_"),
                          input=name, input_sha256=files[name]))
    manifest = dict(version=1, seed=SEED, candidate_commit="d6a17984c758dab825339d0eab8562f21c5fa24b",
                    baseline_commit="2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba",
                    cells=cells, input_files=files)
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return len(cells), len(files), hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    cells, inputs, digest = prepare(args.out)
    print(json.dumps(dict(cells=cells, inputs=inputs, manifest_sha256=digest)))

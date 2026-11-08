# Packed consumer composition measurement

This benchmark measures the real borrowed-slice layout API composed with an
exact integer product. It does not change arithmetic dispatch or claim GMP
parity.

For `n` input coefficients in `[0, 2^p)`, both packed operands use slots of
`w = ceil((2p + ceil(log2(n))) / 64)` limbs, with the empty case using the
coefficient width. The exact product has `2n` slots. Each convolution
coefficient is strictly below `2^(2p + ceil(log2(n)))`; extraction therefore
uses that output precision `q`, which can differ from the input precision `p`.
The final allocated coefficient is the defined zero tail. The Rust consumer
calls `pack_coefficients`, the production `toom_multiply::full` entry, and
`extract_coefficients` from one preallocated workspace. The independently
implemented Python oracle checks every extracted word against
arbitrary-precision coefficient sums.

Three paths use the same input sets, exact result, compact output size and
caller-owned allocation boundary:

| Path | Work included |
|---|---|
| `layout` | The checked `pack_coefficients` API for both operands, current production `toom_multiply::full` exact product, and `extract_coefficients` at precision `q` |
| `bulk_zero` | `checked_layout`, whole-buffer zero fill, coefficient copies, the same production exact product and the same extraction API |
| `direct` | Exact `u128` schoolbook coefficient convolution, writing each full coefficient into the same compact `q`-bit output format |

The packed paths use the exact full-product routine from the registered
mainline baseline `8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa`. The measurement
driver verifies that every arithmetic source file in the Toom-3/Karatsuba call
graph is byte-identical between that commit and the candidate. This is an
accurate mainline implementation baseline; the direct polynomial convolution
is a separate algorithmic control, not a claim about the prior library's
default modular-product latency.

All input, packed, product, scratch, accumulator, output and eviction buffers
are allocated before timing. Reuse batches repeat one fixed input pair and
retain its warm cache state. Streaming batches rotate over 32 pre-generated
pairs and touch one word per cache line in a preallocated 64 MiB buffer before
each timed batch; cache preparation is excluded from the timing. This is an
eviction-cycled streaming condition, not a claim that each operation begins
from DRAM. Modes are interleaved in a rotated order, with seven raw repetitions
per group and each measured batch at least 10 ms. A short attempt is retained
in `discarded.csv`; the runner doubles that mode's batch length and retries the
repetition.

The workload matrix includes empty and one-coefficient inputs, non-64-aligned
precisions, the exact one-word guard case `(n=64,p=29)`, its over-boundary
neighbor `(n=64,p=30)`, odd input sizes, a 257-coefficient case, and 1,024
coefficients at four precisions. Every coefficient sum is below `2^128`, so
the direct baseline uses exact `u128` arithmetic without overflow.

Run from a clean committed worktree with the repository's pinned Verus/Rust
runtime installed under `deps-root`. Use a new output directory for each gate
and run:

```sh
python3 experiments/packed-convolution/layout_verify.py \
  --deps-root /path/to/pinned/deps --output /tmp/packed-layout-gate
python3 experiments/packed-convolution/measure_consumer.py \
  --deps-root /path/to/pinned/deps \
  --layout-gate /tmp/packed-layout-gate \
  --output /tmp/packed-consumer-run-1 --run-id independent-1 --cpu 0
python3 experiments/packed-convolution/measure_consumer.py \
  --deps-root /path/to/pinned/deps \
  --layout-gate /tmp/packed-layout-gate \
  --output /tmp/packed-consumer-run-2 --run-id independent-2 --cpu 0
```

The layout gate's Verus-compiled `libverigmp.rlib` is the library linked by the
release harness. The exact product uses threshold 24 and the production 12n
scratch contract. The measurement driver requires the gate report, library hash
and source commit to match. Each output directory retains raw runner output,
seven-sample timings, per-workload medians/95th-percentile samples, result and
input hashes, an independent oracle receipt, and tool/CPU identities.

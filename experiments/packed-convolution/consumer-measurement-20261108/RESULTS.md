# Consumer composition results

This is a local runtime measurement for the packed-layout candidate. It is not
a production dispatch change, a general crossover policy, an end-to-end solver
result, a composed formal proof, or evidence of GMP parity.

## Source and verification

The harness, measurement driver, and workload report were measured from source
commit `d82d63147cfd45939a6a34765872295dca83a3fa`, descended from candidate
feature commit `a94e71a1945352b35e9df882612381d50dbf1fbf` and review tip
`0a98c832f9a16c9428a2565ccdf94abafc7c69d3`. The registered mainline baseline is
`8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa`; all 13 source blobs in the exact
Toom-3/Karatsuba product call graph match between mainline and the measured
candidate.

The exact operation is `pack_coefficients` for both inputs, the mainline
`toom_multiply::full` product at threshold 24 with its 12n scratch contract,
and `extract_coefficients`. Input coefficient precision is p. The selected
slot width satisfies `64*w >= 2*p + ceil(log2(n))`; output extraction uses
`q = 2*p + ceil(log2(n))` so every coefficient is returned exactly, without
insufficient-precision truncation. Empty input uses the coefficient width and
returns an empty output. The full allocated result includes the required final
zero coefficient.

The same-source layout refinement gate passed 350 Verus items. Its independent
runtime oracle passed 208 valid and 18 error-preservation cases, Rust rejected
the overlapping-borrow fixture with E0502, and three semantic mutants were
rejected by complete logical VCs. The measured full-product/layout composition
itself is checked by runtime cross-path agreement and the independent Python
arbitrary-integer oracle for every coefficient; it is not claimed as a new
formal composition theorem. The accepted optimized-codegen inspection applies
to the identical `packed_layout.rs` SHA-256 recorded in the gate report.

## Protocol

Two separately built and executed release runs used the pinned Verus
`0.2026.10.26.d17fbd0` and Rust `1.99.1` toolchain on WSL2, AMD Ryzen 7 7745HX,
CPU 0. Each run contains 14 workloads, reuse and eviction-cycled streaming
conditions, three paths, and seven raw repetitions per group: 588 samples.
All batches lasted at least 10 ms, no short-sample retries were needed, the two
release binaries have identical SHA-256, and both runs used identical inputs
and outputs. Streaming rotates 32 pre-generated input pairs and touches a
preallocated 64 MiB eviction buffer before each timed batch; that preparation
is excluded from the measured interval. It is not a claim of DRAM-cold access.

All inputs, packed operands, full-product output, Toom scratch, direct
accumulator, result buffers, and cache-eviction storage are allocated before
timing. The two packed paths call the same exact product and extraction. The
`bulk_zero` control performs whole-buffer zero fill then coefficient copies.
This repository has no earlier ordinary coefficient-convolution runtime
implementation; `direct` is a benchmark-only exact u128 schoolbook polynomial
convolution control, not a historical production baseline. The independent
Python oracle uses arbitrary-precision integer sums.

The complete per-workload, per-run medians, 95th-percentile samples, ratios,
raw rows, input/result hashes, and tool/source identities are preserved in
`evidence/confirmation.csv`, `evidence/consumer-run-one.zip`,
`evidence/consumer-run-two.zip`, and `evidence/receipt.json`.

## Observations

Ratios below are the combined median for the packed API path divided by the
named control. Values above 1 are slower. The empty-input group is dominated
by call and timer overhead and is excluded from the following non-empty range.

- Against `bulk_zero`, packed ratios span 0.712 to 1.042. Three non-empty
  workload/phase groups regress: `(64,30)` reuse at 1.011, `(257,17)` reuse at
  1.042, and `(1024,17)` reuse at 1.019.
- Against direct schoolbook, the largest measured gains occur at `(1024,7)`
  and `(1024,17)`, with ratios from 0.300 to 0.319. The 257-coefficient,
  17-bit case ranges from 0.634 to 0.683.
- Near the exact guard-word boundary `(64,29)`, ratios against direct schoolbook
  are 0.996 for reuse and 0.966 for streaming, effectively close to parity at
  this sample size. Raising precision to 30 bits requires two slot words: the
  64-coefficient case is about 3 times slower than direct schoolbook; the
  65-coefficient case is about 2.7 to 2.9 times slower.
- At `(1024,29)` packed ratios against direct schoolbook are 0.952 to 0.958;
  at `(1024,53)` they are 0.968 to 1.002.

These observations identify workload regions for further measurement. They do
not define or implement a crossover threshold. No production dispatch is
promoted by this result, particularly because short guarded cases materially
regress and the direct control is not an existing library runtime baseline.

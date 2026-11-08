# Independent Review: Packed Consumer Measurement

**Decision: ACCEPT for the declared local measurement-evidence scope only.**
This does not establish a new product-composition proof, a general crossover,
solver speedup, production dispatch change, or GMP parity.

The package is at `84887ab1a94b258cc3f5f25fdd7a6044f7a910b2`; the measured
source is `d82d63147cfd45939a6a34765872295dca83a3fa`, an ancestor whose later
package changes add the measurement artifacts. The receipt binds the measured source,
driver and harness hashes, packed-layout source hash, Verus library and metadata
hashes, pinned toolchain, and both run manifests. All 59 layout-gate source
hashes match the measured commit. Both run ZIPs contain binaries matching the
recorded release-binary SHA-256; their archived files match their metadata
hashes. All receipt-listed archive and evidence-file hashes match. The 13
registered Toom/Karatsuba product call-graph blobs match the mainline baseline.
The packed-layout module is added and exposed, while `verified/arithmetic.rs`
and `verified/fast_multiply.rs` are unchanged; no arithmetic dispatch change is
enabled by this measurement.

I independently replayed the layout gate from package HEAD; it passed 350
Verus items, 208 valid runtime cases, 18 error-preservation cases, the E0502
overlap fixture, and all three semantic mutants. The packed-layout source hash
is identical to the measured-source gate. The two recorded WSL2 runs have 588
samples each (14 shapes x 2 phases x 3 modes x 7 repetitions), distinct process
IDs, identical release-binary hashes and inputs/outputs, no short retries, and
minimum batches above 10 ms. Recomputed ratios and ranges match `confirmation.csv`
and `RESULTS.md`; the empty shape is excluded from nonempty ranges. The reported
bulk-zero regressions and `(64,29)`, `(64,30)`, `(65,30)` guard-width results
match the data.

For each workload, the Python arbitrary-precision oracle checks every output
coefficient for the first input pair and all three modes. During setup, all 32
input pairs per workload are checked for equality across layout, bulk-zero, and
direct paths; each timed batch also checks its final result against the
precomputed direct result for that pair. The direct control is exact u128 under
the registered bounds: at maximum `n=1024, p=53`, each coefficient is less than
`1024*(2^53-1)^2 < 2^116`, leaving 12 bits below u128. This supports the
declared workload comparison, while the Python oracle is not run separately on
all 32 pairs. Each maximum-size packed operand has 2048 u64 limbs, the full
product has 4096 output limbs, and scratch is 12 times the packed operand limb
length. The exact extraction precision is `q=2p+ceil(log2(n))`; the `2n`
coefficient output includes its final zero tail. Empty input returns empty.

One nonblocking documentation defect remains: `RESULTS.md:58` names
`evidence/consumer-evidence.zip`, which is absent. The two run archives,
layout-gate archive, confirmation table, and receipt are present separately.
Update that reference or provide the aggregate archive before relying on that
link. Seven observations per group make the reported 95th percentile the
maximum sample; these are descriptive microbenchmark results, not significance
tests. I reviewed the two recorded timing runs and recomputed their summaries;
I did not rerun the full timing protocol.

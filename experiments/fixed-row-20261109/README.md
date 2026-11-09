This directory contains unverified test infrastructure for the actual native
fixed-row implementation at commit `d12759a022d2e285d0bc6b5869ccfb5c1d85f665`,
native tree `5790ad2fbadc9877332124c6a66ae3b70b016d03`. Production full-product
leaves of 15, 20, 22 and 23 limbs use the const-size row implementation. The
native dispatch, caller-owned storage, public contracts and compiled library
are exercised directly.

For radix B=2^64 and little-endian slice s, define V(s)=sum(s[i]*B^i).
The independent full-product obligation is V(dst)=V(a)*V(b), with N input
words and 2*N output words. The first row overwrites dirty output and satisfies
V(row)+B^N*carry=word*V(b). Each later row adds its shifted word product.
Python unbounded integers supply the external arithmetic oracle. GMP's public
mpn_mul_n/mpn_sqr interface supplies a separate observational comparator outside
the verified library. `ordinary.rs` is an unverified same-algorithm control.

The final candidate pair is the coordinator's strict full-library export at
`E:\3sat\VeriGMP-root-fixed-row-native-20261109\full-r05-toolbound`, with
371 verified obligations and zero errors. Its rlib SHA-256 is
`2d533b2038d572b6ab7d79295dec53143f7b7a5cde654ca5763f3695c6aec7c8`;
its vir SHA-256 is
`a53e2cfa19826103656eafcb0ff97bf0d4928e6fd3ffcc90f5eba5511d708d18`.
The receipt binds all native files, Verus files, actual Rust 1.99.1 compiler,
sysroot, executable resolution and optimized export. The baseline is the
source-bound full358 export at
`E:\3sat\VeriGMP-cross-fusion-baseline-fresh-20261109`, native tree
`72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`.

`gates.py` accepts an output directory and runs one explicitly selected untimed
stage. It pins CPU 8, one Verus worker, rlimit 10, --no-cheating, a maximum
60-second child timeout and 480 seconds of aggregate child wall time across
sibling run directories. Exact commands, environment, raw stdout/stderr and
hashes are retained after every child. The script checks source, pair and tool
identity before and after each stage. It does not run `scripts/verify.py` or
launch timing samples.

For a fresh full reproduction in WSL, use an unused external output directory:

```text
python3 experiments/fixed-row-20261109/gates.py prepare --output /mnt/e/3sat/VeriGMP-fixed-row-local-gates-20261109/run-fresh
python3 experiments/fixed-row-20261109/gates.py runtime --output /mnt/e/3sat/VeriGMP-fixed-row-local-gates-20261109/run-fresh
python3 experiments/fixed-row-20261109/gates.py consumer --output /mnt/e/3sat/VeriGMP-fixed-row-local-gates-20261109/run-fresh
python3 experiments/fixed-row-20261109/gates.py mutations --output /mnt/e/3sat/VeriGMP-fixed-row-local-gates-20261109/run-fresh
python3 experiments/fixed-row-20261109/gates.py codegen --output /mnt/e/3sat/VeriGMP-fixed-row-local-gates-20261109/run-fresh
python3 experiments/fixed-row-20261109/gates.py inspect --output /mnt/e/3sat/VeriGMP-fixed-row-local-gates-20261109/run-fresh
```

`runtime` checks 51 lengths, five operand patterns and top precision 1, 32, 63
and 64. It covers direct selected leaves, the original basecase, the ordinary
control, forced full recursion at thresholds 8/24, full Toom dispatch and default
modular multiplication/squaring. Buffers start dirty. Inputs remain unchanged;
outer destination/scratch canaries and a seven-word unborrowed scratch suffix
remain unchanged. Calls receive exactly the documented scratch domain: 3*N for
forced full, 12*N for full/default multiply, and 10*N for default square.

The invalid-call checks observe native assertions for bad lengths, top precision,
threshold and insufficient scratch. They do not prove behavior outside a public
contract. For example, default multiplication requires 12*N scratch words even
though its small-input implementation checks 4*N; the small negative case tests
below 4*N. Workspace queries cover zero, valid capacity and integer-overflow
boundaries without allocating those capacities. Ordinary Rust borrow negatives
must fail specifically with E0502/E0499 for input/output and output/scratch
overlap.

`consumer.rs` imports the actual rlib and vir pair, verifies four callers and
executes them through the real public ABI. It uses no erased-Ghost placeholder,
assumption, admitted obligation or external body. `mutations` copies the full
actual native snapshot, changes one semantic operation and verifies the fixed_row
module. Its four mutations remove the accumulator, start with a wrong carry,
discard the first carry and discard a later carry. A typed failed verification
condition is required. Timeouts, resource limits, type errors and tool failures
are retained and are not accepted as mutation detection.

`codegen.rs` compares all four actual const-row instantiations with ordinary
same-algorithm controls. The inspector compares the successful-path instructions,
checks multiplication counts and cold calls, follows native direct/GOT call
edges in the actual linked binary, and decodes the actual full-dispatch jump
table. Its scope and raw artifact hashes are recorded in `codegen-review.json`.

External evidence for this execution is under
`E:\3sat\VeriGMP-fixed-row-local-gates-20261109`. `run-01` retains the original
r04 pair's 4,885 baseline and 4,905 candidate Python-validated cases, 18 native
assertion negatives, workspace boundaries, imported consumer, borrow negatives
and four typed failed semantic VCs. It also retains an additional dispatch-skip
mutation that produced a failed postcondition together with a resource-limit
error; that attempt is not counted as accepted detection. `run-02` uses the
final r05 pair, replays the frozen integer-validated fixtures against both newly
built actual binaries, and records the final imported consumer and codegen
artifacts. Native source bytes are identical between those runs. The original
pair identities and unsuccessful attempt remain explicit in their receipts.
All four codegen pairs have identical successful-path instruction sequences
after local-label renaming, with 282, 380, 416 and 432 instructions. The actual
native full-dispatch jump table selects exactly 15/20/22/23. Those native leaf
regions contain 30/40/44/46 static multiply instructions and no calls or division.
The inspector also records the actual 16-function native call closure. Its first
attempt stopped at a final-block fallthrough boundary; the raw failure and
original inspector are retained alongside the successful inspection. Total
bounded correctness-child wall time is 118.625 seconds, including failed
attempts. These counts concern checked code generation and test infrastructure,
not an analytic resource theorem.

The coordinator owns all performance sampling. `prepare` emits 8 principal
cells (1024/4096, random/max, multiply/square, top 63), 18 selected/adjacent leaf
cells and 36 default-dispatch boundary cells. Both native binaries compile the
same runner source with the same optimized Rust flags. Candidate cfg only
enables the direct const-row correctness API. The sample command is:

```text
taskset -c CPU runner-{old,new} sample INPUT {mul,square,forced} COUNT
```

Inputs, output size and preallocated 12*N scratch match. Allocations, GMP exact
checks, dirty frames, canaries and deterministic input/output checksums occur
outside the timer. Warmup is min(COUNT,32). Output is
`sample OP COUNT NS INPUT_A_CHECKSUM INPUT_B_CHECKSUM OUTPUT_CHECKSUM`.
Principal counts are 512 at 1024 limbs and 64 at 4096; leaf count is 262144,
inherited from the prior actual-control/prototype measurements. Boundary counts,
interleaving, independent runs and observation windows must be frozen by the
coordinator before final sampling. The declared gate is principal geometric mean
candidate/actual-old <=0.97 and every principal/regression cell <=1.03; all cells
must be reported. These local gates and an individual accepted optimization do
not establish GMP parity or consuming-solver backend acceptance.

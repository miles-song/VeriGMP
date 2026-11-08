# Packed-layout crossover results

## Decision

No robust policy is established by this experiment. None of the 34 prospective
hybrid predicates passes the discovery gate, so the selection was frozen as
selected_rule=null before confirmation timing began. The held-out data do not
retune that decision. Neither universal layout packing nor universal bulk
zero/copy packing passes the registered no-regression rule across all shapes.

Across all 1,440 independent run/shape/cache-phase groups, the geometric mean
of layout/bulk median-time ratios is 0.943469, with a range of 0.677766 to
1.187859. Values below one favor layout. Layout regresses in 234 groups:
138 exceed 1% and 29 exceed 5%. The preferred path changes between the two
independent repeats in 168 of 720 shape/cache-phase groups. These results
support aggregate gains and local variation; they do not support enabling a
new dispatch policy.

## Fixed source and consumer

The reviewed experiment base is
fe9081f1a1d4075f74a46cdd66d97145d065c5ad. Preregistration, harness,
measurement driver, and measured sources were committed before timing at
83c4c52f52b40c8adac2cbda6ed4f0768d0f99a0, tree
13fec2c76d8c354a6b861b150cfdbf0b7d8a2367.

Both paths compose two operand packs, the exact production
verigmp::toom_multiply::full at threshold 24 with its 12n scratch contract,
and packed_layout::extract_coefficients at
q=2p+ceil(log2(n)). Each coefficient is returned exactly, including the
allocated final zero coefficient. Every one of the 13 source blobs in the
Toom/Karatsuba full-product call graph matches mainline baseline
8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa.

The layout path calls pack_coefficients. The bulk control calls checked_layout,
fills the entire packed destination with zero, and copies each compact
coefficient into its slot. Both use the same input ring and equal-sized,
caller-owned workspaces. They call the same product and extraction routines
from the same source-bound library.

| Identity | SHA-256 |
|---|---|
| Preregistered protocol | 1a09aee1fbc18c2d0719693becb35a3de0f2b59194c3bad69d5b0d8ce86d38e2 |
| Rust harness | 7473bf25db3c3b211c77c7ef115a4af14cd9fa2204864d02f369cdeb2cc9a537 |
| Measurement driver | b3c0552066590afe5d1d31e75c17154c960c2a6538e07255c14a168b670ab2bd |
| packed_layout.rs | fb8073712aa5681ef6f4f9dbb3aff85884955539d809e2e0131bc1b84d2626c8 |
| toom_multiply.rs | 58830125c0e82680f11fec6aba9677c8986c8f84fdbe53e3a38dc01b24871602 |
| Release executable, all four processes | a8294ba699aba9b08530534eecca7e993aa84672b8f78816c9cfb2c680f9b9d1 |
| Frozen selection receipt | 5f0a009fbd541cf430586c81506e54f86216f0d4cbd7c4d7ea891ec9467aa9a7 |

The final analysis script has its own SHA-256 in analysis.json. The source map
in each measurement receipt identifies the preregistered measurement snapshot.
All source bytes, mainline blob identities, compiled-library identities, and
tool hashes are retained with the evidence.

## Protocol and environment

The matrix has 360 shapes: 72 registered counts crossed with p=7,17,29,30,53.
Discovery uses n=1..35,125..131,509..515 (245 shapes). Held-out confirmation
uses n=60..69,253..259,1019..1024 (115 shapes). The dense small counts include
the 16/17 slot transition at p=30 and the 24/25 one-slot Toom threshold.
Confirmation includes the 64/65 slot transition at p=29. The matrix was fixed
before timing and does not fit a threshold to the earlier 14-shape study.

Each shape has reuse and eviction-cycled streaming phases, two paths, and
seven raw repetitions per path/phase. Reuse repeats one warmed pair.
Streaming rotates 32 pre-generated input pairs and touches one word per cache
line of a preallocated 64 MiB eviction buffer before each batch. Eviction is
excluded from timing. This does not make every operation DRAM-cold.

Inputs, packed operands, products, scratch, outputs, retained result words, and
eviction storage are allocated before the measured loops. Input generation,
cache preparation, output dumping, exact oracle checks, file hashing, and
compilation are outside timing. Modes use rotated interleaving. Calibration
targets 25 ms; accepted batches must last at least 10 ms.

| Process | Shapes | Raw accepted samples | Minimum accepted batch | Retained short attempts |
|---|---:|---:|---:|---:|
| discovery-a | 245 | 6,860 | 12.107023 ms | 1 |
| discovery-b | 245 | 6,860 | 13.222321 ms | 1 |
| confirmation-a | 115 | 3,220 | 18.729766 ms | 0 |
| confirmation-b | 115 | 3,220 | 17.200359 ms | 0 |
| Total | 360 shapes, twice | 20,160 | all at least 10 ms | 2 |

Each short attempt is retained in its discarded.csv and retried at double
iteration count. It does not enter the reported medians. One initial timing
attempt was explicitly aborted before environment coordination was complete;
its full remaining artifacts are preserved separately and excluded from every
analysis.

All accepted timing used WSL2 x86_64 on AMD Ryzen 7 7745HX, pinned to CPU 0.
The coordinator reserved its sibling CPU 1 and observed the Android emulator
stopped before the controlled runs. A post-timing start command at
2026-11-08 03:26:42 UTC returned "virtual device already running"; the immediate
status query reported it running. Continuous suspension was not monitored,
so these measurements are not labeled guaranteed emulator-free. The recorded Windows power scheme is CS2 Gaming
(Plugged In). The pinned toolchain is Verus 0.2026.10.26.d17fbd0 and Rust
1.99.1, LLVM 23.1.1. Python 3.12.3 performs the independent integer oracle.
The environment receipt includes executable hashes, sibling topology, kernel,
and power-scheme observation; measurement metadata separately hash Rust,
Verus, rust_verify, Z3, vstd, and builtin artifacts.

## Exact checks and identity confirmation

The same-commit layout gate passed 350 Verus items, 208 runtime oracle cases,
18 error-preservation cases, the expected E0502 overlapping-borrow rejection,
and three semantic mutants rejected by complete logical VCs. The measured
packed_layout.rs matches the reviewed layout source hash. The gate's
optimized compiled library is the library actually linked by all four
release harness builds. The independently built harness executables have
identical SHA-256.

For every shape and every one of the 32 input pairs, Rust asserts cross-path
word equality. The complete output dump retains both paths' words. The A
process for each split is checked coefficient by coefficient by an independent
Python arbitrary-precision convolution. Its B process must reproduce the
same input hashes and the entire result dump byte for byte, and retains the
same hash-checked oracle receipt. This is direct equality of result bytes as
well as matching hashes.

| Split | Exact result dump SHA-256, identical in both processes |
|---|---|
| Discovery | a5eb0a8e66fbec72258c629261f7f4f652b1e9d55f3adc3a9f74d363bdd4d28b |
| Confirmation | 45d7dadd762058c8d750b7a39fd326bb8b01d029ebef5b25b6cf286837622710 |

The oracle validates the exact full coefficient rather than a low-precision
residue. The largest registered q is 116 bits; all configured coefficient sums
fit that exact bound. These runtime composition checks do not constitute a new
formal proof of the packing/product/extraction composition. The gate retains
its explicit pending separate codegen-comparison field; this experiment does
not create a new codegen-erasure or performance-proof claim.

## Count, precision, slot, and guard observations

All following ratios are per-group medians from seven samples, followed by
equal-weight geometric means of the group ratios. No samples are pooled across
counts, precisions, cache phases, or independent processes before testing
regressions.

| Input precision p | Groups | Geometric mean layout/bulk | Largest ratio | Layout regression groups |
|---:|---:|---:|---:|---:|
| 7 | 288 | 0.932792 | 1.112834 | 31 |
| 17 | 288 | 0.928847 | 1.085774 | 28 |
| 29 | 288 | 0.937055 | 1.076078 | 44 |
| 30 | 288 | 0.952040 | 1.129745 | 61 |
| 53 | 288 | 0.967137 | 1.187859 | 70 |

| Registered count band | Groups | Geometric mean layout/bulk | Layout regression groups |
|---|---:|---:|---:|
| 1..16 | 320 | 0.851002 | 2 |
| 17..35 | 380 | 0.945807 | 27 |
| 60..69 | 200 | 0.973252 | 28 |
| 125..131 | 140 | 0.982800 | 36 |
| 253..259 | 140 | 0.989312 | 43 |
| 509..515 | 140 | 0.993354 | 54 |
| 1019..1024 | 120 | 0.994135 | 44 |

Small counts show larger aggregate gains, while large-count ratios lie closer
to one and change winner more often. A universal preference based only on
precision is unsupported: every precision contains regressions.

One-slot groups have geometric mean 0.915616 and 60 regressions in 800 groups;
two-slot groups have geometric mean 0.979479 and 174 regressions in 640 groups.
Reuse and streaming geometric means are 0.943501 and 0.943436, with 118 and
116 regressions respectively. Neither cache phase eliminates the variation.

Required guard bits are ceil(log2(n)); the remaining slot margin is
64*slot_words-q. Crossing a slot boundary changes both product operand length
and extraction width:

| n | p | q | Slot words | Required guard bits | Remaining slot margin | Ratio range across both processes and phases |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 30 | 64 | 1 | 4 | 0 | 0.893258..0.926232 |
| 17 | 30 | 65 | 2 | 5 | 63 | 0.928028..0.996368 |
| 64 | 29 | 64 | 1 | 6 | 0 | 0.938474..0.995090 |
| 65 | 29 | 65 | 2 | 7 | 63 | 0.969354..1.038105 |

The held-out (65,29) case favors layout in process A but bulk packing in
process B. The exact guard transition therefore does not identify a stable
single crossover. The zero-remaining-margin descriptive stratum has no
observed regressions in its 64 groups, while the neighboring 1..7-bit-margin
stratum has one. This is a descriptive stratification, not a registered,
independently selected hybrid policy. Precision, count, and margin are linked
by slot sizing, so their stratified correlations do not identify an isolated
causal factor.

## Preregistered hybrid gate

The fixed family contains 34 rules: either branch can select layout based on
one slot-width predicate, one of six count thresholds, or one of nine remaining
margin thresholds. Both branches need coverage of at least three discovery
counts and two precisions. Eligibility requires at least 1% geometric-mean
gain and no median regression in any discovery group in either repeat.

Eligible rules: zero. The best aggregate rule in this family, layout for
n<=512 and bulk otherwise, has discovery geometric mean 0.925542 but 93
regression groups and worst ratio 1.187859. It is rejected. No rule is
promoted from the held-out data, and no post-hoc equality or shape exception
is introduced.

The frozen selection receipt hash was reported to the coordinator before
confirmation execution. It identifies both discovery raw reports, the exact
protocol and source hashes, all candidate outcomes, and selected_rule=null.
The confirmation runs complete the registered shape coverage and independently
check universal-path behavior. They do not supply a replacement hybrid.

## Evidence and limits

The raw-report hashes, run metadata hashes, complete archive inventories, and
source/tool identities are in evidence/receipt.json and evidence/SHA256SUMS.
All-groups and stratified CSV files retain the full measured matrix. The
archives preserve raw accepted and short rows, stdout/stderr, executable,
inputs, every result word, and the exact oracle checks. The initial aborted
attempt is explicitly separate.

This is one machine and one pinned consumer implementation. The unmonitored
emulator state is an additional environment limitation. The matrix covers
one-limb coefficients with p<=53 and n<=1024. Streaming describes a 32-input
eviction-cycled batch condition. Seven samples and a strict no-regression
screen do not prove a statistical or worst-case performance guarantee; a
negative outcome does not prove that no useful policy can exist. Held-out
counts start at 60, so a rule restricted to very small counts cannot earn
held-out gain from this split.

The observed pack difference can be a small part of total Toom/extraction
time. There is no production dispatch change, new formal composition theorem,
GMP parity claim, solver integration claim, or merge/push in this package.
The complete experiment is ready for a new independent Astra Max measurement
review; that review has not yet occurred.

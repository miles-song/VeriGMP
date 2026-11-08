# Four-cell combination receipt

This is a new exploratory result. It does not revise the historical
checked-recursion **NO-GO** at main `515f1efa0d79bcb73272df9f54917f156decf1e1`.
No benchmark or calibration has been executed; performance is pending.

## Fixed source cells

All 57 tracked native files (50 Rust) were reconstructed from fixed Git objects
and validated byte-for-byte. Their canonical native manifest identities are:

| Cell | Native source identity |
| --- | --- |
| Baseline 00 | `7e8d3f151d3eda7c5a3df285f882618a26022d0f7b7661ff266812a4b123f446` |
| Doubled-cross 10 | `ff3843b5b822bc9b2080bd0f26d6b604cf17b1147de193848e01ac8526c00f4a` |
| Checked recursion 01 | `652224b6d79a7c2bc769b4abdb7ae955e975da87cdf55f2ed5b9fb90cefb9756` |
| Combined 11 | `495f1689b95ebd7ed3151a13d6cec505ed77f80177adcc6dadc9567f8836f06b` |

The doubled-cross source is exactly
`f46b835cb8f812293924418abc42a39978d78694`; the checked-worker source is
exactly `b31fbce898054f6db668277f8a4da88f94c95aa2`. The baseline producer proof
at 358 items and the isolated 365/359 producers are reused only with all 50
Rust hashes, exact exports and toolchain hashes verified. The combined source
was freshly checked with pinned Verus `0.2026.10.26.d17fbd0`, Rust `1.99.1`,
`--no-cheating --compile -O`: **366 verified items, zero errors**.

## Untimed gates

Each cell passes 1,898 independent Python/GMP product/default cases and 2,418
forced/default square cases through 4,096 limbs, along with boundaries,
canaries and input preservation. Two targeted mutants fail with complete logical
verification-condition rejections. Every complete native executable section
and relocation record is retained for each single-factor comparison.

In the combined release object, the affected complete functions are
`fast_multiply::full` (901 to 160 bytes plus an 837-byte private worker),
`square_low::low` (1,347 to 1,238 bytes), and its unchanged-source caller
`toom_multiply::full` (2,640 to 2,672 bytes). Three added proof-spec symbols
are unreachable placeholder sections. These code-size differences establish
no runtime gain.

The source-schedule count reaches both factors for default `square_mod` at all
11 preregistered primary sizes, starting at n=255. At n=255, one low-square
correction invokes a 54-limb Toom child, which crosses the fixed Karatsuba
threshold 24. For n=255, the source schedule counts 13 full public entries in
the baseline and 1 public entry plus 13 private-worker entries with the worker;
the square correction visit count falls from 154 to 77 limb iterations. Exact
products, thresholds, workspace, precision and mathematical results do not
change. The count is an analytic source schedule, not dynamic instruction data
or a checked asymptotic cost theorem.

The truncated-square base schedule uses `floor(m*m/4)` cross multiplications
and `ceil(m/2)` diagonal multiplications, totaling 25 at m=9 and 1,056 at m=64.
All 86 operation rows are checked against the analytic schedule. Independent
fixtures enumerate every retained scalar pair once at lengths 1 through 129,
including all 56 dedicated low-square leaf lengths in every source cell.

The existing harness is fixed to four cells plus GMP over all 86 historical
operation/shape controls, with 11 primary square shapes, seed `20261108`, seven
accepted >=10ms samples and two independently launched runs. The combination
must beat baseline on the primary geometric mean by at least 2%, and adding the
checked-worker factor to doubled-cross must improve that geometric mean by at
least 1%. Both combined comparisons must stay within 5% of their comparator in
every cell, in each run. Independent Astra prereview and a coordinated quiet
window are required before any calibration or timing. Full per-cell ratios and
raw records are retained; every failure, regression and incomplete run remains
visible.

The checked-worker factor's prior negative performance result remains in force
for its isolated claim. This factorial experiment makes a new interaction
measurement only. GMP parity, a solver/SAT benefit, a complete bit-cost proof,
peak-live-space bound, caches or dispatch policy are not established here. The
solver's current explicit traces use ring multiply/add, not a dedicated square
path, so a library square result cannot be transferred to SAT performance.

The content-addressed untimed evidence archive and its offline checker are
under [evidence](evidence/README.md). It records no timing result.

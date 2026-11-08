# Independent acceptance review

**ACCEPT for merging the negative experimental-evidence package into main.**
There are no blocking findings within its declared descriptive scope. The
experiment establishes that none of its 34 preregistered rules passed its
registered screen on the retained observations. It promotes no implementation
or dispatch policy. This acceptance does not establish production performance,
GMP parity, a universal negative theorem, or a formal product-composition or
resource theorem.

The reviewed candidate is `80447fdb090e6ea47e09ee487434bd5d7d13089e`, tree
`c2605e2d1de339661074864c9044dd01f360742a`. The measured preregistration is
`83c4c52f52b40c8adac2cbda6ed4f0768d0f99a0`, tree
`13fec2c76d8c354a6b861b150cfdbf0b7d8a2367`. The integration target is main
`8cc144b349269d31a59b18838aea28f52645a8fa`; their merge base is
`fe9081f1a1d4075f74a46cdd66d97145d065c5ad`. The feature contributes only files
under this experiment directory. All 49 native Rust files and all 13 product
source/specification blobs match that main commit. The native tree is also
unchanged between the measured source and candidate. A normal branch merge
preserves main's newer documentation and proof-status records; the older
versions at this divergent branch tip are not feature-owned changes.

The review adds this record, [the independent replay program](independent_audit.py),
and [its complete audit result](evidence/independent-review-complete.json).
Historical raw files, archives, receipts, protocol, report and analysis snapshots
remain unchanged. Their pre-review status fields describe the original package;
this additive record supplies the independent acceptance decision. Both original
branch commits have author and committer `miles-song <2324715854@qq.com>` and no
coauthor trailers.

The independently executed gates were:

1. Rehash every receipt-listed artifact and package document, every SHA256SUMS
   entry, all six archives and their 292 entries. Verify the 19 measured-source
   hashes directly against Git, all 59 gate-source snapshots, all four run
   metadata/output bindings, nine installed tool hashes, library/Verus metadata
   identities and all 13 product Git blobs against main. The two excluded short
   attempts and separate aborted attempt remain archived and are absent from
   accepted statistics.
2. Reconstruct every accepted sample directly from native stdout, check the
   exact registered matrix and unique repetitions, and recompute medians using
   rational `total_ns / iterations` values. All 20,160 retained samples satisfy
   the 10 ms floor. The four per-process sample counts are 6,860, 6,860, 3,220
   and 3,220; minimum batches are 12.107023, 13.222321, 18.729766 and
   17.200359 ms. Both short attempts were retried with at least twice the
   iterations. All 1,440 median-ratio groups, the 22 descriptive strata, top
   regressions and 720 independent-run sign pairs reproduce the stored tables.
3. Independently regenerate all 32 input pairs at each of 360 shapes and check
   every retained coefficient for both paths: 23,040 output frames and
   8,752,640 coefficient values across the A runs. The review oracle uses Python
   arbitrary-precision multiplication with uniform 128-bit digits, independent
   of the harness's variable slot width, and additionally evaluates 56,960
   direct finite sums at edge, middle and zero-tail positions. Both B result
   dumps, input receipts and oracle receipts equal their A counterparts byte
   for byte. The original A-run driver independently used direct schoolbook
   Python convolution for every coefficient, not only one input pair per shape.
4. Recompute all 34 predicates, both branch-coverage conditions, each candidate's
   geometric mean and every per-group regression. None is eligible; the frozen
   selection is null. Repeating eligibility with unrounded rational median
   ratios gives the same decisions. Confirm the final analysis consumes the
   frozen rule and does not fit a replacement from held-out rows.
5. Reuse the unchanged source-bound layout proof gate after verifying source,
   library and log identities. Its retained successful run has 350 verified
   items, 208 runtime oracle cases, 18 error-preservation cases and E0502 alias
   rejection. Independently reclassify all three mutant logs as complete logical
   VC failures, using the source-bound strict classifier and its self-check.
   No fresh proof batch is claimed or needed for this experiment-only diff.
6. Independently rebuild the release harness with the recorded Rust toolchain
   and verified library, without executing a timing run. Its SHA-256 is exactly
   `a8294ba699aba9b08530534eecca7e993aa84672b8f78816c9cfb2c680f9b9d1`,
   matching all four independently retained executables. Build stdout/stderr
   are empty. No benchmark timings were rerun by this review.

Manual source review confirms the same operation and boundaries in both modes
(`crossover_bench.rs:103`, `:117`, `:134`, `:162`): pack both operands, call
`toom_multiply::full` with threshold 24 and caller-owned scratch, then extract
all `2*n` coefficients at `q = 2*p + ceil(log2(n))`. Canonical inputs make the
bulk zero/copy control semantically equivalent in this measured domain. Source,
packed, product, scratch, output, saved-result and eviction buffers are allocated
before timing. Timed batches include the same mode/input selection and output
black-box consumption. Streaming rotates 32 pairs after batch-level eviction;
it is not per-call DRAM coldness. All 32 pairs are cross-checked before timing,
and every accepted batch checks its final output; the review does not claim
that every intermediate invocation in a timed batch is separately checked.

Precision and output completeness hold for the full registered domain:
`n*(2^p-1)^2 < 2^q`. At `n=1024,p=53`, the bound is
`2^116 - 2^64 + 1024 < 2^116`, so 128-bit oracle digits cannot carry into
neighbors. The widest packed product occupies 4,096 u64 words, and extraction
retains every coefficient including the final zero coefficient. This is exact
runtime composition evidence, not a new universal formal composition proof.

The selection source identities are deliberately separate. The measurement
receipt's source map binds preregistered `analyze.py` to
`8469eab95bd2608d4b18229241078a510c3e2dab3a1b958b60e34bc96f0a779e`.
The final `analysis_script_sha256` binds the archived analysis script to
`8373387692748a718b2b0a6cb2af0b5c7b371d6d8e1924541d26d3f208014573`.
All function ASTs except `confirm` are identical; the inspected `confirm` diff
only corrects count metadata, adds its own hash and records the emulator caveat.
Selection predicates, eligibility and confirmation decisions are unchanged.
The frozen null-selection hash is
`5f0a009fbd541cf430586c81506e54f86216f0d4cbd7c4d7ea891ec9467aa9a7`.
Local retained filesystem provenance places selection at
`2026-11-08T03:12:57.2749923Z`, before confirmation-a executable creation at
`2026-11-08T03:13:42.9095636Z`. These timestamps and coordinator provenance
support the reported chronology; they are not an authenticated timestamp proof.
The decisive independent check uses discovery rows alone and produces the same
null result, regardless of confirmation outcomes.

The recomputed aggregate layout/bulk ratio is `0.9434685851099173`, ranging
from `0.67776605` to `1.18785872`, with 234 regressions, 138 exceeding 1% and
29 exceeding 5%. Winner signs change in 168 of 720 shape/phase pairs. Universal
bulk also fails, with geometric mean `1.0599187040059173` and 1,206 regressions
against layout. The best aggregate registered hybrid, layout for `n<=512`,
still has 93 discovery regressions. These facts support REPORT.md's negative
policy decision and its descriptive aggregate gains simultaneously.

The limitations in `REPORT.md:92`, `:127`, `:181` and `:216` are material to
this acceptance. The emulator was observed stopped before controlled timing
and running afterwards; continuous suspension was not monitored. No guaranteed
emulator-free result is accepted. This is one WSL2 machine, a finite one-limb
input matrix with `p<=53,n<=1024`, seven samples per group, and a strict observed
no-regression screen. It is not a confidence bound or a theorem about all
policies. The zero-margin stratum is descriptive and cannot be promoted into a
new rule. Held-out counts start at 60, limiting confirmation of very-small-count
rules. Bit complexity, peak space, full composition proof, solver integration,
automatic dispatch and GMP parity remain outside this review's acceptance.

The independent replay was run with:

```text
wsl -d Ubuntu -- taskset -c 2-15 python3 /mnt/e/3sat/VeriGMP-packed-crossover-sweep-20261108/experiments/packed-crossover-sweep-20261108/independent_audit.py --output /mnt/e/3sat/VeriGMP-packed-crossover-sweep-20261108/experiments/packed-crossover-sweep-20261108/evidence/independent-review-complete.json
```

For replay, choose a fresh output path; the script refuses to overwrite evidence.
It uses the recorded local dependency/library paths for the reproducible build.
The review program SHA-256 is
`ef7ea2363c329037434a200e1e76478577e7445cb4340c65f54815902e940a18`;
the complete audit JSON SHA-256 is
`fb50a9316565f2e9aff4378830af7f058500fdec98b3645327d4b7babb29823d`.
This review performs no merge or push.

# Forced Toom-4 experiment

This archive contains a verified Toom-4 candidate that has not been accepted for production dispatch. The public `native/` implementation remains at baseline `e22a4dd00a28681fd27d68e2a78fa304cf17563e`.

The candidate passed functional refinement and recorded correctness gates. Two complete timing runs showed improvements over the baseline at large sizes but missed the registered GMP target on all principal workloads. All measurements, including regressions, are retained.

## Algorithm and contracts

The implementation splits each input into four blocks. Evaluation computes seven products at points `0`, `1`, `-1`, `2`, `1/2`, `-1/2`, and infinity. Half-point operands are scaled by eight, so their products are scaled by 64. Interpolation recovers seven coefficients via exact divisions by powers of two and odd divisors `3`, `9`, and `15`.

| Layer | Archived source | Responsibility |
|---|---|---|
| Independent integer model | [toom4.rs](overlay/native/specs/toom4.rs), [toom4_blocks.rs](overlay/native/specs/toom4_blocks.rs) | Input-defined coefficients, evaluation identities, interpolation, block ranges and capacity inequalities |
| Evaluation | [toom4_evaluate.rs](overlay/native/verified/toom4_evaluate.rs) | Weighted and signed four-block evaluation with explicit carries |
| Interpolation | [toom4_interpolate.rs](overlay/native/verified/toom4_interpolate.rs) | Exact coefficient recovery and shifted assembly |
| Full recursion | [toom4_multiply.rs](overlay/native/verified/toom4_multiply.rs), [toom4_square.rs](overlay/native/verified/toom4_square.rs) | Seven recursive products or dedicated squares |
| Truncated arithmetic | [toom4_low.rs](overlay/native/verified/toom4_low.rs), [toom4_square_low.rs](overlay/native/verified/toom4_square_low.rs) | Existing low-product decomposition with Toom-4 full kernels |
| Experimental policy | [toom4_candidate.rs](overlay/native/verified/toom4_candidate.rs) | Fixed candidate dispatch used by the comparator |

Verus checks the actual Rust functions against independent integer meanings. Full equal-length products require `2n` output limbs and at least `12n` caller-owned scratch limbs. Dedicated full squares require `2n` output limbs and at least `10n` scratch limbs. Recursive slice capacities and termination obligations are proved. These are caller-scratch bounds, not a complete machine-stack bound.

For full recursion, let `k=ceil(n/4)`, `h=n-3k`, and `m=k+1`. Recursive calls have sizes `k`, `h`, and five copies of `m`. A monotone worst-case envelope gives `T_full(n) <= 2T_full(k)+5T_full(m)+O(n) <= 7T_full(m)+O(n)`. The analytic exponent is `log_4(7)` in limb count with a fixed cutoff. Dedicated square recursion has the same structure. Low products have `T_low(n) <= T_full(k)+2T_low(h)+O(n)`; low squares have `T_square_low(n) <= T_square_full(k)+T_low_product(h)+O(n)`, using the low kernels' own split sizes. These are analytic recurrences, not machine-checked cost theorems or claims about a complete solver.

[Scope](scope.json) states the precise domains. [Pinned GMP references](gmp-toom4-reference.json) identify the reference algorithms; the Rust implementation and proofs are independent.

## Verification record

[Complete historical report](evidence/verification.json) records:

- Baseline library: 234 verified items, zero errors. Candidate library and runner: 273 verified items each, zero errors.
- 25,062 independent integer-oracle cases: 11,292 existing cases and 13,770 new Toom-4 cases.
- Six invalid commands rejected and 18 semantic mutations rejected by verification conditions. Timeouts and tool errors do not count as successful mutation detection.
- Actual forced product and square paths reachable in optimized code, with no allocator, general-division call or per-element bounds-check panic on the inspected paths. Entry assertions, slice-region checks, copying and zero fill remain.
- Matching source, verifier, compiler, library and binary identities checked before and after the gate and both measurements.

Verus, vstd, Z3, Rust and LLVM remain trusted dependencies. The arithmetic core contains no added `assume`, `admit`, external body, custom axiom or GMP FFI. Runners, Python checkers and benchmark-only GMP calls are unverified test infrastructure. The separate experimental `mac4` path is not selected and retains its documented bounds checks.

## Performance

The predeclared candidate policy used Toom-4 from 512 limbs with full cutoff 256. Product low recursion retained limit 128 and split mode 2; square low recursion retained limit 64 and split mode 1. Inputs below 512 limbs called existing arithmetic.

Measurements used an AMD Ryzen 7 7745HX under x86-64 WSL2, CPU 0, GMP 6.3.0, Verus `0.2026.10.26.d17fbd0`, Rust 1.99.1 and `-O`. Both runs covered all 52 registered operation/precision shapes. Each mode had seven rotated repetitions; every recorded batch lasted at least 10 ms. Inputs and caller buffers were shared across modes; allocation was outside timing. GMP computed the full result followed by the same low-half copy and precision mask. The continuous measurement window passed the recorded idle-process preflight.

Each pair below is run 1 / run 2. Ratios are candidate time divided by comparator time. Smaller is faster.

| Operation | Limbs | Candidate / baseline | Candidate / GMP |
|---|---:|---:|---:|
| Product | 256 | 0.99874 / 1.01494 | 1.51868 / 1.48353 |
| Product | 512 | 0.95751 / 0.98664 | 1.66478 / 1.76458 |
| Product | 1024 | 0.98705 / 0.97624 | 1.80214 / 1.81193 |
| Product | 2048 | 0.91813 / 0.94005 | 1.93776 / 1.95960 |
| Product | 4096 | 0.91489 / 0.90951 | 2.15619 / 2.10776 |
| Square | 256 | 1.02256 / 1.01767 | 1.35007 / 1.37219 |
| Square | 512 | 0.98080 / 0.97772 | 1.44925 / 1.46118 |
| Square | 1024 | 0.93463 / 0.94500 | 1.68237 / 1.69143 |
| Square | 2048 | 0.96842 / 0.94878 | 1.88050 / 1.86477 |
| Square | 4096 | 0.89848 / 0.87639 | 1.94239 / 1.86450 |

Both runs missed the GMP target on all ten principal workloads. The 1.2-times-GMP limit failed on 34/52 and 35/52 shapes. Relative to the baseline, 20/52 and 23/52 shapes regressed. Twelve shapes regressed in both runs, all below 512 limbs. The result is `target_not_met`.

[Small-path audit](evidence/small-path-audit.json) found identical normalized instructions in 13 existing arithmetic functions. New entry wrappers differed: square added a length branch, product added a branch and register-save/restore trampoline. Static instruction differences do not establish how much these differences caused the observed slowdowns. Original small Toom paths retained the same 88-byte stack reservation.

[Complete matrix](evidence/performance-summary.json), [run 1 CSV](evidence/default1/benchmark.csv), [run 2 CSV](evidence/default2/benchmark.csv), and [measurement-window record](evidence/confirmation-window.json) retain every registered result. [Next-candidate analysis](next-candidate.json) is a proposal, not an implemented or measured optimization.

## Reproduce

Run these commands from a checkout of the `experiments/toom4` branch with its full Git history. Archive audit and source reconstruction need Python 3.12 and Git. These commands verify that all 145 frozen input files match their historical SHA-256 values.

```sh
python3 experiments/toom4/audit.py
python3 experiments/toom4/prepare.py --output /tmp/verigmp-toom4-prepared
```

Preparation refuses to overwrite an existing directory. The [recorded reconstruction check](reconstruction-check.json) is not a fresh proof or benchmark run.

Fresh verification requires x86-64 Linux or WSL, rustup, a C++ compiler, binutils and GMP 6.3.0 development headers and libraries. Install the pinned Rust toolchain and verifier, then use a different output directory:

```sh
rustup toolchain install 1.99.1
python3 scripts/setup_verus.py
export VERUS_BIN="$(pwd)/deps/verus/verus-x86-linux/verus"
python3 experiments/toom4/prepare.py --output /tmp/verigmp-toom4-verified --verify
```

`--benchmark` implies fresh verification and then runs exactly two complete measurements with the frozen idle-window controller:

```sh
python3 experiments/toom4/prepare.py --output /tmp/verigmp-toom4-measured --benchmark
```

The controller uses CPU 0 and refuses a busy preflight. It does not retry measurements based on favorable results. Archive CI audits stored evidence and reconstructs sources; it does not run new proof or timing experiments.

## Evidence layout

`overlay/` contains the 12 changed or new source files. `baseline-byte-overrides/` preserves original mixed-line-ending bytes where necessary. [candidate.patch](candidate.patch) provides a normalized review diff. [publication.json](publication.json) maps original and published SHA-256 values. Source and CSV bytes are unchanged; host paths in historical reports and logs are replaced by logical placeholders. Binary objects and the large oracle output are omitted, identified by digest, and regenerated by verification. `attempts/` retains failed development evidence separately from the passing complete gate.

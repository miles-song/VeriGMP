# Low-Square Direct Generic Fallback Acceptance

## Scope

Candidate source is commit `810b867e7b4e2c43c82e107db2a79c425e52bf29` on
`codex/low-square-25-64`. It sends top-level `square_mod` inputs of 25 through
64 limbs directly to the proved symmetry-specialized low-square leaf. Every
other size uses the generic `square_low::low` path and its existing recursive
dispatch. The comparison source is generic baseline
`96ca54d94ee24013cd64c66fb0a7eac4ef42f4cc`.

The candidate library proof, independent integer oracle, semantic mutations,
optimized code generation, and focused runtime comparison all passed. This
does not establish the library-wide GMP target: the candidate met 20 of 54
registered default operation and shape bounds; the baseline met 17 of 54 in
this run. All five principal sizes for each operation remained slower than the
registered GMP control. Independent Astra review is still required before this
candidate can be considered for merge.

## Proof and Correctness

The candidate's fresh source-bound `scripts/verify.py` run passed with 225
verified library items. The Toom and square gate passed 9,852 integer-oracle
cases through 4,097 limbs, rejected 17 of 17 semantic mutations, compiled the
optimized code, and passed production code-generation inspection. The mutation
set included deleting the second low-square cross-product addition and changing
the low-square cross term. The optimized production call graph had no allocator,
general division, or element-bounds panic. The low-square leaf retained the
same low-square refinement and scratch contract.

The generic baseline was independently rebuilt from its pinned source archive.
Its Toom runner verified 220 items, passed the same 9,852 oracle cases, and its
optimized code generation was inspected. The baseline and candidate benchmark
runner source is byte-identical.

| Identity | SHA-256 |
|---|---|
| Candidate `native/verified/arithmetic.rs` | `e48e93cddc5ecedd8349cc2722d81d5d7fb1781af51998f5ea4b697fbf4ba190` |
| Candidate `native/verified/square_low.rs` | `8821e24fdcfce9b0982c52a4d38c4ca56d7461bd7d056c057d74df2012cdda13` |
| Baseline `native/verified/arithmetic.rs` | `7c0181fed9d53f842062fd2f4e738dedf42985fee28bff53cabba4a7fc20cc54` |
| Baseline `native/verified/square_low.rs` | `1ec917ab1a36d35e2401fa4a35bee5202adaeb905bfc0009f3b3e48a4685838d` |
| Shared `native/toom_bench.rs` | `3a547dbc3391fb95df3bc9fa81e945da58d40dc316f746f11416ee824cbebf8e` |
| Verus executable | `1208c995c8e5244577693eba311d34bc2050c4acf984e10c4c7baf2003abff14` |
| GMP shared library | `0ccdfb6d6f5c039465f6d002cf7e4c072d48ac6a2cffc8dd6c748dec31592804` |

Full reports, raw observations, and the pooled result are retained under
`docs/data/2026-11-04-low-square-25-64-direct-generic/`. They bind the evidence
to these source hashes and tool identities.

## Measurement Protocol

Measurements ran in WSL2 Ubuntu 24.04 on Linux
`6.6.87.2-microsoft-standard-WSL2`, AMD Ryzen 7 7745HX. Each process was pinned
to CPU 0. The verifier was Verus `0.2026.10.26.d17fbd0`; Rust was
`1.99.1-x86_64-unknown-linux-gnu` with LLVM 23.1.1; GMP was 6.3.0.

The same seed (`16438731`), generated operands, preallocated buffers, modulo
`2^p` semantics, correctness checks, six benchmark modes, seven repetitions,
and minimum 10 ms recorded batches were used for both source snapshots. Modes
and shapes followed the registered benchmark harness. The four fresh processes
in each order were `baseline, candidate, candidate, baseline` (ABBA) and
`candidate, baseline, baseline, candidate` (BAAB). Every process exited 0 and
produced 2,268 measurement rows across 324 groups, with seven samples per group.
The shortest recorded batch was 10.001 ms. Empty stderr files and exit records
are retained beside each raw CSV.

The binaries were compiled with the pinned Verus executable using:

```sh
"$VERUS" "$BASE/native/toom_bench.rs" --compile -O -o baseline-toom-bench
"$VERUS" "$CANDIDATE/native/toom_bench.rs" --compile -O -o candidate-toom-bench
```

Each measurement process used the following command, with the binary, output
path, and role changed to follow the orders above:

```sh
taskset -c 0 "$BINARY" 16438731 > "$RAW_CSV" 2> "$STDERR"
```

Raw CSV SHA-256 values:

| Order | Process | SHA-256 |
|---|---|---|
| ABBA | 1 baseline | `cec586e41b6bda2b136fa1287a621a3ec5ca10dd51fc8267e7e12d601bf6fa31` |
| ABBA | 2 candidate | `4054310dca891401752a7be1252521e73db5bbe4e9bcbdf3a152e0b59b2940b9` |
| ABBA | 3 candidate | `18b561af4c2b6229e2348d551238d8a9ff35144b15cef12c69620734da52fd11` |
| ABBA | 4 baseline | `af3a8b2e67e0ec50ec74c07ec3837e55f0d46acbe2bc06aa42d832980fd18200` |
| BAAB | 1 candidate | `a284ef0aeb552bf16a805bded67eed9c8614003f42793ca4256de7a64e97fe02` |
| BAAB | 2 baseline | `fcdf54234ae8aeeab4342deb2e42f17465ebaa5b413a0a787705f6b0b10ec174` |
| BAAB | 3 baseline | `c86fc1e9e57ba7a85640140b21fc04f45d1fe5559dd866a088f1d27f4b6d4a27` |
| BAAB | 4 candidate | `caf1517cdc63ee8cdf7d31d477f1d6b5ff83a530554e0db4dd669cfa731428e2` |

Reported times are pooled medians across the four process-level medians for
each mode and shape. ABBA and BAAB deltas are computed from the two candidate
and two baseline process medians within each order. GMP mode uses the same
public full-product followed by low-half copy and precision-mask control used
by the registered target. These are local runtime observations, not worst-case
bounds or a machine-checked complexity theorem.

## Results

| Limbs | Candidate `square_mod` ns | Baseline ns | Candidate / GMP | ABBA delta | BAAB delta | Pooled delta |
|---:|---:|---:|---:|---:|---:|---:|
| 24 | 247.266 | 267.634 | 1.319 | -8.17% | -6.50% | -7.61% |
| 25 | 202.710 | 267.738 | 1.003 | -27.05% | -22.15% | -24.29% |
| 26 | 212.143 | 295.199 | 0.895 | -16.04% | -31.49% | -28.14% |
| 63 | 907.053 | 1,601.068 | 0.920 | -41.94% | -43.40% | -43.35% |
| 64 | 920.902 | 1,628.515 | 0.924 | -38.51% | -43.24% | -43.45% |
| 65 | 1,076.714 | 1,012.894 | 1.023 | +4.98% | +8.16% | +6.30% |

The specialized range improved all four measured sizes from 25 through 64 in
both order-specific comparisons and pooled medians. At 65 limbs, the generic
fallback is 6.30% slower than the generic baseline in the pooled comparison;
the two order-specific results agree on the regression. It remains within the
nonprincipal 1.2-times-GMP bound at this shape. The 24-limb generic fallback
was 7.61% faster in this run.

This 65-limb change is associated with the candidate's new leaf branch and the
compiler's resulting `verified_square` code generation. The generic
`square_low::low` source body is unchanged from baseline, but the candidate's
inlined optimized function reserves an 88-byte stack frame versus 24 bytes in
baseline. This supports a candidate-induced code-generation cost; the timing
does not isolate the stack frame as the sole cause, so it should not be
described as proven to be either stack traffic or compiler noise.

The candidate's measured default met 20 of 54 registered key-shape bounds,
versus 17 of 54 for the baseline in this run. At 65 limbs candidate `square_mod`
was 1.023 times GMP, inside the 1.2 nonprincipal bound. Median candidate/GMP
ratios across principal sizes were 1.861 for `mul_mod` and 1.806 for
`square_mod`; all ten principal workloads exceeded the 1.0 limit. This
focused result supports the 25-through-64 square optimization only; it does not
meet library-wide GMP parity and does not justify backend promotion.

# Low-Square Direct Generic Fallback Acceptance

## Scope

Candidate arithmetic source is commit `810b867e7b4e2c43c82e107db2a79c425e52bf29` on
`codex/low-square-25-64`. It sends top-level `square_mod` inputs of 25 through
64 limbs directly to the proved symmetry-specialized low-square leaf. Every
other size uses the generic `square_low::low` path and its existing recursive
dispatch. The comparison source is generic baseline
`96ca54d94ee24013cd64c66fb0a7eac4ef42f4cc`.

Relative to `810b867`, all files under `native/` are byte-identical. The
verification-harness delta adds an executable leaf mutant, retains mutant
sources and raw diagnostics, and permits the targeted Toom gate to finish
without running benchmarks. The remaining delta consists of evidence and
documentation. The existing matched performance observations apply to the same
arithmetic source and were preserved.

The candidate library proof, independent integer oracle, semantic mutations,
optimized code generation, and focused runtime comparison all passed. This
does not establish the library-wide GMP target: the candidate met 20 of 54
registered default operation and shape bounds; the baseline met 17 of 54 in
this run. All five principal sizes for each operation remained slower than the
registered GMP control. Independent Astra review is still required before this
candidate can be considered for merge.

## Proof and Correctness

The full source-bound `scripts/verify.py` run for `810b867` passed with 225
verified library items. Its Toom and square gate passed 9,852 integer-oracle
cases through 4,097 limbs and rejected 17 of 17 semantic mutations. In that
set, `missing_double_cross` deletes the second executable addition from the
generic `square_low::low` path using `temp`; `wrong_low_square_cross` changes
only the new leaf's ghost coefficient from `c2=value(cross@)` to `c2=0`.

The targeted source-bound gate with the extended harness independently passed
the 225-item library proof, the 225-item Toom runner proof, the same 9,852
integer-oracle cases, 11 invalid-input rejections, 18 of 18 semantic mutations,
and optimized production code-generation inspection. The eighteenth mutant,
`omit_leaf_second_cross_add`, removes the actual second
`limbs::add_assign(&mut dst[k..],cross)` call from `base_low_square`, retaining
the ghost coefficient and proof code. Its raw diagnostic reports a genuine
verification-condition failure at the following `congruent_suffix` proof call;
the result is `224 verified, 1 errors`, with the failed precondition at mutated
`square_low.rs:45`. It is not a parse, type, resource-limit, or timeout rejection. The mutant source
and raw diagnostic are retained with their hashes in
`proof/mutation-repair/toom/`.

The optimized production call graph had no allocator, general division, or
element-bounds panic. The low-square leaf retained the same refinement and
scratch contract. The targeted gate performed no timing; the full run's timing
data is superseded for this decision by the exclusive matched suite below.

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

| Evidence identity | SHA-256 |
|---|---|
| Candidate `810b867` Git source archive | `7f0e48e8e57d234de6b4d021aa65ce7ab15ff326721b093f94b39765e6776f07` |
| Baseline `96ca54d` Git source archive | `81dd8048075e987e05ae628f4414fbfc898ad8c1fc71335290e2f2fb66f9edaf` |
| Extended `scripts/verify_toom.py` | `7742813570d281c2131186889d5d600d6cba8d59c1e1dffcdbec6e08a0cfa976` |
| Targeted gate runner | `7c13a71762b1ff3b2f23d1a275afe23086eca77e981b16f746f35b4f8c6464b0` |
| Targeted source manifest | `b701636fa3d9a17bd3c3c64aaf743404e634a07c4bcf78dd3ebc82af1ce9faee` |
| Targeted gate report | `74a1c7e63a57b8d964a83e82a916364d28953ee0a731d6d97e12a3c6253f3921` |
| Targeted Toom report | `8d227e714b59f0f735542ba7e4d0e2b06650aea29ced390d07a0fd00cf943474` |
| Executable leaf mutant source | `8cf14fcb61c172a38966f6622f6ef1792171e0e57135d032e8b9f2966469bde4` |
| Executable leaf mutant raw log | `c1d84b47202614ebbe65914fc35efd6f1fc1c491f073dd5b1d310bdf19190013` |
| Extended matched `summary.json` | `3927c9e152435da0b640795e601df51d9cfbbf7c2829e359a13cdcac7264f676` |

Full reports, raw observations, and the pooled result are retained under
`docs/data/2026-11-04-low-square-25-64-direct-generic/`. They bind the evidence
to these source hashes and tool identities.

The targeted gate and registered-target validation commands were:

```sh
python3 docs/data/2026-11-04-low-square-25-64-direct-generic/proof/mutation-repair/run-targeted.py \
  "$PWD" "$PWD/results/low-square-25-64-direct-generic-810b867/mutation-repair"
python3 docs/data/2026-11-04-low-square-25-64-direct-generic/matched/summarize-target.py "$PWD"
```

The gate freezes all native Rust and control sources, native JSON inputs, and
Python verification scripts. Its LF-normalized source manifest, actual tool
hashes, commands, library artifacts, oracle identities, mutation identities, and
code-generation identity are recorded in
`proof/mutation-repair/verification.json` and `source-sha256.tsv`.

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

Two registered bounds newly fail: `mul_mod` at 127 limbs changes from
1.158925 times GMP to 1.202393, and `square_mod` at 128 limbs changes from
1.194659 to 1.231350. Both have a 1.2 limit. Five square bounds newly pass,
at 25, 26, 63, 64, and 192 limbs, giving the net increase from 17 to 20 passes.
The 192-limb crossing is relative to that run's GMP control; its candidate
default runtime is slightly slower than baseline. These observations do not
establish that every out-of-scope workload is unaffected.

All 54 official default workloads are listed below. Each cell is the pooled
default/GMP ratio followed by its registered pass/fail result. Principal sizes
are exactly 256, 512, 1024, 2048, and 4096; the other shapes use the 1.2 limit.
The JSON contains one record per operation and registered shape, with actual
default and GMP medians for each source. Only benchmark mode 5 supplies the
default and mode 4 supplies GMP; forced modes are excluded from these counts.

| Limbs/top | Limit | Baseline `mul_mod` | Candidate `mul_mod` | Baseline `square_mod` | Candidate `square_mod` |
|---|---:|---:|---:|---:|---:|
| 1/1 | 1.2 | 0.854822 pass | 0.898082 pass | 0.838544 pass | 0.960533 pass |
| 1/64 | 1.2 | 0.806531 pass | 0.881192 pass | 0.861387 pass | 0.967713 pass |
| 2/1 | 1.2 | 0.691468 pass | 0.726531 pass | 0.684542 pass | 0.759539 pass |
| 23/63 | 1.2 | 0.761390 pass | 0.715593 pass | 1.342990 fail | 1.334461 fail |
| 24/63 | 1.2 | 0.773723 pass | 0.770548 pass | 1.400292 fail | 1.318767 fail |
| 25/63 | 1.2 | 0.836453 pass | 0.746557 pass | 1.345020 fail | 1.003046 pass |
| 26/63 | 1.2 | 0.753017 pass | 0.800333 pass | 1.375841 fail | 0.895339 pass |
| 63/63 | 1.2 | 1.168951 pass | 1.179552 pass | 1.655908 fail | 0.920405 pass |
| 64/63 | 1.2 | 1.151688 pass | 1.153968 pass | 1.656362 fail | 0.924242 pass |
| 65/63 | 1.2 | 1.159944 pass | 1.138188 pass | 0.999670 pass | 1.023073 pass |
| 127/63 | 1.2 | 1.158925 pass | 1.202393 fail | 1.176320 pass | 1.164766 pass |
| 128/63 | 1.2 | 1.218074 fail | 1.210758 fail | 1.194659 pass | 1.231350 fail |
| 129/63 | 1.2 | 1.207275 fail | 1.230937 fail | 1.220918 fail | 1.222922 fail |
| 191/63 | 1.2 | 1.356171 fail | 1.409770 fail | 1.251709 fail | 1.250422 fail |
| 192/63 | 1.2 | 1.344704 fail | 1.346372 fail | 1.271084 fail | 1.197008 pass |
| 193/63 | 1.2 | 1.330761 fail | 1.383558 fail | 1.237684 fail | 1.259821 fail |
| 255/63 | 1.2 | 1.489018 fail | 1.473620 fail | 1.347240 fail | 1.308157 fail |
| 256/63 | 1.0 | 1.504338 fail | 1.495925 fail | 1.322117 fail | 1.314407 fail |
| 257/63 | 1.2 | 1.454109 fail | 1.461712 fail | 1.322437 fail | 1.307532 fail |
| 511/63 | 1.2 | 1.692336 fail | 1.721440 fail | 1.489937 fail | 1.559514 fail |
| 512/63 | 1.0 | 1.700384 fail | 1.753061 fail | 1.449875 fail | 1.490176 fail |
| 513/63 | 1.2 | 1.667355 fail | 1.721936 fail | 1.479129 fail | 1.475270 fail |
| 1023/63 | 1.2 | 1.843888 fail | 1.866400 fail | 1.761045 fail | 1.809472 fail |
| 1024/63 | 1.0 | 1.845836 fail | 1.860745 fail | 1.788903 fail | 1.805827 fail |
| 1025/63 | 1.2 | 1.787537 fail | 1.815832 fail | 1.732613 fail | 1.748933 fail |
| 2048/63 | 1.0 | 2.114034 fail | 2.105717 fail | 1.912664 fail | 1.886535 fail |
| 4096/63 | 1.0 | 2.272742 fail | 2.259155 fail | 2.110812 fail | 2.128831 fail |

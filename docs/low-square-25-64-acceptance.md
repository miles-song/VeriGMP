# Low-Square Leaf Acceptance

## Scope

Source under test is branch `codex/low-square-25-64`, commit
`8ad982507546c12b3d020b8a11a5fdeef331daca`, based on VeriGMP `c083839`.
Production `square_mod` enables the symmetry-specialized low-square leaf only
when the top-level input length is 25 through 64 limbs. Smaller inputs and
inputs above 64 limbs retain the generic or recursive low-square algorithm. The
leaf computes a full square of the low `ceil(n/2)` limbs and one low product
between the lower and upper blocks, then adds that cross product twice. Its
word-multiplication count is analytic, not a machine-checked cost theorem.

The leaf preserves the exact low-square refinement and caller-owned scratch
contract. Source-bound candidate acceptance verified 226 items, passed 9,852
integer-oracle cases up to 4,097 limbs and rejected all 17 semantic mutations,
including removal of the low-square cross term. The detached generic baseline
at `96ca54d94ee24013cd64c66fb0a7eac4ef42f4cc` verified 220 items and passed the
same oracle. Its arithmetic state is pinned baseline `c083839`; its measurement
commit adds only the shared 26-limb benchmark registration and runner changes.

The full VeriGMP/GMP parity target remains unmet. The official evaluators report
`target_not_met`: 37 of 54 registered workloads fail for the baseline and 34 of
54 for the candidate. All five candidate principal sizes exceed the evaluator's
per-workload 1.0 ratio limit. The median across those five per-workload ratios
is 1.886 for `mul_mod` and 1.830 for `square_mod` on the candidate, versus
1.819 and 1.753 on the baseline. No backend promotion or GMP replacement
follows from this library-only result.

## Method

The registered suite contains 27 `(limbs, top)` shapes for both operations,
including 24/25/26 and 63/64/65. Its six modes run in rotated order within each
repetition. Each fresh process used seed `16438731`, equal generated operands,
the same modulo-`2^p` semantics, preallocated output and scratch, a correctness
check against GMP before timing, seven repetitions per mode and shape, and
recorded batches of at least 10 ms. Four separate processes used ABBA order
(baseline, candidate, candidate, baseline); four used BAAB order (candidate,
baseline, baseline, candidate). All eight exited successfully with 2,268 rows
each, 324 groups and seven valid samples per group. Every process was pinned to
CPU 0.

The table reports pooled medians across the four baseline and four candidate
processes. Ratios are elapsed time divided by the public GMP full-product plus
required low-half copy and precision mask. Delta is candidate median time versus
baseline median time. Results apply only to this WSL2 Linux environment,
processor, pinned toolchain and registered workload set.

| Limbs | Top bits | `mul_mod` baseline/GMP -> candidate/GMP (delta) | `square_mod` baseline/GMP -> candidate/GMP (delta) |
| ---: | ---: | ---: | ---: |
| 1 | 1 | 0.814 -> 0.894 (+9.76%) | 0.879 -> 0.880 (+0.17%) |
| 1 | 64 | 0.808 -> 0.876 (+8.45%) | 0.831 -> 0.884 (+6.42%) |
| 2 | 1 | 0.695 -> 0.757 (+8.84%) | 0.699 -> 0.720 (+2.92%) |
| 23 | 63 | 0.795 -> 0.736 (-7.39%) | 1.365 -> 1.307 (-4.25%) |
| 24 | 63 | 0.777 -> 0.752 (-3.15%) | 1.321 -> 1.348 (+2.09%) |
| 25 | 63 | 0.776 -> 0.740 (-4.57%) | 1.378 -> 0.937 (-32.00%) |
| 26 | 63 | 0.764 -> 0.742 (-2.93%) | 1.402 -> 0.919 (-34.48%) |
| 63 | 63 | 1.175 -> 1.144 (-2.63%) | 1.614 -> 0.914 (-43.35%) |
| 64 | 63 | 1.206 -> 1.164 (-3.49%) | 1.674 -> 0.917 (-45.20%) |
| 65 | 63 | 1.154 -> 1.146 (-0.70%) | 0.975 -> 1.040 (+6.70%) |
| 127 | 63 | 1.197 -> 1.172 (-2.09%) | 1.230 -> 1.216 (-1.12%) |
| 128 | 63 | 1.234 -> 1.244 (+0.83%) | 1.200 -> 1.231 (+2.54%) |
| 129 | 63 | 1.184 -> 1.206 (+1.86%) | 1.219 -> 1.226 (+0.55%) |
| 191 | 63 | 1.385 -> 1.344 (-3.00%) | 1.244 -> 1.282 (+3.08%) |
| 192 | 63 | 1.371 -> 1.339 (-2.32%) | 1.225 -> 1.220 (-0.41%) |
| 193 | 63 | 1.344 -> 1.337 (-0.58%) | 1.264 -> 1.217 (-3.72%) |
| 255 | 63 | 1.475 -> 1.475 (-0.02%) | 1.324 -> 1.318 (-0.49%) |
| 256 | 63 | 1.510 -> 1.516 (+0.39%) | 1.320 -> 1.346 (+1.90%) |
| 257 | 63 | 1.441 -> 1.418 (-1.62%) | 1.330 -> 1.295 (-2.58%) |
| 511 | 63 | 1.688 -> 1.705 (+0.98%) | 1.482 -> 1.507 (+1.73%) |
| 512 | 63 | 1.749 -> 1.761 (+0.72%) | 1.535 -> 1.470 (-4.22%) |
| 513 | 63 | 1.720 -> 1.691 (-1.66%) | 1.463 -> 1.482 (+1.27%) |
| 1023 | 63 | 1.878 -> 1.899 (+1.12%) | 1.792 -> 1.724 (-3.77%) |
| 1024 | 63 | 1.922 -> 1.854 (-3.56%) | 1.797 -> 1.812 (+0.81%) |
| 1025 | 63 | 1.857 -> 1.755 (-5.54%) | 1.791 -> 1.739 (-2.93%) |
| 2048 | 63 | 2.169 -> 2.065 (-4.77%) | 1.971 -> 1.817 (-7.83%) |
| 4096 | 63 | 2.268 -> 2.229 (-1.73%) | 2.166 -> 2.044 (-5.62%) |

For `square_mod`, candidate medians improved at 25, 26, 63 and 64 limbs by
32.00%, 34.48%, 43.35% and 45.20%. The generic 24-limb case was 2.09% slower
than baseline in the pooled medians; the original-recursion 65-limb case was
6.70% slower. The ABBA/BAAB comparisons at those boundaries were +3.07%/-0.36%
at 24, -34.62%/-30.73% at 25, -35.71%/-35.65% at 26, -43.15%/-43.96% at 63,
-47.92%/-41.98% at 64, and +4.77%/+10.25% at 65. This leaves 24 and 65 as
mixed or regressed boundaries to watch.

## Reproduction

Measurements ran on WSL2 Linux `6.6.87.2-microsoft-standard-WSL2`, AMD Ryzen 7
7745HX, available affinity 0-15, with each benchmark process pinned to CPU 0.
A pre-run WSL load-average snapshot was `0.79, 3.01, 2.86` (1, 5 and 15
minutes).
Toolchain: Verus `0.2026.10.26.d17fbd0`, Rust
`1.99.1-x86_64-unknown-linux-gnu`, GMP 6.3.0 and C++ 13.3.0. Both benchmark
binaries linked the same GMP library SHA-256
`0ccdfb6d6f5c039465f6d002cf7e4c072d48ac6a2cffc8dd6c748dec31592804`.
The Verus executable SHA-256 is
`1208c995c8e5244577693eba311d34bc2050c4acf984e10c4c7baf2003abff14`.
The fresh stand-alone ABBA/BAAB baseline and candidate benchmark binary
SHA-256 values are
`9b0e803e3d61845552b01ba371671037e7781e0b278563dcdc3216a4208f56d7` and
`47f5f6f41392278462cb0459668044759ffad8d139c7730bfa8faf17e1283fd7`.
The registered harness files are byte-identical across baseline and candidate:
`native/toom_bench.rs` SHA-256
`3a547dbc3391fb95df3bc9fa81e945da58d40dc316f746f11416ee824cbebf8e`,
`scripts/verify_toom.py` SHA-256
`25be77d609a1eb2d3c7ea78f2cdc3586f43519dfc84d409f00919e8eb032b52d`, and
`native/performance-target.json` SHA-256
`bb61e0eb2049435b2e30ffac5a411d9bbc9c96a1b3d90146a509b3502baa52eb`.
The frozen toolchain manifest SHA-256 is
`a8f1ba756fd50480017e10d24c390a4b94528ab387c965d28c35cf3432c9e678`.
Candidate arithmetic hashes are `native/verified/arithmetic.rs`
`6a83daa34bfdefadf16f39156ebd5b7aef8ee68ef86f3b1b560894fa7322dd68` and
`native/verified/square_low.rs`
`c9028937653ee54c86bfd01c5329e88e5f44bcb4683c224d67215ddc17d8c257`.

Full acceptance reports and official evaluator outputs are retained at:

- Baseline: `E:\3sat\VeriGMP-low-square-gated-baseline\results\low-square-gated-8ad9825\full\baseline\acceptance\`.
  Raw benchmark CSV SHA-256 `fbb55ebac2de88847fecca5285c4768b98dc927356c37d7026b4e5f237d3da85`;
  verification JSON SHA-256 `7c3e2d947e75e895796e67d5068d55dd37c76b598a88354dcaff4400cd1919ae`.
  Official evaluator JSON at `../performance-target.json` has SHA-256
  `ebf29b281ccf213bb3f48eb4b6c586517e1a833d53b3e47ca0a24f66ecf32360`.
- Candidate: `E:\3sat\VeriGMP-low-square-gated\results\low-square-gated-8ad9825\full\candidate\acceptance\`.
  Raw benchmark CSV SHA-256 `958948a65182799807329d2b0ad2c65bb686a92a42d6d4dcfd5f3d6fc80a8e7d`;
  verification JSON SHA-256 `284c8447e8faf08ff768a90c9fa5bf7eb3a3744f4212fed85d75cc1b0fc5525d`.
  Official evaluator JSON at `../performance-target.json` has SHA-256
  `2b5bbdc57459299df2b8d4c214b9a4f347f245d781875c7a25dafbf69fce0551`.

The eight four-run raw CSVs are retained under
`E:\3sat\VeriGMP-low-square-gated\results\low-square-gated-8ad9825\ab-ba\`
and `...\ba-ab\`. The pooled table is `registered-shape-medians.csv`, SHA-256
`fe0076fb145e5612571f91fd35297ed659728a8d9db41fd8d958a260401fd3c4`.
The aggregate with separate ABBA and BAAB deltas is
`aggregated-registered-medians.csv`, SHA-256
`82e51b69c789a4e3d820e15611bbb276a67f1773443b7fb00600ce4a619e54cd`.
In ABBA run order, CSV hashes are `affbf023cef0056ed70bcbf8be0f4d2af62448f31021a6edc87b44eeeb67d94`,
`f1e2af8c2cd9f1907ed114fbf5dc8170cf689018ebfb4fc324e06151643e0cf7`,
`f756e7cfd312138076368085ab14b86d4b67b3fa1ba0fa2fdae5521bbd947393`, and
`96b71b35895373ded186184343cc599880f392e000743795f58c321c964eeabd`.
In BAAB order, hashes are `230899e03bfc58ad3313892110b5c165d925c84757e0d6a386d3d061ed3ead55`,
`ff658b5cfa355600fed7fc389325a3dad38d37ccc0c7dd9a47ce4a6882212b59`,
`ef4c4b85ade9514f01b30d4406cdddf219490e857814ce2e86a141c289c2f040`, and
`c43e53277ba65cc5548b834e99529beb4a44c8e877c11fae55ac3d52d2ec13a3`.

These are local WSL verification and measurements. Remote CI was not run; no
push was made. No representative solver trace was measured, so this work does
not establish SAT-solver performance. The VeriGMP consumer continues to use
trusted GMP pending separate semantic and whole-workload acceptance.

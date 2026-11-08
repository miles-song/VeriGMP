# Checked-recursion experiment: no-go result

**Disposition: valid negative evidence; do not promote the private-recursion
candidate.** Neither run met the frozen promotion criteria. The
candidate remains reachable in branch history at
`905edec767a9e5eeee838e083cad93e027d73c51` with fixed native source
`b31fbce898054f6db668277f8a4da88f94c95aa2`. Production native sources and
`native/proof-status.json` are restored byte-for-byte to baseline
`de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9`. No runtime optimization, dispatch
change, speedup, GMP parity, or solver/backend replacement is accepted.

The public `fast_multiply::full` originally performs buffer and threshold
assertions on each recursive call. The experiment moved same-contract recursive
work into a private verified worker while preserving the public checks and
direct small-input `base_full` call. The complete modified library passed 359
Verus items at the fixed candidate source; that is historical candidate
evidence, not a proof count for production after restoration. Production has the
baseline's 358-item verified library identity, reused by exact source/tool and
export hash rather than re-proved for this evidence-only result.

The measured package accepts both completed runs as protocol-valid, then applies
the predeclared gates separately to each run:

| Frozen criterion | Run 1 | Run 2 |
| --- | ---: | ---: |
| Geometric mean over 27 forced full-product sizes with `n > 24`; limit `<= 0.97` | `0.9997460919631549` fail | `1.0028851442261115` fail |
| Maximum candidate/baseline median over all 86 cells; limit `<= 1.05` | `1.0554729047100921` fail | `1.0455882132295198` pass |
| Cells slower than baseline, ratio `> 1.00` | 44 | 43 |
| Cells slower than baseline by more than 5%, ratio `> 1.05` | 1 | 0 |
| Promotion | **NO-GO** | **NO-GO** |

The sole ratio above 1.05 is forced full multiplication at `n=191`, `top=64`,
threshold 24 in Run 1: baseline `13,686.3076171875 ns/op`, candidate
`14,445.52685546875 ns/op`. Run 2's maximum is the unchanged default square
control at `n=23`, `top=63`, ratio `1.0455882132295198`; it is retained and is
not attributed to this multiplication change. No averaging, threshold tuning,
shape removal or retry follows the failed gate.

Each run contains 86 registered cells, seven accepted samples for each of three
paths, and 258 calibration calls: 2,064 invocations / 6,192 durable raw records.
All samples exceed 10 ms (minimum `18,567,032 ns` and `18,613,079 ns`), with no
short-sample retries or failed process calls. Every full 86-cell ratio and raw
record remains in the package and `all-86-ratios.csv`.

The separate GMP comparison remains below the registered target. Each run has
ten principal workload ratios above 1.0. Across the 52 default key cells, 34
cells in Run 1 and 32 in Run 2 exceed 1.2 times GMP. This experiment does not
change or replace the consuming solver's trusted GMP backend.

Both runs used the same frozen optimized binaries and seed on one AMD Ryzen 7
7745HX / WSL2 host, pinned to logical CPU 8. The external
host receipt binds the exact emulator and QEMU process IDs, start times, image
hashes, suspend/resume statuses, thread states and process CPU counters. Both were observed
fully suspended for the measured window and resumed by the wrapper's `finally`
path; ADB was not stopped. These observations do not establish that the whole
machine was continuously free of interference or that results generalize to
other platforms.

The independent final audit verdict is **VALID NEGATIVE EVIDENCE / NO-GO
PROMOTION**. It independently replayed all raw rows and medians; its exact review
and replay artifacts are bound in `manifest.json` and `evidence.zip`.

For offline validation, use [CHECKER_USAGE.md](CHECKER_USAGE.md) and
[check_evidence.py](check_evidence.py). The archive contains the historical
359/0 candidate proof only under its fixed source identity, exact baseline
358-item producer export identity, complete codegen review, initial static
review, harness correction review, both independent timing reports/raw streams,
host restoration receipt and final negative audit. The archive is evidence for
this no-go experiment; it is not a runtime feature artifact.

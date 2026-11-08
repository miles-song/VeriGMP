# Arithmetic experiments

These archives retain candidate source, independent oracle drivers, proof logs,
raw measurements and reproducible preparation scripts. The machine-readable
[index](index.json) pins the seven archive commits and their independent audit.
All candidates in these archives remain experimental. Individual optimizations
can be enabled through scoped dispatch after reproducible gains against the
current implementation, relevant regression and combination measurements,
same-source proof and correctness checks, independent review and exact-commit CI.
They need not first meet the overall GMP target. Replacing a consuming solver's
trusted GMP backend additionally requires the complete registered
[performance target](../native/performance-target.json), independent confirmation
and acceptance of the solver's actual dependency path and representative traces.

| Archive | Optimization mechanism | Accepted scope |
| --- | --- | --- |
| [scaled-subtraction](scaled-subtraction/index.json) | Double-carry, single-carry and split-slow-path scaled subtraction | Three reproducible experiments; GMP target not met |
| [toom4](toom4/index.json) | Four-way evaluation, recursive multiplication and interpolation | Verified candidate and measurements; GMP target not met |
| [toom4-entry](toom4-entry/index.json) | Toom-4 entry-policy changes | Verified candidate and measurements; GMP target not met |
| [odd-division](odd-division/index.json) | Exact division by odd interpolation constants | Verified candidate and measurements; GMP target not met |
| [toom4-fusion](toom4-fusion/index.json) | Four-group interpolation fusion and scaled subtraction | Verified candidate and measurements; GMP target not met |
| [toom4-signed-eval](toom4-signed-eval/index.json) | Single-pass signed evaluation | Verified candidate and measurements; GMP target not met |
| [toom8-primitives](toom8-primitives/) | Toom-8 arithmetic primitives and composition gates | Reproducible primitive archives; production performance acceptance remains open |
| [combination-20261108](combination-20261108/) | Fused doubled-cross low-square correction with checked private Karatsuba recursion | Four-cell combination static gate passes; prereview and quiet-window measurements pending |

Each archive's own index and audit define its exact claims and exclusions.
Historical source and raw CSV retain their published bytes. Historical reports
can contain redacted host paths, with original and published digests recorded
by the individual archives. Regeneration uses a new destination and the pinned
experiment baseline; it does not patch the active production tree.

The [independent audit bundle](acceptance-20261102/independent-audit.zip) retains
the complete identity report, audit script and 36 command logs for all seven
published tips. Its digest and per-command identities are in the index. Those
checks cover archive integrity, oracle/measurement summaries and preparation
boundaries. They do not claim a fresh Verus proof or a new performance run.
Each archive workflow audits and reconstructs its candidates on `main`; the
production verification workflow checks the actual production arithmetic.

Combination acceptance requires fresh same-source proof and optimized
compilation for every measured library, independent oracles, semantic mutants,
actual benchmark call-path inspection and repeated measurements. Sequential
variants and leave-one-out variants must retain their regressions as well as
their improvements. An isolated primitive speedup does not establish a
production entry-point speedup.

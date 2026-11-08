# Offline checkpoint validation

From a repository checkout, run:

```sh
python experiments/acceptance/arithmetic-negative-20261108/check_evidence.py
```

The checker reads only saved evidence and source files and prints a JSON result.
It uses no external checkout, toolchain, compiler, verifier, dynamic GMP library,
benchmark binary, network connection or process-management operation. The
original measurement commands are historical records, not checker commands.

`manifest.json` maps logical payloads in `evidence.zip` to `objects/<sha256>` and
binds the original reviewer `frozen-measurements.zip` and all 68 members. It also
links the already tracked corrected combination package at
`experiments/combination-20261108/evidence/evidence.zip`, avoiding a second copy.
The doubled-cross static ZIP is logical `double-static/evidence.zip` in the
checkpoint objects. Both retain their original complete payload manifests,
failed attempts, proof/export identities, exact sources and compiled binaries.

The checker rehashes these archives and their payloads, compares all 57 native
files and both README files with the archived production bytes, validates the
static/source/build/protocol associations and independently sealed reviews,
checks host restoration and command-log bindings, then reuses the exact Astra
reconstruction function to replay each run from the saved raw records. Its
path resolver supplies archived binary bytes solely for hashing. It never
loads or executes a binary. Every reconstructed cell, order, sample, ratio,
interaction and gate is compared with the sealed independent audit.

`summary.json` gives the accepted evidence scope and negative disposition;
`all-cell-ratios.csv` exposes every recorded median and ratio. The original
pre-timing receipts remain historical snapshots and retain their original
pending-performance wording. `RESULTS.md` and `summary.json` state the final
performance disposition.

The original static checkers remain in their respective packages for deeper
static-result replay. This checkpoint does not rerun a proof or benchmark.
Its result is evidence-integrity acceptance with performance NO-GO, not
production feature acceptance.

`python experiments/acceptance/arithmetic-negative-20261108/test_evidence.py`
additionally confirms rejection of altered native source, a public README,
the frozen measurement input, the original raw archive and the linked static
archive. These fixtures alter returned read bytes in memory; they write no
actual source or evidence file.

# Toom-4 Composition Experiment

This directory tests a fixed Toom-4 multiplication and squaring policy through the actual `arithmetic::mul_mod` and `arithmetic::square_mod` entry points. Six combinations isolate exact odd division, fused scaled subtraction, and single-pass signed evaluation.

## Purpose

The candidate uses Toom-4 from 1024 limbs and preserves current production arithmetic below that cutoff. Odd division applies only to divisors 3, 9, and 15 inside Toom-4 interpolation; shared `toom_words` remains byte-identical. Controls use current production dispatch and GMP's public `mpn_mul_n` or `mpn_sqr`, followed by low-half copy and top-bit mask.

Feature acceptance requires reproducible gains on declared workloads, same-source proof and correctness checks, independent review, and exact-commit CI. The overall GMP target is not achieved. Solver backend replacement separately requires every registered library performance gate, a second independent confirmation, semantic compatibility, and frozen representative solver traces.

## Feature Combinations

Six candidate modes extend the baseline entry policy:

- `{}` — entry threshold only, n≥1024
- `{odd}` — entry + exact odd division (3, 9, 15)
- `{odd, fusion}` — entry + odd + four fused scaled-subtraction groups
- `{odd, fusion, signed}` — entry + odd + fusion + single-pass signed evaluation
- `{odd, signed}` — entry + odd + signed evaluation
- `{fusion, signed}` — entry + fusion + signed evaluation

Recursive constants are fixed at 256/128/2 for products and 256/64/1 for squares. Contracts retain nonempty full-u64 operands, `top=1..64`, and caller-owned 12n/10n scratch. Read-only operands may alias; mutable output and scratch remain exclusive.

## Functional Domain and Verification Gates

Required checks include full Verus verification and optimized compilation, paired `.vir`/`.rlib` identities, Python integer oracles, default and forced paths, exact capacities, canaries, and semantic mutants rejected by actual VC failures. Timeouts and tool errors do not pass. Reachable assembly and the actual linked comparison are inspected; normalized text is not a machine-code proof. The full-product recurrence `T(n) ≤ 7T(ceil(n/4)+1)+O(n)` gives an analytic word-operation exponent `log₄(7)`. No checked composed bit-cost or peak-space theorem is claimed.

## Experiment Protocol

The preregistered [policy](policy.json) declares principal, boundary, and odd shapes. Selection chooses the fewest features within 2% of the fastest eligible geometric-mean elapsed time. Each shape/operation/mode has seven rotated repetitions with recorded batches ≥10ms. Allocation and input generation occur outside timing; inputs and outputs use `black_box`. Two immutable confirmation runs follow selection. Every regression is retained; result-dependent reruns and discards are prohibited.

## Usage

Run from the repository root on Linux or WSL with Verus toolchain and bootstrap installed, `VERUS_BIN` set:

```bash
python3 experiments/toom4-composition/prepare.py --output build/toom4-composition
python3 build/toom4-composition/build.py
python3 build/toom4-composition/bench_build.py exploration
python3 experiments/toom4-composition/audit_codegen.py exploration --stage build/toom4-composition
```

Measurement requires WSL with Windows host PowerShell interop for CPU coordination. During a coordinated quiet window on CPU 0:

```bash
python3 build/toom4-composition/measure.py exploration --tag exploration1 --quiet-window 'coordination-reference'
python3 build/toom4-composition/select_candidate.py
```

If selected, run the complete selected-source gate and confirmation:

```bash
python3 build/toom4-composition/accept.py --archive experiments/toom4-signed-eval
python3 build/toom4-composition/bench_build.py confirmation
python3 experiments/toom4-composition/audit_codegen.py confirmation --stage build/toom4-composition
python3 build/toom4-composition/measure.py confirmation --tag default1 --quiet-window 'coordination-reference'
python3 build/toom4-composition/measure.py confirmation --tag default2 --quiet-window 'coordination-reference'
python3 build/toom4-composition/summarize.py
```

Output directories refuse overwrites. Run these commands from the repository root.

## Hosted correctness and codegen

The [workflow](../../.github/workflows/toom4-composition-proof.yml) passed at commit a0201983b9de0f8f47d43225afcb8b8ee84c4c62 in [hosted run 41510435843](https://github.com/miles-song/VeriGMP/actions/runs/41510435843). The separate [Arithmetic run 41510435512](https://github.com/miles-song/VeriGMP/actions/runs/41510435512) also passed at that commit. The composition workflow uses a single sequential Ubuntu 24.04 job with a 180-minute timeout, commit-pinned actions, and checksum-pinned Verus 0.2026.10.26.d17fbd0 with Rust 1.99.1.

The job executes [ci.py](ci.py) which reuses prepare.py → build.py for seven library proofs and optimized .rlib/.vir compiles, the actual arithmetic default Python integer oracle, bench_build.py exploration-mode compilation of matched comparisons without invoking the binary's timing main, and audit_codegen.py for linked actual arithmetic::mul_mod and square_mod entries. An always-run artifact step collects the immutable inputs.tar.gz, preparation manifest, raw logs, artifact pairs and ci.json, including failed attempts when preparation completed. Timeout failures preserve available partial logs. Artifact hashes serve as evidence inventories, not independent authentication or formal machine-code proof.

At a0201983b9de0f8f47d43225afcb8b8ee84c4c62, the baseline library had 234 verified items and each of six variants had 306; these counts overlap. Each library passed the same 8,640 default-entry integer-oracle cases. Ordinary runners and the linked comparison were compiled against separately proved libraries; their zero verified-item counts denote compile-only harnesses. Independent review accepted the hosted proof, optimized compile, default-entry oracle, and linked-codegen evidence for later exploration timing. Forced/helper oracles, actual semantic VC mutants, and local measurements remain pending. These results establish neither machine-code equivalence nor performance acceptance.

## Current Status

Native production dispatch and thresholds remain unchanged. Local WSL process creation remains blocked. Exploration timing and both independent confirmation runs require the registered local coordinated quiet windows; no candidate has been selected or promoted. Historical archives and frozen stages are preserved.

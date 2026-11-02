# Captured-source acceptance gates

This archive records independently reviewed reruns of the full-u64 odd-division and factored Newton modules. The arithmetic source is identical to the corresponding earlier accepted modules. Production dispatch, consumer pins, and performance acceptance are unchanged.

The gate accepts a positive proof only when the process returns zero and emits exactly one complete verification summary with no errors. A negative semantic test must return one, identify the intended module, emit exactly one partial summary with verification errors, and contain an allowed proof-obligation failure. Solver `unknown`, resource limits, timeouts, loading errors, type-checking failures, compiler failures, and other fatal diagnostics cause rejection even when a normal verification-condition failure also appears.

Each checker executes its captured source bytes, captures the remaining inputs, then loads its oracle and code-generation inspector from their captured bytes. It parses captured provenance rather than a second live read. Before success, it checks the current and captured inputs, compiler dependencies, actual runner runtime libraries, command return codes and logs, and generated artifacts against their recorded identities.

## Evidence

| Module | Accepted gate | Captured inputs | Library / runner / codegen verified | Integer cases | Invalid inputs | Semantic mutants |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Odd division | `wide-odd-feature7` | 78 | 327 / 24 / 24 | 28,308 | 17 | 8 |
| Newton interpolation | `newton-feature2` | 89 | 425 / 427 / 427 | 1,087 | 10 | 8 |

For each module, the arithmetic files match the preceding accepted gate byte for byte. The only changed captured input is its `check_*.py` script. The nine appended-failure fixtures are tested against every saved semantic-mutant log by the public audit: 72 mixed-diagnostic rejections per module. The original gates, source snapshots, and reports remain in their historical archive directories.

The reports and independent reviews are in each module's `evidence/` directory. `index.json` binds original and published file hashes, the complete source reconstruction map, and the accepted report identities. Binary bodies, compiled rlib/vir bodies, and large oracle stdout logs are omitted; their recorded hashes are retained.

## Audit the saved archive

From the repository root:

```sh
python3 experiments/toom8-primitives/gate-hardening/audit.py
```

This standard-library audit checks saved hashes and proof diagnostics, rejects mixed failure fixtures, regenerates the independent integer cases and expected output hashes, and inspects the saved assembly. It does not run Verus or the omitted compiled runner.

## Reconstruct and verify

Use a new output directory for each reconstruction:

```sh
python3 experiments/toom8-primitives/gate-hardening/prepare.py \
  --feature wide-odd --output /tmp/verigmp-wide-odd-hardened
python3 experiments/toom8-primitives/gate-hardening/prepare.py \
  --feature newton --output /tmp/verigmp-newton-hardened
```

Reconstruction itself performs no fresh verification. It writes a preparation receipt with the materialized source hashes. The odd-division reconstruction preserves all 78 captured inputs exactly. Newton preserves every executable, specification, proof, oracle, and checker source exactly; two provenance JSON inputs use the previously published path-redacted form. Their original and published hashes are both explicit. Fresh Newton verification therefore creates a new metadata identity, not the original complete snapshot identity.

On Linux with the repository's pinned Verus 0.2026.10.26.d17fbd0 and Rust 1.99.1 toolchain available, set `VERUS_BIN` and the usual `CARGO_HOME`, `RUSTUP_HOME`, and `PATH`, then add `--verify` to either preparation command. The reconstructed checker runs a new full gate in the output directory. A fresh report must pass; saved reports or omitted binaries are never substituted for that run.

## Scope

Odd division retains its full positive odd-u64 divisor and carry domain. Inverse correctness and exact divisibility remain formal caller obligations; the ordinary test runner performs its own explicit checks. Newton retains its nonnegative-coefficient and mathematical-evaluation caller obligations. Its existing 72 mathematical updates execute as 144 primitive arithmetic calls. This archive does not add a complete Toom8 multiplication kernel, discharge the eventual producer's remaining interpolation premises, prove the complete scratch schedule, or provide a new timing result.

The historical `wide-odd-feature6` record is retained under `wide-odd/history/feature6/`. Its provenance-action field overstated origin parsing; the adjacent status marks it superseded. The accepted `wide-odd-feature7` actually parses the captured origin and reruns the full gate. The historical evidence is retained with explicit original and published hash mappings; it is not reclassified as final acceptance.

The public arithmetic remains MIT-licensed under the repository license and its existing third-party notices. No trusted arithmetic escape or GMP call is introduced by these checker-only changes. Verus, vstd, Z3, Rust, LLVM, and the test infrastructure remain explicit dependencies of the evidence.
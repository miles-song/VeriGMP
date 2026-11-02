# Low modular product and dedicated low square

This experiment proves low-product and dedicated low-square composition over the accepted recursive full Toom8 kernels. The outputs contain exactly the requested low limbs and precision mask. Production dispatch, performance measurement, and GMP-parity acceptance remain separate.

## Contracts and implementation

The [low-product module](candidate/native/verified/toom8_low.rs) and [low-square module](candidate/native/verified/toom8_square_low.rs) accept positive-length inputs of arbitrary `u64` limbs with no normalized-input requirement. Product inputs have equal lengths. Outputs contain `n` limbs; modular entries accept `1 <= top <= 64` and return `a*b` or `a*a` modulo `2^(64*(n-1)+top)`.

The full-kernel threshold is at least 56, the low-product limit at least 24, and all existing split modes 0, 1, and 2 remain available. The selected split has lower block `k` and upper block `h=n-k`. The exact quotient-first formulas avoid overflowing intermediate products when computing the non-half splits.

Low multiplication uses caller scratch of at least `12*n` limbs. It reuses a `2*k` full-product buffer and `12*k` recursive work, then a truncated cross-product buffer of `h` limbs and `12*h` work. The two cross terms are evaluated sequentially.

Low square uses caller scratch of at least `10*n` limbs. It first uses `2*k` full-square output plus `10*k` recursive square work, then one `h`-limb truncated cross product with `12*h` work. That single cross product is added twice. The existing symmetric low-square leaf from 9 limbs through the low limit is retained.

Actual slice capacity, aliasing restrictions, preserved lengths, and output meanings are proved in the implementation. Analytic work is bounded by `full(k)+2*low(h)+O(n)` for multiplication and `full_square(k)+low_product(h)+O(n)` for square. These expressions are not checked machine-cost instrumentation.

## Evidence

The frozen [gate](evidence/verification.json) binds 144 source inputs, 21 tools, three actual runner runtime libraries including the loader, four compiled artifacts, and 39 completed commands. Full library, runner, and code-generation builds each verified 556 items with zero errors.

The independent integer oracle checks 2,700 modular outputs, split equally between product and square, including 900 shared immutable-input cases. It covers top values 1, 2, 31, 63, and 64; split modes 0, 1, and 2; full thresholds 56, 96, and 192; low limits 24, 64, and 128; and lengths up to 4,096 limbs. All 16 malformed structural inputs exited with code 101.

Fourteen actual semantic mutants produced strict verification-condition failures; all 126 appended fatal-diagnostic combinations were rejected. The checker permits the selected module's own qualified spinoff-prover notes while rejecting another module or duplicate main-module notes. The [independent classifier audit](evidence/module-notes-independent.json) checks 56 wrong-module or duplicate-note negatives and 14 valid qualified-note fixtures.

The [independent arithmetic audit](evidence/root-independent-audit.json) rechecks identities, independently reconstructs integer outputs, and replays the saved runner and malformed commands. Six actual code-generation roots passed allocator, general-division, and element-bounds-panic reachability inspection.

[Development evidence](development/index.json) retains the three-item low-product proof and four-item low-square proof. [Publication mappings](publication.json) preserve exact source bytes and identify host-path redaction. Compiled binaries and the large oracle-output body are omitted, while their identities remain recorded.

These proofs establish the modular APIs over the complete stated parameter domain. They do not select a production policy, measure speed, establish GMP parity, or prove a complete bit-cost model. No default or consumer pin is changed.

## Reproduce

From the repository root:

```sh
python3 experiments/toom8-primitives/low/audit.py
python3 experiments/toom8-primitives/low/test_prepare_boundaries.py
python3 experiments/toom8-primitives/low/prepare.py --output /tmp/verigmp-low
```

The audit checks saved identities, strict diagnostics, independent integers, and generated-code reachability. Preparation reconstructs all 144 source inputs exactly and rejects existing or escaping output paths.

For a fresh Linux proof and oracle run, use the pinned Verus toolchain, set `VERUS_BIN`, and add `--verify` to the preparation command. The saved-evidence audit and reconstruction do not claim that the complete fresh-reproduction command has already run.

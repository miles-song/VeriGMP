# Fifteen-coefficient recomposition

This experimental feature proves that actual shifted additions reconstruct a full product from fifteen input-defined coefficient buffers. It is archived on the experiment branch; the production arithmetic and consumer pins are unchanged. This feature contains no performance measurement or GMP-parity claim.

## Contracts and implementation

The independent [mathematical model](candidate/native/specs/toom8_recomposition.rs) establishes arbitrary-radix input decomposition, the convolution identity and the strict product capacity bound. It defines the answer from the original input blocks, independently of executable outputs.

The actual [Rust implementation](candidate/native/verified/toom8_recomposition.rs) provides two interfaces. `assemble` clears the output and adds fifteen coefficients at offsets `0*k` through `14*k`, computing their weighted sum modulo the output radix. `assemble_exact` uses the input-defined coefficient premises and the strict capacity bound to establish the exact product of the original equal-length inputs. For the exact interface, `7*k <= n <= 8*k` and the output contains `2*n` limbs. The full-u64 domain includes `k=0` and an empty high block.

All fifteen coefficient meanings are formal caller obligations. The ordinary runner checks structural shapes; it does not establish these numeric premises at runtime. The independent integer oracle supplies true coefficients. The actual interpolation-to-recomposition caller and recursive dispatch are separate later features.

Recomposition uses caller-owned output and coefficient slices with no additional scratch. Fifteen shifted additions give linear work at fixed arity; this is an analytic cost statement, not a checked machine-cost theorem.

## Evidence and boundaries

The frozen [gate report](evidence/verification.json) records 119 captured inputs, 21 tool identities, three actual runner runtime libraries including the loader, four compiled artifacts and 33 completed commands. Library, runner and code-generation builds each verified 522 items with zero errors. The 464 independent integer cases comprise 336 general cases and 128 monomial cases; boundary coverage includes empty blocks, trimmed or padded coefficients and untouched output sentinels. All 12 invalid harness inputs exited with code 101.

Twelve semantic mutants produced genuine verification-condition failures. Appending each of nine resource, loading, typing or internal-failure diagnostics to every saved failure was rejected, giving 108 mixed-diagnostic checks. The captured checker, oracle, code-generation inspector and origin data are the bytes actually executed. The [independent review](evidence/root-independent-audit.json) separately checked 6,960 coefficient buffers, reconstructed all integer outputs and replayed the saved runner.

The single reachable code-generation entry was inspected for allocation, general-division and element-bounds-panic paths. This is textual assembly inspection, not a performance result. The archive omits compiled binaries and the large oracle-output body; their identities remain in the reports. [Publication mappings](publication.json) bind original and public bytes, including explicit host-path redaction of evidence.

[Development evidence](development/index.json) retains all three attempts: an initial nat/int type error, a corrected six-item mathematical specification and a passing two-item actual recomposition proof. Earlier failed evidence is not accepted as verification.

## Reproduce

Run from the repository root:

```sh
python3 experiments/toom8-primitives/recomposition/audit.py
python3 experiments/toom8-primitives/recomposition/test_prepare_boundaries.py
python3 experiments/toom8-primitives/recomposition/prepare.py --output /tmp/verigmp-recomposition
```

The audit checks saved identities, strict diagnostics, independent integer results and generated-code reachability. Preparation reconstructs all 119 source inputs exactly and refuses to overwrite an existing output directory.

For a fresh Linux proof and oracle run, use the repository's pinned Verus toolchain, set `VERUS_BIN` to its executable and add `--verify` to the preparation command. This archive's preparation checks do not claim that this fresh-reproduction command has already been executed.
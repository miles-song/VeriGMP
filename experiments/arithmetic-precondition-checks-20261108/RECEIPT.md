# Checked full-product recursion: semantic/static prereview receipt

Status: **functional/static candidate; performance and independent acceptance
pending**. No benchmark binary has been executed, including calibration. The
candidate is ready for independent Astra Max source, proof-evidence and protocol
prereview. It is not ready for promotion or a speed claim.

The branch is `codex/arithmetic-precondition-checks-20261108`, based on committed
main `de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9`. Native source was fixed at
`b31fbce898054f6db668277f8a4da88f94c95aa2`; the passing focused gate is source
`162fdef515793ab72210102c8733c21f0110a23d`. Subsequent documentation and receipt
changes do not change native Rust, the oracle, controls or benchmark sources.
Every new commit uses miles-song <2324715854@qq.com> as author and committer.
There has been no merge or push.

Only `native/verified/fast_multiply.rs` changes in the arithmetic core. Existing
little-endian `value` and the independent Karatsuba identities define the exact
product. The public `full` signature, requires, ensures, entry assertions and
pre-write panic behavior remain. Small products still call unchanged
`base_full` directly. A private worker performs the original three recursive
products with the same exact-product contract, positive/equal input lengths,
2n output, at least 3n scratch, threshold >=8 and strict recursive decrease.
Ghost facts establish every callee precondition. Rust slice checks remain;
there is no unsafe operation, axiom, FFI, unchecked-unreachable, runtime spec
materialization, new allocation or additional data scan in the core. Default
policy and the other kernel families are unchanged at source level.

## Fixed proof and exact execution evidence

The complete modified native crate was verified and compiled with pinned Verus
`0.2026.10.26.d17fbd0`, Rust `1.99.1`, `--no-cheating --compile -O` on x86_64
Linux/WSL: **359 verified items, zero errors**, exit 0. This is a fresh proof of
the changed crate. The old baseline producer is reused only after every native
Rust source hash matches committed base, its exact rlib/vir match the accepted
receipt and its Verus/rust_verify/Z3/vstd identities match the current pin. The
baseline's 358-item proof was not replayed. `semantic-3/build-command.json`
preserves the full command, environment, exit status and output identities.

The focused gate checks 1,898 deterministic Python arbitrary-integer fixtures
against the actual optimized baseline, candidate and ordinary-control builds;
GMP independently checks every expected full or truncated result. Coverage
includes n=1..34 and registered near-boundary sizes through 4,096 limbs,
thresholds 8/24/64/usize::MAX, odd/even sizes, all difference-sign pairs,
maximum/carry/zero/equal-half/random values, top-bit boundaries, actual Toom and
default modular callers, shared immutable input aliases, exact and oversized
scratch, poisoned initial storage, preserved inputs and both-end canaries.
Each build passes seven invalid public-entry panic/preservation cases and six
workspace metadata boundaries. Rust rejects overlapping output/input borrows
with E0502 and private-worker access with E0603.

Three targeted mutants receive strict complete logical VC rejections: wrong
public-to-private forwarding, insufficient private scratch assumptions, and an
incorrect child partition. Tool, parse, type, load and timeout failures do not
count as semantic rejection. The report binds the classifier/helper sources as
well as all native, control, oracle, ABI fixture and measurement sources.

## Complete optimized code

The full before/after release objects contain 156 and 157 function sections.
Complete raw bodies, sizes, relocations and disassembly are retained. Among the
156 common functions, 154 keep identical raw body bytes and normalized
relocations. Only `fast_multiply::full` and its unchanged-source Toom caller
change; `full_inner` is the sole added function. Anonymous data labels and local
section names are normalized for relocation comparison; original targets remain
in the raw reports.

| Function | Baseline bytes | Candidate bytes |
| --- | ---: | ---: |
| Public `fast_multiply::full` | 901 | 160 |
| Private `full_inner` | absent | 837 |
| `fast_multiply::base_full` | 457 | 457 |
| `fast_multiply::low` | 1,297 | 1,297 |
| `toom_multiply::full` | 2,640 | 2,672 |
| `square::full` | 795 | 795 |

The public entry's complete bytes and normalized relocations match the plain
Rust control. The actual worker inlines cross accumulation; the external plain
control calls that helper, giving an 837-byte versus 602-byte worker. No
whole-worker byte-identity claim follows. Full symbols show no allocator,
per-element bounds panic or spec/Seq materialization. The recursive-sized
public entry adds a worker call/frame, and the Toom caller inlines the leaf
choice and calls the worker or basecase. Combined code size grows. These costs
may offset removed entry checks and require the registered measurements.

## Performance protocol and limits

[PROTOCOL.md](PROTOCOL.md) was fixed before any timing. It registers 34 forced
full-product sizes at threshold 24 plus the exact 26 default mul and 26 default
square shapes from `native/performance-target.json`: 86 cells. Both builds use
the same harness, release flags, deterministic input seed and preallocated
buffers. Seven accepted batches of at least 10ms per path/cell, rotated order,
raw calibration/retry rows, exact results checked outside timing and a second
independent run with identical binary hashes are required. GMP computes the
same full result or full result followed by low-half copy and precision mask.

Prospective promotion requires recursive forced-full geometric mean <=0.97 of
baseline and every registered cell median <=1.05 of baseline in **each** run,
plus independent final review. All regressions are retained. Failure leaves an
experiment/no-go. No threshold or dispatch tuning is authorized here. Timing
waits for independent prereview and root's coordinated quiet-window grant.

The arithmetic recurrence, copied words, thresholds and 3n scratch layout are
unchanged analytically. The caller's minimal full-product buffers total 7n
words (two n-word inputs, 2n output and 3n scratch), plus any caller excess and
the recursive stack; this is not a peak-live-space theorem. No composed bit-cost,
GMP parity, solver speedup, tensor creation-provenance or SAT theorem is proved.
SAT callers retain their own precision/provenance and integration obligations.

## Bound artifacts

External evidence root:
`E:/3sat/VeriGMP-precondition-evidence-20261108`.
The raw archive retains the original reports and failed fixture/startup attempts;
historical receipts are not overwritten.

| Artifact under evidence root unless otherwise stated | SHA-256 |
| --- | --- |
| `check-4/verification.json` | `96b7898dd215679cf9284d4ff70c5d6804c86e650722c8faee417efd91388df7` |
| `complete-codegen/comparison.json` | `edce72f02206f6dbb552c4094ec4d371bbaac4ffc997d22140bb8f5a33ba0488` |
| `semantic-3/libverigmp.rlib` | `1ce7a925da627ea99859935ec42ac88b5b3e67933bcf8a8e0c55b8827d685775` |
| `semantic-3/verigmp.vir` | `6054b60c6adad786bb95550364c61ffc725ac7abf965ddbe61f6d7f406749305` |
| `check-4/oracle/cases.bin` | `71bfa0a736414703ce52bd179f0bd2c4f044c50d52d5463c2ce16860d97ffcdf` |
| Native changed `fast_multiply.rs` | `7e8e225dd5edf54f384f3ea4d42aea03d59e3ab04d0050f3f04415b388219db8` |
| This experiment's `PROTOCOL.md` | `3c176e1b665aeae085c52094a68f6a6bfed5f1d77ed99deaa0ae55dc3d6e8d3e` |
| `bench-build/bench-build.json` | `fd8f8e808c15a4be076aaeca94c74aa9a385914d7581e600361a5742178b2af2` |
| `bench-build/baseline-bench` | `4d5c36af924d8c29df716e3b11b7ba1880404e5be27a6341c59ca3137b914fde` |
| `bench-build/candidate-bench` | `f4168e29275ff754acb5b65882ddfcaa15b3de5ed9d6bba405d7a9f9219babdd` |
| `ordinary-tools.json` | `ba862d912b382ee8b38559100ed17ed516525966aef3f0c8141e5009ba2401d0` |
| `prereview-manifest.json` | `5e2dc609a8bb70b563ae17eefafc710269fd5702f892d00325591b95f2293582` |
| `prereview-raw.zip` (30,047,009 bytes) | `260618cdf080c21067fcdfb788cb360d857c4f4c8766268ed6de84ab370cd8cd` |

The pin archive SHA-256 is
`361674d05f0c1b2c9c3f4d5bc56a8fb2ab9241ed0cceca27780668c292bb4940`.
The report records the actual Verus, rust_verify, Z3, vstd, builtin/macro,
Rust/LLVM identities; `ordinary-tools.json` binds Python, C++, ar, objdump,
objcopy and environment tools, and the benchmark build binds its loaded GMP.
Verus/vstd/Z3/Rust/LLVM and ordinary execution tools remain trusted dependencies;
benchmark GMP FFI remains outside the verified core.

Reproduce the focused gate with the pinned runtime and a fresh external output:

```sh
python3 experiments/arithmetic-precondition-checks-20261108/check.py \
  --deps-root /mnt/e/3sat/VeriCount/deps \
  --producer /mnt/e/3sat/VeriGMP-precondition-evidence-20261108/semantic-3 \
  --baseline /mnt/e/3sat/VeriGMP-precondition-evidence-20261108/baseline-binding \
  --output /mnt/e/3sat/VeriGMP-precondition-evidence-20261108/fresh-check
```

The archive contains `complete-codegen/reproduce.py` for a fresh complete-object
comparison. Public README variants, verification documentation and proof status
agree on this narrow functional/static claim and pending performance acceptance.

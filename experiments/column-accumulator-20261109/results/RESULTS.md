# Split-sum column prototype: broad NO-GO

The registered broad column prototype failed its investment screen. All 224
calls completed, but the geometric mean of the eight cell median
candidate/baseline ratios was **1.1295737902573288**, above the fixed **0.90**
limit, and the worst cell was **1.5521974801634209**, above **1.03**.
The completed independent review approves this negative-result archive and
does not justify refinement or production promotion of the registered scope.
There is no candidate Verus proof, production acceptance, default-dispatch
performance or GMP-parity claim.

| Forced general-multiplication leaf | Random ratio | All-max ratio |
| --- | ---: | ---: |
| Full, 15 limbs | 1.5521974802 | 1.5099131073 |
| Full, 20 limbs | 1.3672423522 | 1.3511981167 |
| Low, 46 limbs | 1.0511322592 | 0.9615379419 |
| Low, 115 limbs | 0.7898951721 | 0.7667612222 |

The low-115 observed medians are about 21% and 23% smaller. They remain a
**prospective scoped hypothesis only**. In the all-max low-115 cell, the row and
column batch max/min ratios were 2.0788 and 2.1662. These selected cells do not
overturn the broad NO-GO, establish accepted gains, or authorize fitting a new
dispatch to this session. A narrower hypothesis needs its own prospectively
fixed source, scope, controls and independent confirmation.

The experiment tests a bounded product-scanning leaf. For B=2^64, each word
product is split into low and high halves; two scalar lanes accumulate each
half, and carry is normalized once per output column. Arbitrary u64 limbs and
positive operand lengths at most 128 are supported, with requested output width
1..=len(a)+len(b). The intended result is `(A*C) mod B^q`. Those identities and
overflow bounds were reviewed mathematically; no machine-checked refinement
was performed for the prototype. The original [design](../DESIGN.md) and source
are retained, including their historical pending/design-only wording.

## Exact scope and bindings

The measured prototype commit is `8df6f173040f8cc9a0957420be9dfb832fe26807`.
Its production native tree remains
`72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`. The design-time main was
`7219cbd013dbf323f7121e4a9e197964f55377ca`; the existing comparator library was
proved and compiled at `2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba`, with this same
native tree. The retained baseline receipt records 358 items and 0 errors. It is
historical source-bound comparator evidence, not a formal build of this column
candidate. No native file, threshold or production dispatch is changed.

The direct row controls call the existing `fast_multiply::base_full` and
`base_low` through that paired library. Both sides use identical input bytes,
output widths, counts and preallocated caller buffers. Allocation, input I/O,
expected-result construction, warmup and equality checks are outside the timed
loop. These forced leaves do not measure the production recursive dispatch.

The screen uses eight cells, seven alternating ABBA/BAAB blocks per cell,
four calls per block and 14 batches per side per cell. A is row and B is column.
There were no calibration or retry records. All 224 batches exceed 10 ms;
the minimum is 39.810920 ms. All raw calls, including unfavorable or variable
samples, are retained. [cell-ratios.csv](cell-ratios.csv) and
[summary.json](summary.json) expose the complete result without rerunning code.

Build03 is **`compiled_unverified_prototype`**, using Rust 1.99.1/LLVM 23.1.1,
`--edition=2021 -O`, plus a second `overflow-checks=yes` build. Each retained
oracle receipt records 12,118 Python-integer cases and 5 invalid-input controls;
the driver checks sentinel words and immutable input frames. The 16-operation
screen-input preflight checks both leaves against independent integer products.
The archive preserves existing outcomes and does not replay those oracles.

| Identity | SHA-256 |
| --- | --- |
| `column.rs` | `4ce0b055e728199d3bf368fff8c44aa4227301c96487ea2f61a954c7bfbda0f1` |
| `runner.rs` | `0f497839888f83e5d5322b4d5658eaaf26af5d98b498726ed3fe0fb2b2380a30` |
| `oracle.py` | `39ffceba80ca942711e89d6bec46f02a644de3d80182bab3d5391232b57185b9` |
| Release prototype binary, omitted | `14d5a1426a0dc4b90e5da409e43c065bdecdbebe1fa551d35b6a42f7bda790a8` |
| Overflow-checked binary, omitted | `969f9e4410fc0a4009bac7904cd5b9f525c1ef11a76d98c2e17fa59b515cadb2` |
| Rust compiler, omitted | `b53b780f77f952062f8ca8a3b70aef2390b1e45ad91939be94afdc9543026853` |
| Comparator rlib, omitted | `174a7e55056b622cee5a9974d353532867ceea809ec6cd11ac43a39136acb36f` |
| Comparator VIR, omitted | `99dacd6bb1535d651339c859d9853558499e4555a65104a0ec79987f51c055d6` |
| Original build03 receipt | `3b7f7dc1d8a5427736b51f26c67be1cd9f92510f9b086ad7aa8ea5baa42c681e` |
| Original 224-call raw stream | `ceac6422d75b23a22fd765235596aa6ae818eb936ea3320d39c142bb316d7ed3` |
| Completed independent review | `0b878327f700c74f03d7a79349d0bdb040bb15158e5689da0cb13a1cffd8c3b1` |

## Environment and review limits

The saved host is an AMD Ryzen 7 7745HX. CPU 8 affinity, an owned 120-second
coreutils timeout with 1-second kill escalation, and the root's emulator
pause/finally-resume procedure are recorded. The completed screen took 19.309 s;
the recorded host window was 31.241 s. Both screen exit and resume status are 0.
All 23 named postflight checks passed; the later emulator receipt records it
alive with CPU time increasing by 421.875 ms. The watchdog readiness and root stop
records are retained; the fallback did not fire in this run.

These records do not establish stable clocks, an exclusive host, continuous
absence of interference, default-dispatch gains or repeated-run acceptance.
No new environment rejection rule was fitted after the result. The completed
review reports its exposed runtime identity as Codex GPT-6 and explicitly does
not attest an Astra Max runtime. That limit is retained in its original bytes.

## Portable public archive

[evidence.zip](evidence.zip) contains 66 text/source entries: frozen prototype
source/design, MIT license and original prototype-first policy; build03 receipt and assembly;
both oracle03 receipts; exact oracle inputs/stdout/stderr; all eight screen
inputs, plan, preflight,224 raw calls, report,23-check postflight and host records;
the original build/screen/preflight/postflight/controllers; baseline source/tool/
pair receipts; pre-screen and completed independent reviews. The two oracle03
data streams are byte-identical and stored once as `oracle-common/`.

[manifest.json](manifest.json) maps all 69 original-file bindings to portable
entry names and exact hashes. It also binds the zip, summary and ratio table.
Archive SHA-256:
`3a7d87be42435ab186162af853c415048fbb178436ea31f5eb8d686d32289cc6`.
No executable, rlib/VIR, tool binary or private application code is published.
Earlier build01/build02 and oracle01 attempts remain externally retained; this
archive does not relabel them or replace their original records.

The original operational scripts retain captured machine paths for provenance.
They are evidence and are not invoked by the portable checker. From any clone,
run only the following read-only archive/data check:

```sh
python3 experiments/column-accumulator-20261109/results/check_evidence.py
```

It checks all zip entries and original-file mappings, saved identities and
oracle artifact hashes, exact 224-call schedule and durations, ratios and NO-GO
decision. It does not execute the prototype, a compiler, proof, oracle,
benchmark, emulator or process controller. Omitted binaries and tool files are
bound by the retained original receipts and review; this checker does not
independently reconstruct or reverify those omitted artifacts.

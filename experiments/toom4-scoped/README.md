# Scoped Toom-4 candidate

This is a development candidate on top of
`2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba`. Production arithmetic dispatch is
unchanged. Before line-ending normalization, one complete library verification
and optimized compilation passed for native manifest SHA-256
`da70abe92aeda7e5566cb2111862aac125029514bdaa61cd7bd61aa6e150fc99`
(Verus 0.2026.10.26.d17fbd0, 400 verified, 0 errors). That evidence is tied
to that earlier native file manifest, not to this commit. The complete local
oracle, mutation, code-generation, performance and independent-review gates
remain necessary. Results from earlier archives are historical only.

The eight algorithm and specification modules are restored from
`experiments/toom4-entry/overlay/candidate/native`. `native/lib.rs` registers
them alongside the existing packed modules. `native/verified/toom_words.rs`
contains the archive's proof-only stabilization; the runtime statements and
the current production leaf algorithms are unchanged. The experimental
`toom4_candidate` entry uses the existing path below 2048 product limbs and
1024 square limbs, with Toom-4 at and above those thresholds. These are
starting points for measurement, not accepted dispatch regions.

The relevant GMP reference is release 6.3.0, archive SHA-256
`a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898`.
The Toom-4 source hashes are recorded in
`experiments/toom4/gmp-toom4-reference.json` (Git blob
`163863663616e7a8cba46bd3462562a8276d55ba`); `native/gmp-reference.json`
records the common release and archive reference. GMP's `toom44_mul.c`, `toom4_sqr.c`, and
`toom_interpolate_7pts.c` carry Free Software Foundation copyright notices and
offer LGPL version 3 or later, or GPL version 2 or later. The restored Rust
algorithm and proofs were independently implemented as described in the
historical archive; no GMP implementation is linked into the verified core.

`prove.py` snapshots the current native tree and runs a complete library
verification and optimized compilation. It records source and pinned tool
identities and does not run a benchmark. A passing result is only the full
library gate; it is not a substitute for the other acceptance gates.

`freeze_gate.py` runs the oracle, mutation or code-generation gate on frozen
copies of their local sources with before-and-after hashes and retained raw
observations. The oracle verifies callers of both the candidate entry and the
direct Toom-4 kernels. Direct product requires positive, equal input lengths,
an output of the same length, at least `12*n` scratch limbs and `top` in
`1..=64`. Direct square requires the same output length, at least `10*n`
scratch limbs and the same `top` range; it normalizes the result afterward.
This forced mode is experimental and does not alter production dispatch.

`prepare_measurement.py` builds the measurement binary, verifies its linked
library identity and runs only non-timing functional checks. The predeclared
`measurement-protocol.json` compares current default, candidate, forced kernel
and GMP, with paired batches, raw samples and stop rules. `measure_window.py`
requires an explicitly scheduled quiet window before its `run` command and
retains source/tool identities and guest CPU monitoring. No measurement has
been made by preparing the harness. Any proposed production dispatch requires
fresh gates on that final source and independent review.

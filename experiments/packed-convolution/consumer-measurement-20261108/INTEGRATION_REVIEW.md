# Independent Integration Review

**Decision: ACCEPT for main merge as an opt-in refined `packed_layout` API and
retained local measurement evidence. No unresolved blocker remains in this
declared scope.** This acceptance does not enable a default polynomial strategy
or establish formal product composition, a complete bit/peak-space theorem,
solver speedup, GMP parity, or backend replacement.

The reviewed main baseline is
`8da9dc207d8cae7c0b64aa0d370d1fa7ca2585aa`. The accepted candidate is
`a8b33701c6b110d9031724eb7171a6900aa940e4`, tree
`60ee148586d171373c60744578182025dabfc172`, on
`codex/packed-consumer-measurement-20261108`. All 43 commits in that feature
range have author and committer `miles-song <2324715854@qq.com>` and no
coauthor trailer. This review adds a record only; it does not merge or push.

The new API's integer meanings are independent of executable outputs.
`checked_layout` validates positive precision, sufficient aligned slot width,
and both checked length products. Packing and extraction validate exact source
and destination lengths before writes. Their classified errors preserve the
destination, and successful results preserve each represented coefficient.
Canonical p-bit chunks/slots are explicit caller preconditions; the runtime
does not scan or normalize values. Safe shared/mutable slice borrowing excludes
overlap. The loops terminate, keep checked bounds, reuse the existing
`copy_pad`/`copy_words` helpers, allocate no heap storage, and do not materialize
the mathematical Seq specifications.

All 49 native Rust files at the accepted candidate are byte-identical to
measured commit `d82d63147cfd45939a6a34765872295dca83a3fa`.
`packed_layout.rs` SHA-256 is
`fb8073712aa5681ef6f4f9dbb3aff85884955539d809e2e0131bc1b84d2626c8`.
Against main, the runtime addition is the new module and its library export;
the default arithmetic dispatcher, precision helpers, copy helpers, and exact
product implementation are unchanged. All 13 registered product call-graph
blobs also match main. The feature introduces no proof escape, unsafe code,
FFI, or new dependency.

The source-bound library gate and its optimized compile are retained. The
earlier independent replay at package commit
`84887ab1a94b258cc3f5f25fdd7a6044f7a910b2` passed 350 Verus items, 208 valid
runtime cases, 18 error-preservation cases, the E0502 overlap fixture, and three
logical semantic-mutation rejections. This integration review rechecked the
source identity, gate log hashes and strict rejection classification, rather
than repeating an unchanged full proof/timing batch. Six experiment Python
files parse, the mutation classifier and anchors pass, and all 48 current
documentation/status references resolve. The final diff whitespace check passes.

The complete-symbol code audit independently checks five retained libraries
with `ar`, `nm`, `objdump`, and `objcopy`, including the measured library and
the independent replay. Packing has 140 instructions and 487 bytes, SHA-256
`84df6810c854bd5dd0fe25d5a7d38abed7d18ab11176932ef2135216672953f6`;
extraction has 101 instructions and 324 bytes, SHA-256
`45155a3921293655560a5c6a32a36c461ca92731112f696aea64492c9e26104c`.
Complete relocatable-object symbol bytes agree across the builds before/after
the ghost-counter extension. [The additive audit](evidence/codegen-body-audit.json)
has SHA-256
`589f49aaa24320190580f766bd6a5e7fe6eacac40f09309d757f56f81411d0ac`.
The earlier 469/318 byte counts and associated hashes are not accepted as
complete-body evidence; current documentation/status now use the independently
checked complete bodies. Historical records remain unchanged. Local ghost word
totals and inspected helper loops are not a composed runtime bit-cost or
peak-live-space theorem.

Both retained release timing runs have 588 samples, identical inputs/results
and binary hashes, and the previously reviewed allocation/cache boundaries.
The aggregator independently reproduces `confirmation.csv` byte-for-byte and
the confirmation metadata semantically. All original receipt hashes still
match. The direct schoolbook path is a benchmark-only exact u128 control;
Python arbitrary integers check every coefficient of the first pair per shape,
while all 32 input pairs receive three-path agreement checks. The empty case is
excluded from the nonempty ranges, and the guard-boundary and guard-width
regressions are reported. The scoped measurements support workload-dependent
observations, not a production crossover policy or universal speed claim.

Under the repository's incremental acceptance contract, these API semantics,
local refinement/oracle/boundary/mutation gates, optimized erasure evidence,
and explicit measurement limits support this opt-in feature merge. The separate
dense dispatcher study is outside this accepted snapshot and is not a premise
of acceptance. No dispatcher is enabled; choosing one remains a separate
performance acceptance. Formal product composition and bit/peak-space bounds
remain openly pending in `native/proof-status.json`.

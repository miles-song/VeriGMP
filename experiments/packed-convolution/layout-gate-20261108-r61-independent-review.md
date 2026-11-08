# Independent Review: Packed Layout

**Verdict:** ACCEPT for the narrow borrowed-slice `pack_coefficients` and
`extract_coefficients` functional-refinement claim at source commit
`a94e71a1945352b35e9df882612381d50dbf1fbf`. This does not accept a speedup,
product composition, production dispatch, or a complete cost/space theorem.

The pinned WSL report at `layout-gate-20261108-r61/verification.json` has
SHA-256 `08f3e7a5c76caf3ab0fb161509a63c242023fadacfbc7fa78ce05b7943b4d6c7`;
the codegen comparison has SHA-256
`8717c0eb2bf819ca5bae6dba47293e0dc53d7b632469904055133cd2aab6c0cb`; and
`native/verified/packed_layout.rs` has SHA-256
`fb8073712aa5681ef6f4f9dbb3aff85884955539d809e2e0131bc1b84d2626c8`.
All 59 source hashes listed by the report match this checkout. The verifier,
rustup, six recorded command log pairs, three mutant sources, and borrow-checker
diagnostic also match their recorded hashes. The report records a 350-item
Verus library build, 208 valid and 18 error-preservation runtime-oracle cases,
three logical semantic-mutation rejections, and Rust E0502 for overlapping
borrows.

The contracts make canonical p-bit compact inputs and packed slots explicit
caller preconditions; the runtime deliberately does not scan values. Checked
metadata and exact slice lengths precede writes, returned errors preserve the
destination, and successful results preserve the represented coefficient
values. Safe Rust borrowing prevents input/output overlap. The optimized codegen
comparison shows byte-identical API bodies with and without the ghost counters;
this is erasure evidence, not a timing result.

No timing benchmark or product-composition evidence is present. The counters
establish the stated per-slot word totals, while their relationship to the
called helper loops is supported by source inspection; they do not establish a
complete machine-operation or bit-cost theorem. There is no formal peak-live
space theorem. Therefore performance/high-performance acceptance and product
integration remain blocked on relevant benchmarks and composed cost/space
evidence. This audit inspected the hash-bound WSL artifacts and source but did
not rerun the gate; it is not a substitute for any separately required Astra
Max review.

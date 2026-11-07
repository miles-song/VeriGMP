# Accepted packed-convolution model

This immutable package records the model-only acceptance of source commit
`1dc2781e29ba56a44bd81257342f9d17d76a9513`, tree
`28ce6f963094461b498061e90416963af2b25438`.

[receipt.json](receipt.json) binds every source input and archive member.
[acceptance08.zip](acceptance08.zip) preserves the complete fresh WSL gate:
73 model items, 16 oracle-fixture items, two imported-client items, 10,134
integer-oracle rows, 15 signed cases and four logical mutant rejections.
[astra-review.zip](astra-review.zip) preserves the independent sealed ACCEPT
with hash audits, independently recomputed integer checks and ELF inspection.
The independent audit inspected the fresh proof logs; it did not rerun Verus.

This package adds no arithmetic runtime. Executable packing/extraction, runtime
refinement, bit cost, peak space, benchmarks, performance and GMP parity remain
open as specified in [the module documentation](../../../docs/packed-convolution.md).
The model specifications and proof calls erase from optimized client code.

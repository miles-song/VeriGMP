# Static evidence package

`evidence.zip`, `manifest.json` and `package.json` bind the four reconstructed
native sources, historical producer identity receipts, the fresh combined
proof/export, complete untimed correctness and code-generation gate, all raw
command logs, operation-count schedule, host/tool metadata, and four frozen
benchmark binaries. They contain no benchmark timing or calibration.

Run `python3 experiments/combination-20261108/check_package.py` from a checkout
to verify archive entries, exact four-cell source identities, producer export
hashes, the 366-item combined proof, 86 operation cells and frozen binaries.
The offline checker invokes no verifier and executes no benchmark.

`metadata/bench-build.json` is the effective frozen metadata receipt for the
same four benchmark binaries. The original build and all producer/static
receipts remain intact. The package includes the previous input snapshots,
operation receipt and package identities, exact scalar-pair fixtures, and
metadata reuse/tamper controls. The checker recomputes all 86 operation rows
and verifies the retained-square loop schedule at every length 1 through 129.

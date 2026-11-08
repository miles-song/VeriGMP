# Fixed factorial arithmetic experiment

This is a new exploratory four-cell experiment. The previously reviewed
checked-recursion result remains **NO-GO**. No production arithmetic is changed
on this branch, no threshold is tuned, and neither a combined improvement nor
GMP parity is claimed before the frozen measurements complete.

The two factors are the low-square fused doubled-cross correction and the
same-contract private Karatsuba recursion worker. The experiment reconstructs
all four complete native trees from immutable Git objects, rather than consuming
another worktree's current files. See [PROTOCOL.md](PROTOCOL.md) for the fixed
matrix, measurement cells, decision gates, costs and transfer limits.

Run `prepare.py` into a fresh directory outside the repository, then `prove.py`
for the combined cell. `check.py` reuses unchanged historical producer proofs
only after matching every native Rust byte, export and tool identity; it runs
untimed Python/GMP oracle and boundary checks, targeted semantic mutants,
complete-object comparisons, operation-count checks and measurement-driver
fixtures, and builds all four frozen benchmark binaries. `measure.py` must wait
for independent prereview and the main agent's coordinated quiet window.

All scripts retain raw command output and failed attempts. Source-level visit
counts, functional proofs, complete code generation and measured time are
different evidence. No new imported-client/SAT proof, solver trace, complete
bit-cost theorem or peak-live-space theorem follows from this experiment.

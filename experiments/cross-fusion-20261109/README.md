# Karatsuba cross reconstruction experiment

The arithmetic candidate starts from public baseline
`2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba`. The original implementation is
available at that commit. The production change was fixed in candidate commit
`e0435541f9a518b5d2d829c6ab01d0c69f30ad2d`; this directory adds independent
checks and a reproducible evidence collector. The current commit is the
source identity for a fresh collection, including the complete test harness.

For radix `B = 2^64`, addition accumulates
`z0[i] + z2[i] + d[i] + carry`, with initial carry 0. Subtraction accumulates
`z0[i] + z2[i] + (B - 1 - d[i]) + carry`, with initial carry 1, and returns
the final carry minus 1 as the high word. Missing `z2` words are zero. The
existing boolean means addition when `negative` is true. The largest
intermediate is `3B - 1`, so carry 2 is necessary. The original contract
bounds the final value to `[0, 2B^n)`, hence its high word is 0 or 1 and the
final subtraction carry is 1 or 2. Empty inputs return high 0; an intermediate
subtraction carry can be 0. The immutable input slices may overlap. Safe Rust
prevents the destination from overlapping either live immutable input.

## Collection

From the clean fixed commit, on Linux x86-64 with the project Verus toolchain:

```sh
python3 experiments/cross-fusion-20261109/capture.py /tmp/cross-fusion-evidence
```

For a Windows-created worktree under WSL, set `GIT_DIR` and `GIT_WORK_TREE` to
the WSL paths of its Git worktree metadata and checkout. The output directory
must not exist. The collector archives `native/` and this whole harness from
the exact commit, runs Verus and optimized compilation together on that source
snapshot with at most two threads, and records commands, exit codes, source,
tool, binary and metadata hashes. It tests the resulting compiled library
against a Python integer oracle, compiles negative alias fixtures, checks seven
semantic mutations, and inspects linked code generation. Source and tool
identities are checked again after the run. Logs, manifests and the complete
source snapshot are retained under the output directory.

The initial e0435541 run and its artifacts are retained separately as
historical observations; its incomplete provenance does not constitute this
collector's fresh proof identity. No timing or benchmark is part of these
checks. Performance, scoped ABBA/BAAB comparisons, Toom-4 combination
measurements and independent review remain pending.

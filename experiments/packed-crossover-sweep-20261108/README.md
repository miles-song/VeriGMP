# Packed-layout crossover experiment

**Conclusion: no robust packing policy is established.** The checked layout
path improves aggregate consumer time on this matrix, but neither a universal
path nor any of the 34 preregistered simple hybrids passes the registered
per-group no-regression gate. Production code and dispatch are unchanged.

- [Protocol](PROTOCOL.md): counts, precisions, timing boundary, split, and
  prospective decision rules.
- [Report](REPORT.md): source/tool identities, exact correctness checks,
  stratified observations, guard transitions, and limitations.
- [Evidence receipt](evidence/receipt.json): artifact hashes, archive inventories,
  source identities, and per-process records.
- [Analysis](evidence/analysis.json), [all groups](evidence/all-groups.csv),
  [strata](evidence/strata.csv), and
  [independent-repeat signs](evidence/independent-signs.csv).
- [Frozen selection](evidence/selection.json) and
  [all 34 candidates](evidence/candidates.json).

The reviewed base is fe9081f1a1d4075f74a46cdd66d97145d065c5ad. The committed
preregistration and measured source are
83c4c52f52b40c8adac2cbda6ed4f0768d0f99a0. The package is a local experiment
archive awaiting a new independent Astra Max measurement review. It has not
been merged or pushed.

## Check and replay the archived analysis

From this package's evidence directory:

    sha256sum -c SHA256SUMS

The four run archives each contain the complete raw rows, short attempts,
per-group summary, native stdout/stderr, all 32-set exact result words, oracle
receipts, input hashes, release executable, and metadata. Extract each into a
separate directory named discovery-a, discovery-b, confirmation-a, and
confirmation-b. The original absolute execution paths are retained in raw
metadata for provenance.

The following replay regenerates selection from discovery data alone, making
the replay portable across extraction locations. Its selected_rule must agree
with the archived frozen selection: null.

    python3 analyze.py --train /tmp/replay/discovery-a /tmp/replay/discovery-b \
      --select --output /tmp/replay/new-selection
    python3 analyze.py --train /tmp/replay/discovery-a /tmp/replay/discovery-b \
      --confirmation /tmp/replay/confirmation-a /tmp/replay/confirmation-b \
      --selection /tmp/replay/new-selection/selection.json \
      --output /tmp/replay/new-analysis

The replayed numerical conclusions, raw-file hashes, and source/tool identities
must match. Run-directory strings and selection-receipt hashes change when the
archive is relocated. The original receipt remains unchanged.

For a new measurement, create a clean checkout of the exact measured source
commit and use the pinned toolchain. Run the layout gate first, then the four
commands specified by PROTOCOL.md with fresh output directories. The measurement
driver rejects an uncommitted source tree, a mismatched gate/library, a changed
product source, duplicate/incomplete groups, short accepted batches, an oracle
mismatch, or a nonidentical independent result dump.

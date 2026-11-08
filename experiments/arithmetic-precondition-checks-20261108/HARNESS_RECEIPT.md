# Measurement harness binding supplement

Status: **required harness corrections passed; independent prereview and timing
authorization pending**. No benchmark binary or calibration has been executed.
This supplement binds the corrected runner; the original 735354d candidate,
[semantic/static receipt](RECEIPT.md), check-4 report and raw archive remain
immutable evidence of the arithmetic source and its tests.

Harness source is fixed at `217dafa7e07c94f4ee8baa8964d564d3b1bf3ee1`, based on
`735354d7739cf1c1da21f78b545ece58badebb3a`. Only `measure.py` and the new
`test_measure.py` change executable experiment source. Native arithmetic remains
fixed at `b31fbce898054f6db668277f8a4da88f94c95aa2`; the 359-item producer proof,
benchmark driver, both release binaries and the preregistered shapes, seed,
sample counts, durations, thresholds and acceptance criteria are unchanged.
No arithmetic proof or benchmark was rerun for these harness changes.

For every registered cell, baseline precedes candidate on even repetitions and
candidate precedes baseline on odd repetitions. GMP is inserted at
`(cell_index + repetition) % 3` without changing that relative order. This
implements the alternation already specified in [PROTOCOL.md](PROTOCOL.md).

Every process invocation is written, flushed and fsynced before launch. Its
outcome records complete stdout/stderr, both readable text and exact hex bytes,
return code and timeout status; that record is also flushed and fsynced before
JSON parsing. A timeout kills, drains and reaps the child. Nonzero exits and
timeouts fail after retaining their outcome; invalid JSON additionally retains
a parse-failure record. Parsed result records keep the existing `kind`, path,
cell, repetition, iterations, duration and checksum fields. Raw-row consumers
select `record == "result"` for parsed samples and retain all other records.

The focused fixture gate passes all 86 cells times seven repetitions: **602
order checks**. Four controlled Python stub processes cover valid JSON,
nonzero exit, timeout and invalid JSON. The fixtures check exact retained
stdout/stderr, including a non-UTF8 stderr byte; expected exit/timeout state;
and invocation/outcome fsync calls before the JSON parser runs. Timeout output
is checked after kill/reap/drain. Synthetic fixture durations are not arithmetic
measurements. The gate rehashes every native Rust input and both benchmark
binaries against the prior source-bound report/build.

External evidence root:
`E:/3sat/VeriGMP-precondition-evidence-20261108`.

| Artifact | SHA-256 |
| --- | --- |
| Corrected `measure.py` | `137d3b5607954f1fd3670220f73cd299d4f16bacb068a5a0981a30127137bcfa` |
| `test_measure.py` | `8945d14f3443149aadb5a1f22d4befadc7bbabfc251fd84cc49add7dd80d6528` |
| `harness-check-1/verification.json` | `e3f9e04b88bf8bc611605e04542fba1b4917b54335a8a481b4819839d5b0ad36` |
| `harness-binding.json` | `18b3909c8034a7d9e949cf025e691c4d52833149e76407db01da491e7caa069d` |
| `harness-prereview-manifest.json` | `523cc2c60ab0b7abc64853851f2ea081e59846289ff27844ed55fb1e18e9d9c2` |
| `harness-prereview-raw.zip` (15,148 bytes) | `913ef075067c7966f1416eb6767913d2eded5f9731600653a78d40e2a1a93e37` |
| Unchanged original `prereview-raw.zip` | `260618cdf080c21067fcdfb788cb360d857c4f4c8766268ed6de84ab370cd8cd` |

The supplement archive contains the fixture source snapshots, full order report,
controlled stub source, every invocation/outcome/result/failure row and the
binding to the original proof/static archive. Python executable identity is
recorded in the report. All new commits use miles-song <2324715854@qq.com> as
author and committer without coauthor trailers.

Run the controlled fixtures with a fresh external output directory:

```sh
python3 experiments/arithmetic-precondition-checks-20261108/test_measure.py \
  --evidence /mnt/e/3sat/VeriGMP-precondition-evidence-20261108 \
  --output /mnt/e/3sat/VeriGMP-precondition-evidence-20261108/fresh-harness-check
```

This command never executes a benchmark or verifier. Real timing still requires
independent prereview and root's coordinated quiet-window grant.

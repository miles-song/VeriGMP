# Fused Interpolation Timing Result

**Decision: NO-GO.** Do not enable or merge the fused interpolation candidate. Both complete runs miss the preregistered primary threshold, run 2 also exceeds the all-cell regression limit, baseline control drift fails, and the runner wrote outputs outside the approved directory. Retain this as a negative experiment; do not rerun for a better result.

The candidate is source commit `3a836713adbb0a6632f5131e8d57c97296d22f62` with native tree `212dd5d00d4b2159abd4627a6aaec8b16a1157e5`. The baseline was public `main` at `bf1bc40946967581852dd3b675db8140d757574e`, native tree `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`. The frozen build receipt SHA-256 is `b4a46f45e64fd91ad286c2efb8ff50b1b8d489a2534bac7ed69fd1540bcc85a3`.

| Run | Primary 15-cell geometric mean | All-86 worst ratio | Decision |
| --- | ---: | ---: | --- |
| `fused-20261109-1` | `0.9823753468` (limit `0.98`) | `1.0387009525` (limit `1.05`) | NO-GO |
| `fused-20261109-2` | `0.9863431240` (limit `0.98`) | `1.0629641214` (limit `1.05`) | NO-GO |

Each run contains 86 cells, 258 calibrations, 1,806 accepted samples and zero retained retries. The 71-control run2/run1 geometric mean is `1.0065619566`, within `[0.95, 1.05]`; nine individual controls fall outside `[0.90, 1.10]`, so the registered drift gate fails. Raw observations and all failures remain included.

There is a material output-path deviation. The root approval names `timing-attempt-02/`, but the runner wrote both runs and `summary.json` under the sibling `timing/` directory. The approved directory is empty. The copied raw records still pass the original structural and frozen-build validators, but exact output-path compliance is not claimed. The runner's original failure receipt is retained under `receipts/`.

The independent review receipt requested the `gpt-6-astra` / `max` route, but its runtime only identified as Codex GPT-6. Astra Max runtime identity is therefore not established. The independent no-go audit report and this limitation are retained in `receipts/`.

The original `static-3a83671` archive remains immutable and records the pre-timing static state. It contains the 369-item full proof, correctness/oracle, boundary, semantic-mutation and codegen evidence. Its static acceptance does not override this timing NO-GO. The two measured executables are copied byte-for-byte under `binaries/`; their SHA-256 values are `f9b3f8318426c6dfdd2887f2ea986bd2678f9865ef6a157b140cbbbf7f4375ac` (baseline) and `6bce14a79d96857f7ed4e7ce4e0d6fc46527951705382ee91661230777d89ccc` (candidate). Both used GMP SHA-256 `0ccdfb6d6f5c039465f6d002cf7e4c072d48ac6a2cffc8dd6c748dec31592804`.

The complete raw files are in [`runs/`](runs/), and the frozen build, host, review and reconciliation receipts are in [`receipts/`](receipts/). The report at [`runs/summary.json`](runs/summary.json) has SHA-256 `cf69728da6c51fd7c50c1a6498455525cc82bfca2e4c0817c36db7ee71b69e64`. Its embedded absolute paths describe the original WSL execution environment; the copies here are byte-preserving archive artifacts. This experiment establishes neither a stable performance gain nor GMP parity, solver speedup, or a checked cost theorem.

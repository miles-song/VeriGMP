# Fused Interpolation Timing Audit

**Decision: NO-GO.** Do not enable or merge this candidate. Independent recomputation confirms that both primary geometric means miss the registered `<= 0.98` limit. Run 2 also misses the all-86-cell `<= 1.05` worst-ratio limit. Control drift and a timing output-path discrepancy add provenance concerns; neither changes the raw numeric failures.

The frozen build is bound to baseline `4510b46e4010dd287c9cf760f0195f2edc32e1f7` / native tree `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06` and candidate `3a836713adbb0a6632f5131e8d57c97296d22f62` / native tree `212dd5d00d4b2159abd4627a6aaec8b16a1157e5`. The externally anchored build receipt SHA-256 is `b4a46f45e64fd91ad286c2efb8ff50b1b8d489a2534bac7ed69fd1540bcc85a3`; both executables use the same GMP SHA-256 `0ccdfb6d6f5c039465f6d002cf7e4c072d48ac6a2cffc8dd6c748dec31592804`.

| Run | Primary 15-cell GM | All-86 worst | Result |
| --- | ---: | ---: | --- |
| `fused-20261109-1` | `0.9823753468` (fail) | `1.0387009525` (pass) | NO-GO |
| `fused-20261109-2` | `0.9863431240` (fail) | `1.0629641214` (fail) | NO-GO |

The read-only repository summarizer accepted and recomputed both complete raw matrices: 86 cells, 258 calibrations, 1,806 accepted samples, zero retained retries, and 2,064 invocations per run. Run 2's two cells above `1.05` are `(0,513,64)` at `1.0629641214` and `(1,1,64)` at `1.0526127077`.

Across the 71 controls, the baseline run2/run1 geometric mean is `1.0065619566`, inside `[0.95, 1.05]`. Nine individual controls fail `[0.90, 1.10]`: `(0,25,64)=0.8991141504`, `(0,191,64)=1.1338653547`, `(0,255,64)=1.1159446839`, `(0,256,64)=1.1847604999`, `(0,257,64)=1.1831267513`, `(0,511,64)=1.1623700756`, `(0,512,64)=1.1604075325`, `(1,64,63)=0.8464079914`, and `(1,193,63)=1.1125355141`. The registered drift gate therefore fails.

There is a material output-path/provenance deviation. The root approval names `timing-attempt-02`, but [run_fused_timing.ps1](E:/3sat/VeriGMP-evidence/fused-interpolation-resume-20261109/run_fused_timing.ps1) writes both run directories and `summary.json` under sibling `timing/`; `timing-attempt-02` is empty. Raw files still pass exact structural and frozen-build validation, so retain them as NO-GO evidence. Do not describe the execution as satisfying the approved output-location condition.

The independent static review receipt records `static_accept=ACCEPT` and `timing_ready=READY`, while disclosing that the requested Astra Max role / `gpt-6-astra/max` dispatch ran in a context identified as Codex GPT-6, not Astra Max. This audit preserves that caveat and does not count Astra Max review identity as established.

The raw adjudication is [summary.json](E:/3sat/VeriGMP-evidence/fused-interpolation-resume-20261109/timing/summary.json), SHA-256 `cf69728da6c51fd7c50c1a6498455525cc82bfca2e4c0817c36db7ee71b69e64`. Per-run raw SHA-256 values are `2500e81da0ed1d00e093d5d59af256b8cd8cdebb6547a9e929579ec86bbb43a1` and `8e1100e24e7fcbd7ce997db1e32aa81d191db212c8a8e2e323f8147ef9257b6c`. No benchmark, calibration, build, or proof was run for this review.

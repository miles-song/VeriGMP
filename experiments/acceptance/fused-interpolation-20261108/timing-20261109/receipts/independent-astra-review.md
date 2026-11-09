# Independent Static Acceptance Review

**Decision:** `static_accept=ACCEPT`; `timing_ready=READY`. No benchmark or calibration was run. Timing remains unauthorized until root approves the protocol, records fresh host and affinity checks, freezes the external build digest, and grants the bounded quiet window.

The review is bound to candidate `3a836713adbb0a6632f5131e8d57c97296d22f62`, native tree `212dd5d00d4b2159abd4627a6aaec8b16a1157e5`, and the archive at `experiments/acceptance/fused-interpolation-20261108/static-3a83671`. The archive contains 943 entries; ZIP CRC, manifest hashes, and canonical receipt copies were checked. Public upstream `main` was `bf1bc40946967581852dd3b675db8140d757574e`; its native tree matches the registered baseline `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06`.

Static evidence accepted: candidate full proof is 369 verified with zero errors; both baseline and candidate passed 4,036 Python-integer oracle fixtures; boundaries, aliases, capacity behavior, and four semantic mutants are covered. The archived producer rlib/VIR and benchmark binary hashes match their recorded identities. Full codegen and per-control comparisons are retained.

**Codegen disclosure:** `toom_multiply::full` changed from 2,640 to 2,672 bytes and `toom_square::full` from 2,299 to 2,286 bytes, with changed normalized relocations. Ten default-square controls reach those changed callers without interpolation visits. Final executable body/layout identity is false for all 71 controls. Any measured result applies to the complete frozen binaries; it must not be attributed solely to the removed interpolation loop visits.

**Timing conditions:** Use `--cpu 8` explicitly because `measure.py` defaults to CPU 0 while the validator and summarizer require CPU 8. Run two complete, independent 86-cell runs using the same frozen binaries. Each run must independently satisfy primary 15-cell geometric mean `<= 0.98` and all-86 worst ratio `<= 1.05`, with the registered baseline-drift checks also passing. Measured improvement, production performance acceptance, and GMP parity remain pending.

**Review identity:** `/root/fused_interpolation_astra_audit`, assigned the independent Astra Max audit role. The runtime identity exposed in this agent context is Codex GPT-6, not Astra Max; this receipt does not claim otherwise.

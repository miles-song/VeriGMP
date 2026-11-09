# Focused helper and raw-validator receipt

当前状态为 **focused helper proof PASS；synthetic raw-validator self-check PASS**。
这不是完整 native proof、runtime oracle、codegen、timing 或 promotion receipt。
没有执行候选 benchmark，包括 calibration；没有 measured speedup 或 GMP parity 结论。

通过的 helper source 为 `cb9f26860accdfb3471e5e668b42a6a732da3608`，commit tree
`2f1921b2843b5f31d8e6144e0115149771781d92`，native tree
`212dd5d00d4b2159abd4627a6aaec8b16a1157e5`。`focused-cb9f268-01` 包含
source/tool/baseline binding、public-origin remote SHA 确认、完整命令与完整 logs。
实际 invocation 使用 `--verify-module toom_words --no-cheating --multiple-errors 0
--num-threads 2`；returncode 0，唯一 partial summary 为37 verified、0 errors。
driver PID 645、Verus launcher PID 871；无 TTY。focused receipt SHA-256 为
`760b37e156f331c50114170e85aba40b29bac40c99cfd0c5b2561d77b0e6c3ac`。

baseline 沿用同源、同工具、同 rlib/vir 绑定的358-item producer，没有重新证明。
`focused-840e2ff-01` 保留此前完整35个 obligations 中34 verified、1个逻辑
postcondition failure 的尝试；该失败不被覆盖，也不计作 candidate correctness。
两个 attempt 的精确 source bytes 均可由各自 commit 的 native blobs 恢复。

`validator-static-01` 仅生成并检查 synthetic JSON，不执行 benchmark 或 verifier。
完整86-cell schedule 含258 calibrations、1,806 accepted samples及1个 retained retry，
56种篡改被拒绝。测试涵盖 stdout/result、binary/argv、calibration ladder、固定顺序、
short-sample retry、count persistence、所有 checksum、median/ratio 和外部 build anchor。
其 source hashes、Python identity、完整 command/stdout/stderr 在 receipt 内。

`manifest.json` 绑定本目录24个原始 evidence files；`.gitattributes` 保留原始 bytes。
后续完整 native、oracle、domain/alias/capacity、strict mutants、codegen 与 frozen build
必须使用新的完整 receipts。timing 仍需独立 Astra READY 与 root quiet-window grant。

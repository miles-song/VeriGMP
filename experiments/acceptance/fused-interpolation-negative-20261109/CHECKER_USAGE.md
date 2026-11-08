# Offline replay

在包含 production prerequisite `4510b46e4010dd287c9cf760f0195f2edc32e1f7` 的 repository
checkout 中，使用 Python3 与 Git：

```sh
python experiments/acceptance/fused-interpolation-negative-20261109/check_evidence.py
```

Checker 只读取保存的 evidence。它不连接网络、不启动 Verus/compiler、benchmark、GMP、
ADB 或 process-management commands，也不重新测量。唯一子进程是本机 Git：在临时 bare
repository 中先从当前 checkout 获取 depth1 的 exact production prerequisite，确认
candidate object 尚不存在，再从 `source.bundle` 恢复 source3a 与 publication97的真实
Git commits/trees/blobs。feature branch refs 将来删除后，bundle 仍保留恢复入口。

`source.bundle` 相对4510保存五个实际 candidate commits，包含全部 source/test/protocol
bytes、focused failures 与完整 static package。其 nested static ZIP 的943项完整 payload
逐项核对，包括同源 full proof、rlib/vir、oracles、boundaries、mutants、codegen、两个
实际 benchmark binaries、build/identity receipts 和所有失败 attempts。

`review-evidence.zip` 是 independent Astra 封存的单一 literal ZIP，175 members、
23,914,268 bytes、SHA-256 `0438069f487ddac4d8e832ee10c9ec6563204bacaf34333efa6d81b746249341`。
没有重新打包或再复制一份 whole-gate。其 `captured-rev1` 保留原86个 files，
`captured-window` 保留完整两 runs 与 root/pre/post/host/plans/scripts；nested
`prior-timing-eligibility/evidence.zip` 保留 static-ready review、完整 author static
package 与 raw-validator prereview。原 reviewer receipt 和 manifest 在此按原 bytes 保存。

Checker 验证三级 review archive/member/seal hashes、57个 production native files 和
两个 public README 与4510完全一致、真实 Git recovery、static receipts、root freeze、
rev1启动前失败与rev2restoration。随后从恢复的原 source 装载未经修改的 `raw_validate.py`，仅调用其纯 raw
validator，重放 exact86-cell schedule、258 calibrations、1,806 accepted samples、
retained retry、stdout/result/argv binding 与全部 medians，重算每 run gates 和71controls。

这里的 raw replay 复用原冻结 validator；independent Astra 的额外 exact Fraction/60-digit
Decimal reconstruction 已作为 sealed historical evidence 保存。Checker 不伪造当前本机
toolchain/GMP identity，也不把离线 replay 称为重新证明或独立新测量。可选 `--output`
只允许写入尚不存在的新 JSON report。

# Fused interpolation negative checkpoint

**Disposition: NO-GO for production promotion.** 两个登记的完整 runs 都未达到
primary 与 all-86 performance gates；71 个 baseline controls 中另有 9 个超过
per-cell drift limits。生产 native source、proof status、thresholds、workspace domains、
default dispatch 和两个 public README 保持 `4510b46e4010dd287c9cf760f0195f2edc32e1f7`
的原始 bytes。这个 checkpoint 只归档已完成的实验与审查，不启用 fused candidate。

Production 的完整 producer 仍是 **358 verified items**。隔离 candidate 的完整
**369/0** 属于 source `3a836713adbb0a6632f5131e8d57c97296d22f62`，native tree
`212dd5d00d4b2159abd4627a6aaec8b16a1157e5`；不可把369写成 main 的证明数量。
Publication `97d3ee9b281b5c65d3b4c84caadb51cb79b550c0` 只增加 static evidence，
完整 source/publication map 保留在 archive。既有 W1/W2 NO-GO 仍有效。

Candidate 将 interpolation 中 factors16 与2 的两个 copy/pad、scale、subtract pipelines
各融合为一个 shifted subtraction。数学含义、cross-limb shift carry 和 subtraction
borrow 经同源 Verus 验证。原 two-producer oracle 各4,036 fixtures、domain/alias/capacity、
ownership negatives、precondition negatives、四个 semantic mutants 与 optimized codegen
evidence 均复用原封存结果，没有再次证明、编译或测量。设计中的4L loop visits、scratch
stores/reads 减少是 analytic operation-count claim；测量没有建立相应的独立 causal gain。

原 harness、seed20261108、CPU8、86 cells、每 cell/path 七个 accepted samples、
20ms calibration 与10ms sample minimum、原 baseline/candidate/GMP invocation order
都保持登记值。Primary15 是 mul512/513/1023/1024/1025/2048/4096 与
square511/512/513/1023/1024/1025/2048/4096，均 top63。每 run 分别要求 primary
candidate/baseline geometric mean<=0.98、all86 worst<=1.05，没有 pooling。

| Gate | Run 1 | Run 2 | Registered limit |
| --- | ---: | ---: | ---: |
| Primary15 geometric mean | 0.9855939276239505 fail | 0.9833143068125133 fail | <=0.98 each |
| All86 maximum ratio | 1.0617446394400472 fail | 1.0730485054388073 fail | <=1.05 each |
| Calibrations | 258 | 258 | 258 each |
| Accepted samples | 1,806 | 1,806 | 1,806 each |
| Retained short-sample retries | 0 | 1 | original immediate doubling rule |

超过1.05的全部 cells 如下；op0 为 forced full multiply、top64，op1 为 default
mul、op2 为 default square。它们包含 controls，因此不能仅报告 primary 的局部改善。

| Run | Cell `(op,n,top)` | Candidate/baseline |
| --- | --- | ---: |
| 1 | `(0,8,64)` | 1.0589258324090898 |
| 1 | `(0,1025,64)` | 1.0588294376303937 |
| 1 | `(1,511,63)` | 1.0617446394400472 |
| 1 | `(2,256,63)` | 1.0584170369901076 |
| 2 | `(0,48,64)` | 1.0506237840469277 |
| 2 | `(0,129,64)` | 1.0730485054388073 |
| 2 | `(1,1,64)` | 1.061204819573276 |

Baseline controls 的 run2/run1 geometric mean 为1.012098212025976，落在[0.95,1.05]。
要求每个 control 位于[0.90,1.10]的独立条件失败，完整9项如下。control drift 限制了稳定
性能归因；它没有取消已记录的失败，也没有授权重新测量、丢弃 run、修改阈值或拟合 dispatch。

| Control `(op,n,top)` | Baseline run2/run1 |
| --- | ---: |
| `(0,2,64)` | 0.8938525923338395 |
| `(0,23,64)` | 0.8989710791495671 |
| `(0,31,64)` | 0.8884758037941818 |
| `(0,129,64)` | 1.1175555311461582 |
| `(0,257,64)` | 1.173458127810747 |
| `(1,25,63)` | 1.1938396060874066 |
| `(1,65,63)` | 1.10756276975769 |
| `(1,192,63)` | 1.1464549673308244 |
| `(2,63,63)` | 1.107391184454415 |

Control identity 的已知边界保留：61/71 controls 的完整 library arithmetic bodies 和
normalized relocations 相同；10个 default square controls 会进入改变的 Toom full caller，
即使 interpolation visits为零。全部71 controls 的最终 absolute/raw layout identity 为false。
新增 `shift_factor` 是26-byte cold spec panic stub，无 library incoming references、
actual roots 不可达、最终 benchmark ELF 不存在。没有修改 inline/padding 逼近 identity。

Rev1 的 host window 在任何 ADB、pause 或 benchmark invocation 前因 process timestamp
identity rejection 退出，失败 receipt、原 scripts/plans/grants 与修订前后 records 全部保留。
Rev2 两个完整 runs 后 emulator 在finally中恢复；pause342.2724186秒，低于480秒 cap。
原 pre/post provenance、host observations、stdout/stderr、root grant 与 freeze receipt
按原 bytes 归档。这些记录证明保存的 host procedure 与 restoration，不证明持续无干扰。

Independent Astra Max 的 sealed review 与 exact-rational raw reconstruction 同包保留。
所有 cell medians、ratios 和 control drift 在 `summary.json`、`all-cell-ratios.csv` 与原
raw 中可读；离线复核见 `CHECKER_USAGE.md`。pre-timing READY receipts 仍保留当时的
pending-performance wording，最终 disposition 以本 checkpoint 和 sealed performance review 为准。

没有 performance acceptance、生产 promotion、GMP parity、solver/backend replacement、
全局 bit-cost 或 peak-live-space theorem 的主张。main 不因这个 evidence-only checkpoint 改变。

# exact-by3 E1 evidence archive

本目录是 `exact-by3` E1 timing window 的 **evidence-only** 归档。Astra independent adjudication 的结论是 `NO-GO`；本归档不修改 native arithmetic、dispatch、production build，也不宣称 performance acceptance。`GMP` 仍只是 registered comparator。

## Gate result

两轮各包含 86 cells、2,064 measured invocations、1,806 accepted samples、258 calibrations，raw stream 各 6,192 records。原始 raw integrity 和结构检查通过，但 registered gates 没有同时通过：

| Run | Primary geomean（threshold `<=0.98`） | All-cell max（threshold `<=1.05`） | Result |
| --- | ---: | ---: | --- |
| 1 | `1.003475113457792` | `1.0569454258446673` | primary fail; all-cell fail |
| 2 | `0.999232749796327` | `1.043576927224447` | primary fail; all-cell pass |

71-control drift 的 geomean 是 `0.9940665863937836`，observed range 是 `[0.9115531242710423, 1.1238331700636073]`，超出 registered `[0.90, 1.10]` range，因此 drift gate 也失败。两轮 worst cell 都是 `(op=2, n=2048, top=63)`；worst control drift cell 是 `(op=2, n=1, top=1)`。Astra adjudication 明确记录 `checks_failed=[]`、`raw_integrity=pass`，并且 reviewer 没有重新执行 calibration 或 timing。

结论是 registered E1 measurement **NO-GO**。该结论只描述这两轮冻结 window 的证据，不外推到其他 host、source 或 future build。

## Host restore

`host-receipt.json` 记录 `avd_restored=true`、14 条 host commands 全部 return code `0`、`pause_method=adb_pause_plus_authorized_exact_held_handle_ntsuspend`、pause `218.8228747` seconds，以及两个 observed process 的 `nt_status=0` / `status=resumed`。完整 host receipt、provenance、stdout/stderr logs 和 preflight inputs 都在 `raw-window.zip`；Astra review files 与 sealed adjudication 都在 `astra-evidence.zip`。

## Frozen identities

| Identity | SHA / value |
| --- | --- |
| candidate source head | `d5acf5ba17b32993ea0272aa9b17669412cd688b` |
| candidate source tree | `988c46ae554a1e10a0a356f3018d2568e9f2ff85` |
| candidate native tree | `1b1d99e2d9b7eee8b8e4ee7083bdf93344ab7fc4` |
| production baseline head | `4510b46e4010dd287c9cf760f0195f2edc32e1f7` |
| production baseline native tree | `72dc8a5da2cbb7eddcdd26c219d50770e8b73b06` |
| publication head/tree | `2010bd4a025d7cdf22e153a5e198f2f33b43cf77` / `3cc25bdec266408e012ffff9641e767d854474bd` |
| frozen build | `05130a2af31db678ff77f5a8dc2c4f6cb0fab9a927d07b451b1bd62182e3a3` |
| build identity receipt | `9562b2ebdb7c8da4aa59f2ebf139144dc49b710b8dfbd8458e26c8196f69e7ae` |
| timing candidate | `7fea94cbae8bdc0acb11e59b2abca9f658299141dbceb4b3be4eba1bddf39211` |
| authoritative protocol | `0e8dc6f90f46ef7bef129ecdc3ea4ae038ba0a09d921affa37ca36ee0af0ca0b` |
| root grant (historical E1 input) | `9dda301b188c436d6750641c9b0cb3f61f625237735657d960d93ad5f3815367` |
| host receipt | `24bdf28b63e32be249bd2c723464282db9fb7383a1e4e8f9289c1f4b68944cba` |
| Astra E1 adjudication | `2927663e58e3904008d5aea6f8b33f83865cdf2707b19b2dff3df389c4bcd156` |

## Archive identities

`raw-window.zip` contains 50 members and 6,502,406 uncompressed bytes; its SHA-256 is `371f96298ec7e60f9332ca71c99378a7e35c552947664f8406ad16ee8986bfea`. `astra-evidence.zip` contains 16 members and 127,498 uncompressed bytes; its SHA-256 is `b730b11df4837e9a301f15859dba245017b315ee587f70d48dd072b200e63e8c`. `manifest.json` records every member byte count and SHA-256. Run `check_evidence.py` for an offline replay of the archive, raw counts, gate recomputation, identity bindings, and evidence-only git scope.

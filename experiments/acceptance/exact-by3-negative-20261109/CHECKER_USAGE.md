# Offline checker

在本目录运行：

```text
python check_evidence.py
```

checker 只读取 `manifest.json`、`raw-window.zip`、`astra-evidence.zip` 和当前 checkout 的 Git metadata。它会验证 archive bytes/SHA、全部 50 个 raw-window members、全部 16 个 Astra members、两轮 86-cell summaries、raw record 分布、primary/all-cell/control-drift gate、host restore receipt、Astra `NO-GO` adjudication，以及从 manifest base commit 到当前 HEAD 的 diff 是否严格限制在本目录。

checker 不会启动 benchmark、calibration、Verus、Rust compiler、emulator 或 timing process。它的 `PASS` 只表示证据包可离线复核且 scope 没有越界，不表示 performance acceptance。

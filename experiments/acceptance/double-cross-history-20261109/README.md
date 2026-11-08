# Double-cross source history

This archive retains the actual eight non-main commits of the historical
double-cross branch. Its tip is `3ce342e2f09964518c9ff889b2538006c44741c0`
and its tip tree is `eb63c089229bf15e2464a44fbdcccee177362aa5`. The bundle
is relative to main `338632fef7f0cbe5b442cc6b00b7161bebded647`; its Git
prerequisite is `515f1efa0d79bcb73272df9f54917f156decf1e1`, an ancestor of
that main commit. `source.bundle` has SHA-256
`88b007fa20648ab061556d5219fe2c06e613172861488f73a2b57c03fa7a2f5a`.
The prerequisite and its reachable objects must remain available to restore
the bundle; the bundle is not a standalone copy of main history.

The existing [negative checkpoint](../arithmetic-negative-20261108/RESULTS.md)
retains the registered performance outcome: **NO-GO for production promotion**.
This archive makes no performance-acceptance claim and does not change native
arithmetic or dispatch.

## Offline recovery check

With Git and Python 3 installed, choose a new fixture path and a new receipt
path outside the source repository. The main repository must already contain
the main commit and its reachable objects; no network is used.

```text
python experiments/acceptance/double-cross-history-20261109/verify_history.py \
  --main-repo . --fixture /path/to/new-fixture.git --receipt /path/to/new-receipt.json
```

Use paths appropriate to the host. The script fetches only the specified main
commit into a new bare repository over local Git transport, confirms the
initial object set equals the main-reachable set, all eight candidate commits
are absent and no alternates are configured, checks the bundle, and imports
its advertised ref. It compares every recovered commit,
tree and parent with the recorded identities, verifies the tip tree and all
reachable objects, and runs `git fsck --full`. The fixture is retained for
inspection. `recovery-receipt.json` records one completed run; repeating the
check requires new fixture and receipt paths.

# Offline evidence checker

Run from this repository checkout with Python 3.10+:

```sh
python3 experiments/acceptance/arithmetic-precondition-checks-20261108/check_evidence.py
```

The checker uses only the Python standard library. It validates every object in
`evidence.zip` against `manifest.json`, confirms the checkout's complete
`native/` file set matches the recorded baseline hashes, confirms the archived
historical candidate source and complete-library proof identities, verifies the
host process restoration, reconstructs all 86 cells and seven sample medians
from each raw stream, and reapplies both frozen no-go criteria independently.
It does not invoke Verus, compile code, execute a benchmark, inspect environment
variables, or change any files. It exits nonzero if the evidence or restored
native source no longer matches the package.

The archive stores one object per unique SHA-256 digest. The manifest maps each
logical path to its object digest, preserving original archive member names
while avoiding repeated copies of the same sources, reports, tools and build
outputs. Original static-review, harness-review and independent-review archive
hashes and member counts remain explicit in the manifest.

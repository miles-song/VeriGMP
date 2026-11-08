# Exact-by3 experiment history

This evidence-only archive retains the four commits unique to the historical
`codex/gmp-exact-by3-20261109` branch, including the candidate native code,
experiment inputs, GMP reference notice and the `static-d5acf5b` evidence. It
does not modify production arithmetic or dispatch. The E1 timing outcome is
[NO-GO for production promotion](../exact-by3-negative-20261109/RESULTS.md),
not a performance acceptance or a claim of GMP parity.

The static receipt describes the earlier, pre-timing state: benchmark and
calibration had not yet run and independent review was pending at that point.
The later E1 negative archive records the actual timing and independent
adjudication. Retaining either archive does not accept the candidate.

| Identity | Value |
| --- | --- |
| Public main used for recovery | `2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba` |
| Bundle prerequisite, ancestor of that main | `4510b46e4010dd287c9cf760f0195f2edc32e1f7` |
| Historical branch tip | `2010bd4a025d7cdf22e153a5e198f2f33b43cf77` |
| Historical tip tree | `3cc25bdec266408e012ffff9641e767d854474bd` |
| `source.bundle` | 22,463,053 bytes; SHA-256 `15969149016acd56d7c8344dcce58679381af3b0a00b9f6ad573479adfa1e648` |
| Recovered static `evidence.zip` | 22,788,327 bytes; SHA-256 `69ff54aa4c8e56979e1d6936efa8dad15c424e210e20d6b4693e851d6f5e2348` |
| `verify_history.py` | SHA-256 `aad0fe1654ebf5527563029605d2b3a581a1f6614f73f4c898f673fa04b6ffab` |
| `check_bundle_tamper.py` | SHA-256 `11e59cf2ae0e116bbbed2fc9900104625941cc00485a9532903b863897f25cde` |
| `windows-longpaths-recovery.json` | SHA-256 `0402524cd1f8886cf9f356d80d3721da18f600c6383aa25243ca04633e0de839` |
| `linux-recovery.json` | SHA-256 `7b96b993fb139b0cd26e328481627a89188928957107dac2df998372222a7783` |
| `windows-tamper.json` | SHA-256 `179bdc214bbb137044d9b645e3db4f16822a3562bad46d935900b91fb00b647f` |
| `linux-tamper.json` | SHA-256 `b135371dd13f01df9725a6575ee6428e3d31f46456e4f0f7d7dc81ea31d190c5` |
| `windows-original-failure.log` | SHA-256 `b91272b14a3fbc580f6416be67702fdbb4c128ab98477825229b4df5d1a8340d` |
| Historical `recovery-receipt.json` | SHA-256 `e3fef9d8184c4fa7f5d56072865d802c844e49ae1785b264288a430d133919e1` |
| `audit_sensitive.py` | SHA-256 `78390e0653b0609464396d56003b0e54080688a999ef0a0f8973d4f89ce642ea` |
| `sensitive-audit-scoped.json` | SHA-256 `ad366b4eeb64db353948687012b256e7241d858d7da86b3520cd8299d1ea4389` |
| Historical `sensitive-audit.json` | SHA-256 `59c6a61a107e49b96a9e6e7e98ca02fe2b1a5a86cc59b1e18223bfcd7fb3c97e` |
| `independent-review-2c5037b.json` | SHA-256 `80067bdfe0b16b1b9b08fc1141090f97803dff07f3d0be01de7f210545d91d83` |

The four commits, oldest first, are `c28039e165e082fdcff7ab3ed72eb32252d0153e`,
`d5acf5ba17b32993ea0272aa9b17669412cd688b`,
`27f0e42188e3ecbcb6263ee9a4278e763e0da3a1`, and the tip above. The bundle
advertises `refs/heads/codex/gmp-exact-by3-20261109`. It is incremental, not a
standalone repository: the prerequisite commit and its reachable objects must
be available from public main or an equivalent complete local copy.

## Independent recovery

With Git and Python 3, run the following from a checkout containing this archive.
Choose new paths outside existing repositories; the verifier retains both the
bare fixture and its sibling `-checkout` directory. Its default source is the
public GitHub repository and it fetches the fixed main SHA, not the current tip.
For offline use, add `--main-source /path/to/local/repository` containing that
commit and its reachable objects.

```sh
python experiments/acceptance/exact-by3-history-20261109/verify_history.py \
  --fixture /path/to/new-fixture.git --receipt /path/to/new-recovery.json
python experiments/acceptance/exact-by3-history-20261109/audit_sensitive.py \
  --repo /path/to/new-fixture.git --receipt /path/to/new-sensitive-audit.json
python experiments/acceptance/exact-by3-history-20261109/check_bundle_tamper.py \
  --receipt /path/to/new-tamper.json
```

The verifier checks that the new fixture initially contains exactly main's
reachable objects, all four candidate commits are absent, and no Git alternates
are configured. It verifies and imports the bundle, compares the exact commit,
tree and parent identities, checks reachability and `git fsck --full`, and
checks out the candidate separately. It compares the complete checkout with
the tip tree, checks selected native and static archive SHA-256 values, verifies
the three reference license files against `reference.json`, and runs the
recovered static checker with `--check-publication`. It does not rerun Verus,
compile native code, or conduct timing.

The checkout and working-tree comparison use the command-scoped Git option
`core.longpaths=true`, without changing global or repository configuration. The
[Windows recovery receipt](windows-longpaths-recovery.json) records a direct
GitHub fetch followed by a successful checkout with a 153-character checkout
root; the longest checked-out path measured 299 characters. The [WSL recovery
receipt](linux-recovery.json) uses Linux Git and a local copy of the previously
fetched public main. Both runs include the static checker and `git fsck`. The
[Windows](windows-tamper.json) and [WSL](linux-tamper.json) tamper receipts show
that a changed bundle byte was rejected before fixture creation.

The historical [`recovery-receipt.json`](recovery-receipt.json) records the
earlier short-path Windows run with verifier SHA-256
`dcd763082b6aae15744d551ef9c089768b324d483e0faaea7c7b15dd911be3b4`.
The previous deep-path failure is preserved as a path-redacted
[stderr excerpt](windows-original-failure.log); the original local stderr has
SHA-256 `eafa17a3f32cd416e194a4b7b7613e036b62bad606d18254e2a38c1e8fad9ad3`.
The static checker result confirms the frozen evidence and source
correspondence; it is not a new proof, benchmark, or performance acceptance.
For manual use in a separate repository that contains the prerequisite, the
following restores the historical branch under a new name:

```sh
git bundle verify /absolute/path/source.bundle
git fetch /absolute/path/source.bundle refs/heads/codex/gmp-exact-by3-20261109:refs/heads/recovered-exact-by3
```

## Reference and content checks

The restored `experiments/exact-by3-20261109/reference/NOTICE.md` documents the
GMP 6.3.0 reference method and contains the original notice. Its associated
`COPYING.LESSERv3`, `COPYINGv2`, and `COPYINGv3` files are preserved unaltered;
the candidate's independently authored Rust retains the repository's MIT
license. The reference notice states the GMP source license as
LGPL-3.0-or-later or GPL-2.0-or-later, or both in parallel. See the restored
`reference.json` for source and license hashes.

[`sensitive-audit-scoped.json`](sensitive-audit-scoped.json) records the
credential-pattern scan of the contents of the 40 blobs and four commits among
71 non-main objects, including all 1,209 static ZIP members. It found no
matches for the listed patterns. Filename checks cover ZIP member names and the
single path `git rev-list --objects` reports for each object; they do not cover
every tree path, duplicated blob path, or name attached to a blob already in
main. The [independent review](independent-review-2c5037b.json) reproduced that
limitation with a synthetic case and separately found no matching names among
the 29 paths changed across the four candidate commits. The earlier
[`sensitive-audit.json`](sensitive-audit.json) is retained as a historical
receipt; its scope description must be read with these limits.

The frozen ZIP contains historical environment metadata, including a
user-specific absolute Windows path in `helper/freeze.json`. A supplementary
pattern inventory of the non-main commit/blob contents and ZIP members found
that path and no matches for its `/home/<name>/` or RFC1918 IPv4 patterns.
Pattern scans are not exhaustive privacy or secret audits. The original
evidence also contains logs, build metadata and compiled artifacts. This
archive preserves those historical bytes; no untracked files were added to the
historical candidate.

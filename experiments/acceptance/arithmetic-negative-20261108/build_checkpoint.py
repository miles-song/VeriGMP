#!/usr/bin/env python3
"""Package existing negative evidence only; never compile, prove, or measure."""
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '515f1efa0d79bcb73272df9f54917f156decf1e1'
PRODUCTION = 'de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9'
COMBINATION = 'f9c2977233a573ddf32dae3993b46626678ca3ca'
DOUBLE = '3ce342e2f09964518c9ff889b2538006c44741c0'
EXTERNAL = Path('E:/3sat')
REVIEW = EXTERNAL/'VeriGMP-measurement-review-astra-v2-20261108'
DOUBLE_EVIDENCE = EXTERNAL/'VeriGMP-double-cross-20261108/experiments/double-cross-20261108/evidence'
COMBO_EVIDENCE = ROOT/'experiments/combination-20261108/evidence'
sha = lambda data: hashlib.sha256(data).hexdigest()
encode = lambda value: (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    payload = {}

    def add(name, data):
        assert name not in payload, name
        payload[name] = data

    def folder(prefix, path, skip=()):
        for file in sorted(path.rglob('*')):
            if file.is_file() and file.name not in skip:
                add(prefix+'/'+file.relative_to(path).as_posix(), file.read_bytes())

    review_seal = (REVIEW/'review-artifacts.json').read_bytes()
    assert sha(review_seal) == '8745ff70654273d48621c4411499ef881865b34aad3ee7275e67657c9ad77332'
    for name, row in json.loads(review_seal)['files'].items():
        data = (REVIEW/name).read_bytes()
        assert sha(data) == row['sha256'] and len(data) == row['bytes'], name
    assert sha((REVIEW/'frozen-measurements.zip').read_bytes()) == '7e3476d8f0fb15accc0824fb9982c3a2c66c3fb055c5bffe5a8a52d0faecf825'
    with zipfile.ZipFile(REVIEW/'frozen-measurements.zip') as frozen:
        roots = dict(W1=EXTERNAL/'VeriGMP-double-cross-evidence-20261108/measurement-host-20261108-W1-01',
                     W2=EXTERNAL/'VeriGMP-combination-evidence-20261108/measurement-host-20261108-W2-01')
        inventory = {name: sha(frozen.read(name)) for name in frozen.namelist()}
        for tag, source in roots.items():
            actual = {tag+'/'+p.relative_to(source).as_posix(): sha(p.read_bytes())
                      for p in source.rglob('*') if p.is_file()}
            assert actual == {p: v for p, v in inventory.items() if p.startswith(tag+'/')}
    shutil.copyfile(REVIEW/'frozen-measurements.zip', HERE/'frozen-measurements.zip')
    folder('measurement-review', REVIEW, skip=('frozen-measurements.zip',))
    folder('earlier-W1-independent-audit', EXTERNAL/'VeriGMP-double-cross-w1-astra-v2-20261108')
    folder('window-plan', EXTERNAL/'VeriGMP-measurement-window-plans-20261108-01')
    folder('double-static', DOUBLE_EVIDENCE)
    omitted = []
    for tag, source in [('double-prereview', EXTERNAL/'VeriGMP-double-cross-prereview-astra-20261108'),
                        ('combination-prereview', EXTERNAL/'VeriGMP-combination-astra-v2-20261108')]:
        for file in sorted(source.iterdir()):
            if not file.is_file():
                continue
            data = file.read_bytes()
            if file.suffix == '.zip':
                omitted.append(dict(review=tag, name=file.name, original_path=str(file),
                    sha256=sha(data), bytes=len(data),
                    retention='Original external archive retained. Redundant reviewer collection snapshot; authoritative source/proof/binary closure is in the linked accepted static packages.'))
            else:
                add(tag+'/'+file.name, data)
    # Preserve commit and native source identities even after experiment refs retire.
    protected = git('ls-tree', '-r', '--name-only', BASE, '--', 'native').decode().splitlines()
    assert len(protected) == 57
    protected += ['README.md', 'README.zh-CN.md']
    identities = {}
    for ref in [PRODUCTION, BASE, COMBINATION, DOUBLE,
                'f46b835cb8f812293924418abc42a39978d78694',
                'b31fbce898054f6db668277f8a4da88f94c95aa2',
                '4306f32ff5778fcbc402cc8cea39c6abea3fb52a',
                'b6447382b96b91df179b393c2ef7eef18b0848de']:
        commit = git('cat-file', 'commit', ref)
        assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest() == ref
        add('git-commits/'+ref, commit)
        identities[ref] = dict(tree=git('rev-parse', ref+'^{tree}').decode().strip(),
                              native_tree=git('rev-parse', ref+':native').decode().strip())
    baseline_hashes = {}
    directories = {''} | {str(Path(name).parent).replace('\\','/') for name in protected if name.startswith('native/')}
    for directory in sorted(directories):
        tree = git('rev-parse', PRODUCTION+(':'+directory if directory else '^{tree}')).decode().strip()
        add('baseline-git-trees/'+tree, git('cat-file', 'tree', tree))
    for name in protected:
        data = git('show', PRODUCTION+':'+name)
        assert data == git('show', BASE+':'+name) == git('show', COMBINATION+':'+name) == (ROOT/name).read_bytes(), name
        baseline_hashes[name] = sha(data)
        add('production-baseline/'+name, data)
    for name in git('ls-tree', '-r', '--name-only', DOUBLE, '--', 'native').decode().splitlines():
        add('double-publication/'+name, git('show', DOUBLE+':'+name))
    add('double-publication/native.patch', git('diff', '--binary', BASE, DOUBLE, '--', 'native'))
    for name in ('PROTOCOL.md', 'README.md', 'RECEIPT.md', 'SPEC.md', 'status.json'):
        add('double-publication/experiments/double-cross-20261108/'+name,
            git('show', DOUBLE+':experiments/double-cross-20261108/'+name))
    native_audit = dict(status='pass', baseline_production=PRODUCTION, integration_base=BASE,
        inherited_combination_source=COMBINATION, protected_sha256=baseline_hashes,
        native_files=57, native_rust_files=50, public_readme_files=2,
        all_protected_bytes_equal_at_production_base_integration_base_and_candidate=True,
        baseline_complete_producer_verified_items=358,
        producer_reused_by_source_tool_export_hash=True, fresh_proof=False,
        baseline_rlib_sha256='02dabb57ecbee4b82fe99b4ed555cbd892160b999b47d01d9ac0ab9788372d28',
        baseline_vir_sha256='9890ff7d0d62f53101b41089017f913ecd6495421e54c79e2819735c3769ed41',
        identities=identities)
    (HERE/'native-byte-audit.json').write_bytes(encode(native_audit))
    audit = json.loads((REVIEW/'audit.json').read_bytes())
    summary = {tag: dict(verdict=value['verdict'], host_pause_seconds=value['host_pause_seconds'],
        host_restore_reported=value['host_restore_reported'], runs=[{k: r[k] for k in
            ['run_id','phase','accepted_samples','calibrations','minimum_sample_ns','sample_retries',
             'actual','limits','passes','verdict','primary_interaction_geomean','gmp_assessment']}
            for r in value['runs']]) for tag, value in audit['windows'].items()}
    (HERE/'summary.json').write_bytes(encode(dict(collection='pass', static_candidate='ACCEPT',
        performance='NO-GO', production_promotion_accepted=False, gmp_parity_accepted=False,
        solver_integration_accepted=False, independent_reviewer='Astra Max', windows=summary)))
    csv_output = io.StringIO(newline='')
    writer = csv.writer(csv_output, lineterminator='\n')
    writer.writerow(['window','run_id','op','n','top','path','median_ns','ratio','value'])
    for tag, value in audit['windows'].items():
        for run in value['runs']:
            for row in run['summaries']:
                for path, ns in row['median_ns'].items():
                    writer.writerow([tag,run['run_id'],row['op'],row['n'],row['top'],path,repr(ns),'',''])
                for key, ratio in row['ratios'].items():
                    writer.writerow([tag,run['run_id'],row['op'],row['n'],row['top'],'','',key,repr(ratio)])
    (HERE/'all-cell-ratios.csv').write_text(csv_output.getvalue(), encoding='utf-8', newline='')
    for name in ['RESULTS.md','CHECKER_USAGE.md','native-byte-audit.json','summary.json',
                 'all-cell-ratios.csv','check_evidence.py','test_evidence.py','build_checkpoint.py']:
        add('checkpoint/'+name, (HERE/name).read_bytes())
    validation = EXTERNAL/'VeriGMP-negative-checkpoint-validation-20261108-02'
    if validation.exists():
        folder('validation', validation)
        assert (HERE/'validation.json').read_bytes() == (validation/'validation.json').read_bytes()
    # Keep the original reviewer ZIP byte-exact and store every raw record only there.
    objects = {sha(data): data for data in payload.values()}
    with zipfile.ZipFile(HERE/'evidence.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for digest, data in sorted(objects.items()):
            info = zipfile.ZipInfo('objects/'+digest, date_time=(2026,11,8,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
    combo_receipt = json.loads((COMBO_EVIDENCE/'package.json').read_bytes())
    assert sha((COMBO_EVIDENCE/'evidence.zip').read_bytes()) == combo_receipt['archive_sha256'] == 'f195f84f88e571b7e022f88b4f6baa13a55f65222937cf16488ed7581a396991'
    manifest = dict(schema=1, disposition='VALID NEGATIVE EVIDENCE / NO-GO PROMOTION',
        integration_base=BASE, inherited_source=COMBINATION, production_base=PRODUCTION,
        native_promotion_accepted=False, performance_accepted=False, gmp_parity_accepted=False,
        raw_archive='frozen-measurements.zip', raw_archive_sha256=sha((HERE/'frozen-measurements.zip').read_bytes()),
        raw_archive_members_sha256=inventory, payload_sha256={p:sha(d) for p,d in sorted(payload.items())},
        object_bytes={h:len(d) for h,d in sorted(objects.items())}, evidence_archive='evidence.zip',
        evidence_archive_sha256=sha((HERE/'evidence.zip').read_bytes()),
        existing_combination_archive=dict(path='experiments/combination-20261108/evidence/evidence.zip',
            sha256=combo_receipt['archive_sha256'], manifest_sha256=combo_receipt['manifest_sha256'],
            logical_payloads=combo_receipt['logical_payloads'], retained_byte_exact=True),
        redundant_reviewer_snapshot_archives=omitted,
        independent_measurement_review_manifest_sha256=sha(review_seal),
        reviewer='Astra Max', source_and_tool_closure='Original static packages and preflight receipts',
        new_benchmark=False, new_calibration=False, new_build=False, new_proof=False)
    (HERE/'manifest.json').write_bytes(encode(manifest))
    print(json.dumps(dict(status='packaged',logical_payloads=len(payload),unique_objects=len(objects),
        evidence_bytes=(HERE/'evidence.zip').stat().st_size,raw_bytes=(HERE/'frozen-measurements.zip').stat().st_size)))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Retain the single sealed review ZIP and source bundle; never build, prove, or measure."""
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
REVIEW = Path('E:/3sat/VeriGMP-fused-performance-astra-v2-20261109')
BASE = '4510b46e4010dd287c9cf760f0195f2edc32e1f7'
SOURCE = '3a836713adbb0a6632f5131e8d57c97296d22f62'
PUBLICATION = '97d3ee9b281b5c65d3b4c84caadb51cb79b550c0'
SEAL = 'a61ad33cfdef28a287d3d7e7cb3c294b79d360bb5505fa30273a126b674998c1'
sha = lambda data: hashlib.sha256(data).hexdigest()
encode = lambda value: (json.dumps(value, indent=2, sort_keys=True)+'\n').encode('utf-8')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    assert not (HERE/'manifest.json').exists(), 'Do not overwrite a frozen package'
    receipt = (REVIEW/'receipt.json').read_bytes()
    assert sha(receipt) == SEAL
    seal = json.loads(receipt)
    assert seal['verdict'] == 'NO-GO' and not seal['candidate_promotion_authorized']
    raw_manifest = (REVIEW/'manifest.json').read_bytes()
    assert sha(raw_manifest) == seal['manifest_sha256']
    archive_bytes = (REVIEW/'evidence.zip').read_bytes()
    assert sha(archive_bytes) == seal['archive_sha256']
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    assert len(archive.namelist()) == len(set(archive.namelist())) == seal['archive_members'] == 175
    assert archive.read('manifest.json') == raw_manifest
    for name, row in json.loads(raw_manifest)['files'].items():
        data = archive.read(name)
        assert sha(data) == row['sha256'] and len(data) == row['bytes'], name
    shutil.copyfile(REVIEW/'evidence.zip', HERE/'review-evidence.zip')
    (HERE/'review-receipt.json').write_bytes(receipt)
    (HERE/'review-manifest.json').write_bytes(raw_manifest)
    native = git('ls-tree', '-r', '--name-only', BASE, '--', 'native').decode().splitlines()
    assert len(native) == 57 and sum(p.endswith('.rs') for p in native) == 50
    protected = native + ['README.md', 'README.zh-CN.md']
    hashes = {}
    for name in protected:
        data = git('show', BASE+':'+name)
        assert data == (ROOT/name).read_bytes(), name
        hashes[name] = sha(data)
    trees = {commit:git('rev-parse', commit+'^{tree}').decode().strip() for commit in (BASE, SOURCE, PUBLICATION)}
    audit = dict(status='pass', production_base=BASE, source_head=SOURCE, publication_head=PUBLICATION,
        native_files=57, native_rust_files=50, public_readme_files=2, protected_sha256=hashes,
        native_tree='72dc8a5da2cbb7eddcdd26c219d50770e8b73b06',
        production_producer_verified_items=358, isolated_candidate_producer_verified_items=369,
        baseline_reproved=False, candidate_reproved=False, native_candidate_promoted=False)
    (HERE/'native-byte-audit.json').write_bytes(encode(audit))
    author = json.loads(archive.read('captured-window/measurement-F1-02/adjudication.json'))
    independent = json.loads(archive.read('independent-adjudication.json'))
    assert not author['numeric_gates_pass'] and independent['verdict'] == 'NO-GO'
    summary = dict(disposition='NO-GO', performance_accepted=False, production_promotion=False,
        source_head=SOURCE, publication_head=PUBLICATION, production_base=BASE,
        production_verified_items=358, isolated_candidate_verified_items=369,
        independent_performance_receipt_sha256=SEAL,
        runs=author['runs'], baseline_validation=author['baseline_validation'],
        control_drift_failed_cells=independent['baseline_drift']['failed_cells'],
        performance_thresholds=author['performance_thresholds'],
        baseline_drift_limits=dict(control_count=71, geomean_min=.95, geomean_max=1.05,
                                   each_cell_min=.9, each_cell_max=1.1),
        pooling=False, measurement_retry=False, threshold_change=False,
        no_new_proof_oracle_or_timing=True, gmp_parity=False)
    (HERE/'summary.json').write_bytes(encode(summary))
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['run','op','n','top','primary','baseline_median_ns','candidate_median_ns',
                     'gmp_median_ns','candidate_over_baseline','candidate_over_gmp'])
    primary = {(1,n,63) for n in (512,513,1023,1024,1025,2048,4096)}
    primary |= {(2,n,63) for n in (511,512,513,1023,1024,1025,2048,4096)}
    for number in (1,2):
        report = json.loads(archive.read(f'captured-window/measurement-F1-02/fused-run-{number}/measurement.json'))
        for row in report['summaries']:
            cell = row['op'],row['n'],row['top']
            writer.writerow([number,*cell,cell in primary,
                *[repr(row['median_ns'][p]) for p in ('baseline','candidate','gmp')],
                repr(row['candidate_over_baseline']),repr(row['candidate_over_gmp'])])
    (HERE/'all-cell-ratios.csv').write_text(output.getvalue(), encoding='utf-8', newline='')
    files = {}
    for name in ['.gitattributes','source.bundle','review-evidence.zip','review-receipt.json','review-manifest.json',
                 'RESULTS.md','CHECKER_USAGE.md','summary.json','all-cell-ratios.csv','native-byte-audit.json',
                 'build_checkpoint.py','check_evidence.py']:
        data = (HERE/name).read_bytes()
        files[name] = dict(sha256=sha(data), bytes=len(data))
    manifest = dict(schema='fused-interpolation-negative-checkpoint-v1', disposition='NO-GO',
        production_base=BASE, source_head=SOURCE, publication_head=PUBLICATION, source_trees=trees,
        source_bundle_prerequisite=BASE, source_bundle_ref='refs/heads/codex/gmp-fused-interpolation-20261108',
        independent_performance_receipt_sha256=SEAL, protected_sha256=hashes,
        checkpoint_files=files, review_archive_sha256=seal['archive_sha256'],
        native_promotion=False, gmp_parity=False)
    (HERE/'manifest.json').write_bytes(encode(manifest))
    print(json.dumps(dict(status='packaged', literal_review_members=175,
        review_bytes=len(archive_bytes), source_bundle_bytes=(HERE/'source.bundle').stat().st_size,
        manifest_sha256=sha((HERE/'manifest.json').read_bytes())), indent=2))


if __name__ == '__main__':
    main()

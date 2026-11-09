#!/usr/bin/env python3
"""Offline archive integrity and saved-data checks; never run the prototype or its scripts."""
import argparse
import ast
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import sys
import zipfile

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check():
    manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
    summary = json.loads((HERE / 'summary.json').read_text(encoding='utf-8'))
    assert sha((HERE / 'evidence.zip').read_bytes()) == manifest['archive_sha256'] == summary['archive_sha256']
    assert sha((HERE / 'summary.json').read_bytes()) == manifest['summary_sha256']
    assert sha((HERE / 'cell-ratios.csv').read_bytes()) == manifest['cell_ratios_sha256'] == summary['cell_ratios_sha256']
    with zipfile.ZipFile(HERE / 'evidence.zip') as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert set(archive.namelist()) == set(manifest['entries'])
        data = {}
        for name in archive.namelist():
            path = PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts
            assert path.suffix not in ('.exe', '.rlib', '.vir', '.dll', '.so', '.bundle', '.tar')
            value = archive.read(name)
            assert not value.startswith((b'\x7fELF', b'MZ'))
            assert (sha(value), len(value)) == (manifest['entries'][name]['sha256'], manifest['entries'][name]['bytes'])
            if path.suffix == '.py': ast.parse(value.decode('utf-8'), filename=name)
            data[name] = value
    for row in manifest['original_files']:
        assert sha(data[row['archive_path']]) == row['sha256'] and len(data[row['archive_path']]) == row['bytes']
    def load(name): return json.loads(data[name].decode('utf-8-sig'))
    build, baseline = load('build-03/build.json'), load('baseline/summary.json')
    plan, report = load('screen-01/plan.json'), load('screen-01/report.json')
    post, pre = load('screen-01/postflight.json'), load('screen-01/preflight.json')
    review = load('reviews/completed/review.json')
    assert manifest['source_commit'] == review['source_binding']['commit'] == '8df6f173040f8cc9a0957420be9dfb832fe26807'
    assert manifest['native_tree'] == baseline['native_tree'] == build['baseline_native_tree'] == '72dc8a5da2cbb7eddcdd26c219d50770e8b73b06'
    assert build['status'] == 'compiled_unverified_prototype' and build['verus_runs'] == 0
    assert build['baseline_pair'] == baseline['library_pair']
    assert sha(data['baseline/summary.json']) == build['baseline_summary_sha256']
    for name, digest in build['source_sha256'].items():
        assert sha(data['source/' + name]) == digest
        assert sha((HERE.parent / name).read_bytes()) == digest
    for prefix in ('source', 'tools', 'pair'):
        assert data[f'baseline/{prefix}-before.json'] == data[f'baseline/{prefix}-after.json']
    binaries = {row['label']: row['binary_sha256'] for row in build['builds']}
    for row in build['builds']:
        assert row['returncode'] == 0 and sha(data['build-03/' + row['label'] + '.s']) == row['assembly_sha256']
    assert binaries['release'] == plan['binary_sha256'] == report['binary_sha256'] == pre['binary_sha256']
    assert sha(data['screen-01/plan.json']) == pre['plan_sha256'] == report['plan_sha256']
    assert sha(data['build-03/build.json']) == plan['build_receipt_sha256']
    assert sha(data['screen-01/raw.jsonl']) == report['raw_sha256']
    for mode, label in (('release', 'release'), ('overflow', 'overflow-checked')):
        oracle = load('oracle-' + mode + '-03/oracle.json')
        assert oracle['status'] == 'pass_unverified_integer_oracle' and oracle['cases'] == 12118
        assert len(oracle['invalid']) == 5 and all(row['returncode'] != 0 for row in oracle['invalid'])
        assert oracle['proof_claim'] is False and oracle['performance_samples'] == 0
        assert oracle['binary_sha256'] == binaries[label] and oracle['source_sha256'] == build['source_sha256']
        for name, digest in oracle['artifacts'].items(): assert sha(data['oracle-common/' + name]) == digest
    for name, key in (('preflight-input.txt', 'inputs_sha256'), ('preflight-stdout.txt', 'stdout_sha256'), ('preflight-stderr.txt', 'stderr_sha256')):
        assert sha(data['screen-01/' + name]) == pre[key]
    assert pre['operations'] == 16 and pre['samples'] == 0 and pre['proof_claim'] is False
    assert post['status'] == 'pass' and len(post['checks']) == 23 and all(post['checks'].values())
    assert post['proof_claim'] is False and post['production_acceptance'] is False
    for name, digest in post['artifacts'].items():
        target = 'scripts/' + name if '/' not in name else name
        assert sha(data[target]) == digest
    assert review['decision']['archive_review'] == 'APPROVE_NO_GO_ARCHIVE'
    assert review['decision']['registered_broad_screen'] == 'NO_GO'
    assert sha(data['reviews/completed/review.json']) == '0b878327f700c74f03d7a79349d0bdb040bb15158e5689da0cb13a1cffd8c3b1'
    for name, digest in review['evidence_sha256'].items():
        target = 'reviews/' + name if name == 'prototype-screen-review.json' else 'scripts/' + name if '/' not in name else name
        assert sha(data[target]) == digest
    rows = [json.loads(line) for line in data['screen-01/raw.jsonl'].splitlines()]
    assert len(rows) == plan['sample_invocations'] == 224 and len(plan['cells']) == len(report['cells']) == 8
    assert plan['retry'] is False and plan['minimum_batch_ns'] == 10_000_000
    assert plan['go_geomean_ratio_max'] == 0.90 and plan['go_cell_ratio_max'] == 1.03
    csv_rows = list(csv.DictReader(io.StringIO((HERE / 'cell-ratios.csv').read_text(encoding='utf-8'))))
    ratios, minima = [], []
    for index, cell in enumerate(plan['cells']):
        assert sha(data['screen-01/' + PurePosixPath(cell['input']).name]) == cell['input_sha256']
        values = {'row': [], 'column': []}
        for block in range(7):
            order = ('row', 'column', 'column', 'row') if (index + block) % 2 == 0 else ('column', 'row', 'row', 'column')
            for position, side in enumerate(order):
                row = rows[index * 28 + block * 4 + position]
                assert (row['cell'], row['block'], row['position'], row['side']) == (index, block, position, side)
                assert row['command'] == [plan['binary'], 'sample', cell['input'], side + '_' + cell['operation'], str(cell['count'])]
                assert row['returncode'] == 0 and row['stderr'] == ''
                fields = row['stdout'].split()
                assert fields[:3] == ['sample', side + '_' + cell['operation'], str(cell['count'])] and len(fields) == 5
                values[side].append(int(fields[3]))
        saved = report['cells'][index]
        assert values == saved['samples'] and len(values['row']) == len(values['column']) == 14
        ratio = statistics.median(values['column']) / statistics.median(values['row'])
        minimum = min(min(values['row']), min(values['column']))
        assert ratio == saved['ratio'] == float(csv_rows[index]['candidate_over_baseline'])
        assert minimum == saved['minimum_batch_ns']
        ratios.append(ratio)
        minima.append(minimum)
    gm = math.exp(statistics.mean(map(math.log, ratios)))
    assert math.isclose(gm, report['geomean_ratio'], rel_tol=1e-14)
    assert min(minima) >= 10_000_000 and gm > 0.90 and max(ratios) > 1.03
    assert report['screen_numerical_go'] is False and summary['numerical_go'] is False
    assert summary['candidate_formal_proof'] is False and summary['production_acceptance'] is False
    assert summary['geomean_ratio'] == report['geomean_ratio'] and summary['worst_cell_ratio'] == max(ratios)
    assert load('screen-01/windows-git-after.json')['commit'] == manifest['source_commit']
    assert load('screen-01/windows-git-after.json')['status'] == ''
    window = load('screen-01/window.json')
    assert window['screen_exit'] == window['resume_status'] == 0 and window['qemu_alive'] is True
    assert data['screen-01/resume-watchdog.stop'].decode('utf-8-sig') == 'resumed by root finally'
    return dict(status='pass_archive_integrity_and_saved_data_only', archive_sha256=manifest['archive_sha256'],
                manifest_sha256=sha((HERE / 'manifest.json').read_bytes()), summary_sha256=sha((HERE / 'summary.json').read_bytes()),
                entries=len(data), original_file_bindings=len(manifest['original_files']), calls=224,
                geomean_ratio=report['geomean_ratio'], worst_cell_ratio=max(ratios), postflight_checks=23,
                proof_build_oracle_benchmark_or_process_control_executed=False,
                limitations='Omitted executable/pair/tool binaries are bound by retained original receipts and review, not reverified by this portable checker.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check()
    if args.output:
        result['checker_sha256'] = sha(Path(__file__).read_bytes())
        result['interpreter'] = dict(path=sys.executable, version=sys.version, sha256=sha(Path(sys.executable).read_bytes()))
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

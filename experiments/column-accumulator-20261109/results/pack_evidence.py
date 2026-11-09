#!/usr/bin/env python3
"""Copy public frozen evidence only. Never execute the archived experiment scripts."""
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
EVIDENCE = Path('E:/3sat/VeriGMP-root-column-prototype-20261109')
BASELINE = Path('E:/3sat/VeriGMP-cross-fusion-baseline-fresh-20261109')
SOURCE_COMMIT = '8df6f173040f8cc9a0957420be9dfb832fe26807'
NATIVE = '72dc8a5da2cbb7eddcdd26c219d50770e8b73b06'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    for name in ('evidence.zip', 'manifest.json', 'summary.json', 'cell-ratios.csv'):
        if (HERE / name).exists():
            raise FileExistsError('immutable archive already exists: ' + name)
    files, origins = {}, []

    def include(path, archive_path, origin_root):
        data = (subprocess.run(['git', '-C', str(SOURCE.parents[1]), 'show', SOURCE_COMMIT + ':' + path.name],
                              check=True, capture_output=True).stdout
                if origin_root == 'source-policy' else path.read_bytes())
        if archive_path in files:
            assert files[archive_path] == data, 'deduplicated oracle bytes differ'
        else:
            files[archive_path] = data
        origin_base = {'source': SOURCE, 'baseline': BASELINE, 'evidence': EVIDENCE, 'source-policy': SOURCE.parents[1]}[origin_root]
        origins.append(dict(origin_root=origin_root, origin=str(path.relative_to(origin_base)).replace('\\', '/'),
            archive_path=archive_path, sha256=sha(data), bytes=len(data)))

    for name in ('column.rs', 'runner.rs', 'oracle.py', 'DESIGN.md', 'design-plan.json'):
        include(SOURCE / name, 'source/' + name, 'source')
    include(SOURCE.parents[1] / 'AGENTS.md', 'source/AGENTS.md', 'source-policy')
    include(SOURCE.parents[1] / 'LICENSE', 'source/LICENSE', 'source-policy')
    for name in ('build-03.py', 'screen.py', 'preflight.py', 'postflight.py', 'run-window.ps1', 'resume-watchdog.ps1'):
        include(EVIDENCE / name, 'scripts/' + name, 'evidence')
    include(EVIDENCE / 'prototype-screen-review.json', 'reviews/prototype-screen-review.json', 'evidence')
    for name in ('review.json', 'REVIEW.md'):
        include(EVIDENCE / 'independent-completed-review' / name, 'reviews/completed/' + name, 'evidence')
    assert sha(files['reviews/completed/review.json']) == '0b878327f700c74f03d7a79349d0bdb040bb15158e5689da0cb13a1cffd8c3b1'
    assert sha(files['reviews/completed/REVIEW.md']) == 'be622eafc77187425e656485ee42586853409a7c6951aef0bfdcc66da1a1dfdd'
    for path in sorted((EVIDENCE / 'screen-01').iterdir()):
        assert path.suffix in ('.json', '.jsonl', '.txt', '.ready', '.stop')
        include(path, 'screen-01/' + path.name, 'evidence')
    for name in ('build.json', 'release.s', 'overflow-checked.s', 'column-prefix.s',
                 'release.stdout', 'release.stderr', 'overflow-checked.stdout', 'overflow-checked.stderr'):
        include(EVIDENCE / 'build-03' / name, 'build-03/' + name, 'evidence')
    for mode in ('release', 'overflow'):
        root = EVIDENCE / ('oracle-' + mode + '-03')
        include(root / 'oracle.json', root.name + '/oracle.json', 'evidence')
        for name in ('inputs.txt', 'stdout.txt', 'stderr.txt'):
            include(root / name, 'oracle-common/' + name, 'evidence')
    for name in ('summary.json', 'source-before.json', 'source-after.json', 'tools-before.json', 'tools-after.json',
                 'pair-before.json', 'pair-after.json', 'commands.jsonl', 'artifacts.json', 'environment.json'):
        include(BASELINE / name, 'baseline/' + name, 'baseline')
    for name in ('library-gate.log', 'platform.log', 'rustc-version.log', 'verus-version.log', 'z3-version.log'):
        include(BASELINE / 'logs' / name, 'baseline/logs/' + name, 'baseline')
    build = json.loads(files['build-03/build.json'])
    baseline = json.loads(files['baseline/summary.json'])
    report = json.loads(files['screen-01/report.json'])
    review = json.loads(files['reviews/completed/review.json'])
    assert build['status'] == 'compiled_unverified_prototype' and build['verus_runs'] == 0
    assert build['baseline_native_tree'] == baseline['native_tree'] == NATIVE
    assert build['baseline_pair'] == baseline['library_pair']
    assert review['source_binding']['commit'] == SOURCE_COMMIT
    assert review['decision']['archive_review'] == 'APPROVE_NO_GO_ARCHIVE'
    for name, digest in build['source_sha256'].items():
        assert sha(files['source/' + name]) == digest
    for name, digest in review['evidence_sha256'].items():
        target = 'reviews/' + name if name == 'prototype-screen-review.json' else 'scripts/' + name if '/' not in name else name
        assert sha(files[target]) == digest
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('operation', 'n', 'pattern', 'count', 'row_median_ns', 'column_median_ns',
                     'candidate_over_baseline', 'minimum_batch_ns'))
    for cell in report['cells']:
        writer.writerow((cell['operation'], cell['n'], cell['pattern'], cell['count'], cell['row_median_ns'],
                         cell['column_median_ns'], cell['ratio'], cell['minimum_batch_ns']))
    (HERE / 'cell-ratios.csv').write_text(output.getvalue(), encoding='utf-8', newline='\n')
    with zipfile.ZipFile(HERE / 'evidence.zip', 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (2026, 11, 9, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data, compresslevel=9)
    summary = dict(status='NO_GO_FOR_PREREGISTERED_BROAD_PROTOTYPE_SCOPE', source_commit=SOURCE_COMMIT,
        baseline_native_tree=NATIVE, build_status=build['status'], candidate_formal_proof=False,
        production_acceptance=False, calls=224, cells=8, blocks_per_cell=7, batches_per_side_per_cell=14,
        minimum_batch_ns=min(cell['minimum_batch_ns'] for cell in report['cells']),
        geomean_ratio=report['geomean_ratio'], geomean_limit=0.90,
        worst_cell_ratio=report['every_cell_max'], cell_limit=1.03, numerical_go=report['screen_numerical_go'],
        low_115='Prospective scoped hypothesis only; broad failure and retained variation prevent accepted performance claims.',
        cells_summary=[{k: c[k] for k in ('operation', 'n', 'pattern', 'count', 'ratio', 'minimum_batch_ns')}
                       for c in report['cells']],
        low_115_all_max_variation=review['environment_and_supervision']['low_115_variation'],
        environment_limits=review['environment_and_supervision']['limits'],
        reviewer_runtime_identity=review['reviewer']['runtime_identity'],
        retained_external_history=['build-01', 'build-02', 'oracle-release-01', 'oracle-overflow-01'],
        oracle_scope='12118 cases and 5 invalid-input controls in each retained build03 mode; saved evidence, no replay.',
        postflight_named_checks=23, benchmark_replayed_for_archive=False,
        archive_sha256=sha((HERE / 'evidence.zip').read_bytes()),
        cell_ratios_sha256=sha((HERE / 'cell-ratios.csv').read_bytes()))
    write(HERE / 'summary.json', summary)
    manifest = dict(schema='verigmp-column-prototype-public-archive-v1', source_commit=SOURCE_COMMIT,
        native_tree=NATIVE, archive='evidence.zip', archive_sha256=summary['archive_sha256'],
        archive_bytes=(HERE / 'evidence.zip').stat().st_size,
        entries={name: dict(sha256=sha(data), bytes=len(data)) for name, data in sorted(files.items())},
        original_files=origins,
        deduplication='Both oracle03 input/output/stderr streams are byte-identical and stored once under oracle-common/.',
        roots=dict(source='experiments/column-accumulator-20261109 at ' + SOURCE_COMMIT,
                   evidence=str(EVIDENCE), baseline=str(BASELINE), source_policy='AGENTS.md and LICENSE at ' + SOURCE_COMMIT),
        omitted='No executable, rlib, VIR, tool binary, private application code or unrelated historical attempt payload.',
        review_only=True, timing_authorized=False, candidate_proof=False, production_acceptance=False,
        summary_sha256=sha((HERE / 'summary.json').read_bytes()),
        cell_ratios_sha256=summary['cell_ratios_sha256'])
    write(HERE / 'manifest.json', manifest)
    print(json.dumps(dict(status='packed_public_evidence_only', entries=len(files), origins=len(origins),
                         archive_bytes=manifest['archive_bytes'], archive_sha256=manifest['archive_sha256'])))


if __name__ == '__main__':
    main()

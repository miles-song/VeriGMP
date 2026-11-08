#!/usr/bin/env python3
"""Offline evidence replay only. Requires Python and Git; never runs arithmetic binaries."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
import types
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '4510b46e4010dd287c9cf760f0195f2edc32e1f7'
SOURCE = '3a836713adbb0a6632f5131e8d57c97296d22f62'
PUBLICATION = '97d3ee9b281b5c65d3b4c84caadb51cb79b550c0'
BASE_NATIVE = '72dc8a5da2cbb7eddcdd26c219d50770e8b73b06'
CANDIDATE_NATIVE = '212dd5d00d4b2159abd4627a6aaec8b16a1157e5'
BUILD_SHA = 'bac446bdf52f2a9ce6babb653019427d3f65ec36c90de68b5a8459ae945a62c4'
STATIC = 'experiments/acceptance/fused-interpolation-20261108/static-3a83671/'
PRIMARY = {(1,n,63) for n in (512,513,1023,1024,1025,2048,4096)}
PRIMARY |= {(2,n,63) for n in (511,512,513,1023,1024,1025,2048,4096)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def geometric_mean(values):
    return math.exp(sum(math.log(v) for v in values) / len(values))


def check():
    manifest = json.loads((HERE/'manifest.json').read_bytes())
    require(manifest['disposition'] == 'NO-GO', 'wrong checkpoint disposition')
    for name, row in manifest['checkpoint_files'].items():
        data = (HERE/name).read_bytes()
        require(sha(data) == row['sha256'] and len(data) == row['bytes'], name)
    archive_data = (HERE/'review-evidence.zip').read_bytes()
    require(sha(archive_data) == manifest['review_archive_sha256'], 'review archive drift')
    archive = zipfile.ZipFile(io.BytesIO(archive_data))
    seal_bytes = (HERE/'review-receipt.json').read_bytes()
    require(sha(seal_bytes) == manifest['independent_performance_receipt_sha256'] ==
            'a61ad33cfdef28a287d3d7e7cb3c294b79d360bb5505fa30273a126b674998c1', 'independent seal drift')
    seal = json.loads(seal_bytes)

    def sealed_archive(data, receipt, raw_manifest):
        require(sha(data) == receipt['archive_sha256'] and sha(raw_manifest) == receipt['manifest_sha256'], 'review seal binding')
        z = zipfile.ZipFile(io.BytesIO(data))
        files = json.loads(raw_manifest)['files']
        require(len(z.namelist()) == len(set(z.namelist())) == receipt['archive_members'], 'sealed archive count')
        require(set(z.namelist()) == set(files)|{'manifest.json'}, 'sealed archive inventory')
        require(z.read('manifest.json') == raw_manifest, 'sealed manifest bytes')
        for name, row in files.items():
            item = z.read(name)
            require(sha(item) == row['sha256'] and len(item) == row['bytes'], 'sealed member: '+name)
        require(sha(z.read('review.json')) == receipt['review_sha256'], 'sealed review bytes')
        return z

    sealed_archive(archive_data, seal, (HERE/'review-manifest.json').read_bytes())

    def saved(name):
        return archive.read(name)

    def load(name):
        return json.loads(saved(name))

    for name, digest in manifest['protected_sha256'].items():
        require(sha((ROOT/name).read_bytes()) == digest, 'production source drift: '+name)
    require(git(ROOT, 'rev-parse', BASE+':native').decode().strip() == BASE_NATIVE, 'baseline native tree')
    # A fresh shallow repository contains only the production prerequisite before
    # importing the bundle. No candidate objects are borrowed from the live repo.
    with tempfile.TemporaryDirectory(prefix='verigmp-fused-evidence-') as temporary:
        temp = Path(temporary).resolve()
        require(temp.parent == Path(tempfile.gettempdir()).resolve() and
                temp.name.startswith('verigmp-fused-evidence-'), 'unexpected temporary directory')
        recovered = temp/'recovered.git'
        subprocess.run(['git', 'init', '--bare', str(recovered)], check=True, capture_output=True)
        git(recovered, 'fetch', '--depth=1', '--no-tags', '--no-write-fetch-head', str(ROOT), BASE)
        candidate_absent = subprocess.run(['git', '-C', str(recovered), 'cat-file', '-e', PUBLICATION],
                                         capture_output=True).returncode != 0
        require(candidate_absent, 'recovery already contained candidate objects')
        git(recovered, 'bundle', 'verify', str(HERE/'source.bundle'))
        git(recovered, 'fetch', '--no-tags', str(HERE/'source.bundle'),
            'refs/heads/codex/gmp-fused-interpolation-20261108:refs/heads/archived-candidate')
        for commit, tree in manifest['source_trees'].items():
            require(git(recovered, 'rev-parse', commit+'^{tree}').decode().strip() == tree, 'recovered tree')
        require(git(recovered, 'rev-parse', SOURCE+':native').decode().strip() == CANDIDATE_NATIVE, 'candidate native tree')
        require(git(recovered, 'rev-parse', PUBLICATION+':native').decode().strip() == CANDIDATE_NATIVE, 'publication native tree')
        for name, digest in manifest['protected_sha256'].items():
            require(sha(git(recovered, 'show', BASE+':'+name)) == digest, 'restored production bytes')
        delta = git(recovered, 'diff', '--name-status', SOURCE, PUBLICATION).decode().splitlines()
        require(len(delta) == 11 and all(v.startswith('A\t'+STATIC) for v in delta), 'publication delta')
        static_bytes = git(recovered, 'show', PUBLICATION+':'+STATIC+'evidence.zip')
        static_manifest = json.loads(git(recovered, 'show', PUBLICATION+':'+STATIC+'manifest.json'))
        require(sha(static_bytes) == '77116e0a56509aa4b09c238733e6ad41af0b023b01ceb2c56ac5c7ee7463416f', 'static archive drift')
        static_archive = zipfile.ZipFile(io.BytesIO(static_bytes))
        require(len(static_archive.namelist()) == len(set(static_archive.namelist())) == 943, 'static inventory')
        require(set(static_archive.namelist()) == set(static_manifest['files']), 'static manifest inventory')
        for name, row in static_manifest['files'].items():
            data = static_archive.read(name)
            require(sha(data) == row['sha256'] and len(data) == row['bytes'], 'static member: '+name)
        timing_receipt = load('prior-timing-eligibility/receipt.json')
        timing_archive = sealed_archive(saved('prior-timing-eligibility/evidence.zip'), timing_receipt,
                                        saved('prior-timing-eligibility/manifest.json'))
        require(timing_archive.read('author-static/evidence.zip') == static_bytes, 'nested static identity')
        raw_receipt = json.loads(timing_archive.read('prior-raw-validator/receipt.json'))
        sealed_archive(timing_archive.read('prior-raw-validator/evidence.zip'), raw_receipt,
                       timing_archive.read('prior-raw-validator/manifest.json'))
        build_bytes = static_archive.read('build-identity-01/bench-build.json')
        require(sha(build_bytes) == BUILD_SHA, 'frozen build drift')
        build = json.loads(build_bytes)
        identity = json.loads(static_archive.read('build-identity-01/identity.json'))
        require(identity['producers']['baseline']['verified_items'] == 358 and
                identity['producers']['candidate']['verified_items'] == 369, 'producer scope')
        validator_bytes = git(recovered, 'show', SOURCE+':experiments/fused-interpolation-20261108/raw_validate.py')
        require(sha(validator_bytes) == '90f564d57098ac703b73635f47981c334b6c32ff9b0c98c17540991838c14e59', 'validator drift')
        validator = types.ModuleType('frozen_raw_validate')
        validator.__file__ = str(temp/'raw_validate.py')
        exec(compile(validator_bytes, validator.__file__, 'exec'), validator.__dict__)
        freeze = load('captured-window/measurement-F1-02/root-measurement-freeze.json')
        require(sha(saved('captured-window/measurement-F1-02/root-measurement-freeze.json')) ==
                '29946c99d968c26b8216b34040d7769578db1d9d716690699b33228a1a965b27', 'root freeze drift')
        for name, row in freeze['files'].items():
            data = saved('captured-window/measurement-F1-02/'+name)
            require(sha(data) == row['sha256'] and len(data) == row['bytes'], 'frozen measurement file')
        rows = []
        results = []
        for number in (1, 2):
            prefix = 'captured-window/measurement-F1-02/fused-run-'+str(number)+'/'
            report = validator.strict_json(saved(prefix+'measurement.json'))
            computed, receipt = validator.validate_report(report, saved(prefix+'raw.jsonl'), build, BUILD_SHA)
            ratios = {(r['op'],r['n'],r['top']):r['candidate_over_baseline'] for r in computed}
            primary = geometric_mean([ratios[c] for c in sorted(PRIMARY)])
            worst = max(ratios.values())
            require(primary > .98 and worst > 1.05, 'negative result changed')
            results.append(dict(run=number, primary_geomean=primary, all_86_worst=worst, **receipt))
            rows.append({(r['op'],r['n'],r['top']):r for r in computed})
        controls = set(validator.CELLS)-PRIMARY
        drift = {c:rows[1][c]['median_ns']['baseline']/rows[0][c]['median_ns']['baseline'] for c in controls}
        failures = [c for c in sorted(controls) if not .9 <= drift[c] <= 1.1]
        summary = json.loads((HERE/'summary.json').read_bytes())
        author = load('captured-window/measurement-F1-02/adjudication.json')
        independent = load('independent-adjudication.json')
        require(independent['verdict'] == 'NO-GO' and not author['numeric_gates_pass'], 'sealed verdict differs')
        for i, result in enumerate(results):
            require(math.isclose(result['primary_geomean'], author['runs'][i]['primary_geomean'], rel_tol=1e-14), 'primary result')
            require(result['all_86_worst'] == author['runs'][i]['all_86_worst'], 'worst result')
            require(summary['runs'][i] == author['runs'][i], 'summary run changed')
        require(len(controls) == 71 and len(failures) == 9, 'control drift coverage')
        require(summary['baseline_validation'] == author['baseline_validation'], 'control summary changed')
        require(math.isclose(geometric_mean(list(drift.values())), 1.012098212025976, rel_tol=1e-14), 'drift mean')
        failed = load('captured-rev1/measurement-F1-01/host-receipt.json')
        require(failed['status'] == 'failed' and failed['benchmark_launched'] is False and
                failed['commands'] == failed['resume'] == failed['observations'] == [], 'rev1 failure was lost')
        require(freeze['avd_restored'] is True and freeze['pause_seconds'] < 480 and
                all(r['status'] == 'resumed' and r['nt_status'] == 0 for r in freeze['resume']), 'host restoration')
        require(seal['verdict'] == 'NO-GO' and seal['performance_acceptance'] == 'REJECTED' and
                not seal['candidate_promotion_authorized'] and not seal['remeasurement_authorized'], 'independent disposition')
    return dict(status='pass', disposition='NO-GO', production_promotion=False,
                protected_files=len(manifest['protected_sha256']), source_bundle_recovered=True,
                static_members_verified=943, runs=results, control_cells=71,
                baseline_drift_failed_cells=failures, benchmark_executed=False,
                verifier_executed=False, compiler_executed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    result = check()
    text = json.dumps(result, indent=2)+'\n'
    if arguments.output:
        require(not arguments.output.exists(), 'use a fresh output file')
        arguments.output.write_text(text, encoding='utf-8')
    print(text, end='')

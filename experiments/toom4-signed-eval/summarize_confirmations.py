"""Recompute every registered comparison from the two retained raw CSVs."""
from pathlib import Path
import csv
import hashlib
import json
import os
import statistics

STAGE = Path(__file__).resolve().parent
OUT = STAGE / 'evidence'
assert os.name == 'posix', 'Run inside the recorded WSL environment to resolve runtime-library symlinks'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


verification_path = OUT / 'verification.json'
verification = json.loads(verification_path.read_text())
window_path = OUT / 'confirmation-window.json'
window = json.loads(window_path.read_text())
target_path = STAGE / 'baseline/native/performance-target.json'
target = json.loads(target_path.read_text())
assert verification['status'] == 'pass'
assert window['status'] == 'pass'
assert window['tags'] == ['default1', 'default2']
shapes = [tuple(shape) for shape in target['key_shapes']['shapes']]
primary = set(target['principal_workloads']['limbs'])
records = []
for tag in window['tags']:
    raw = OUT / tag / 'benchmark.csv'
    binding_path = OUT / (tag + '-binding.json')
    measured_path = OUT / tag / 'measurements.json'
    binding = json.loads(binding_path.read_text())
    measured = json.loads(measured_path.read_text())
    assert binding['status'] == measured['status'] == 'pass'
    assert binding['verification_report_sha256'] == sha(verification_path)
    assert binding['raw_sha256'] == measured['raw_sha256'] == sha(raw)
    assert window['bindings'][tag]['sha256'] == sha(binding_path)
    assert window['bindings'][tag]['raw_sha256'] == sha(raw)
    assert binding['measurements_sha256'] == sha(measured_path)
    assert measured['verified_library_identities'] == verification['libraries']
    assert measured['benchmark_binary_sha256'] == verification['benchmark_binary_sha256']
    assert measured['benchmark_source_sha256'] == verification['benchmark_source_sha256']
    assert {str(Path(path).resolve()): digest for path, digest in measured['linked_library_sha256'].items()} == verification['runtime_library_sha256']
    samples = list(csv.DictReader(raw.read_text().splitlines()))
    groups = {}
    for row in samples:
        key = tuple(int(row[name]) for name in ('operation', 'limbs', 'top', 'mode'))
        groups.setdefault(key, []).append(row)
    assert set(groups) == {(op, n, top, mode) for op in (0, 1) for n, top in shapes for mode in (0, 1, 2, 3)}
    medians = {}
    for key, group in groups.items():
        assert len(group) == 7
        assert {int(row['repetition']) for row in group} == set(range(7))
        assert all(int(row['iterations']) > 0 and int(row['ns']) >= 10_000_000 for row in group)
        medians[key] = statistics.median(int(row['ns']) / int(row['iterations']) for row in group)
    comparisons = []
    for op in (0, 1):
        for n, top in shapes:
            baseline, previous, candidate, gmp = [medians[op, n, top, mode] for mode in (0, 1, 2, 3)]
            comparisons.append({'operation': 'mul_mod' if op == 0 else 'square_mod',
                'limbs': n, 'top': top, 'baseline_ns': baseline, 'previous_ns': previous, 'candidate_ns': candidate,
                'gmp_ns': gmp, 'candidate_over_baseline': candidate / baseline, 'candidate_over_previous': candidate / previous,
                'candidate_over_gmp': candidate / gmp,
                'principal_workload': n in primary and top == 63})
    key_failures = [row for row in comparisons if row['candidate_over_gmp'] > 1.2]
    primary_failures = [row for row in comparisons if row['principal_workload'] and row['candidate_over_gmp'] > 1.0]
    records.append({'tag': tag, 'raw_sha256': sha(raw), 'binding_sha256': sha(binding_path),
        'measurements_sha256': sha(measured_path), 'samples': len(samples),
        'minimum_recorded_ns': min(int(row['ns']) for row in samples),
        'performance_status': 'target_not_met' if key_failures or primary_failures else 'registered_library_target_met',
        'key_gmp_failures': len(key_failures), 'primary_gmp_failures': len(primary_failures),
        'regressions_vs_baseline': sum(row['candidate_over_baseline'] > 1 for row in comparisons),
        'regressions_vs_previous': sum(row['candidate_over_previous'] > 1 for row in comparisons),
        'comparisons': comparisons})

summary = {'status': 'pass', 'scope': 'Complete raw-data audit; status pass is not a performance acceptance claim',
    'candidate': 'isolated single-pass signed Toom-4 evaluation; frozen interpolation-fusion candidate and public e22 dispatch are controls; the fusion control previously missed the registered GMP target',
    'baseline_commit': verification['baseline_commit'],
    'verification_report_sha256': sha(verification_path),
    'confirmation_window_sha256': sha(window_path),
    'performance_target_sha256': sha(target_path),
    'analysis_script_sha256': sha(Path(__file__)),
    'libraries': verification['libraries'],
    'benchmark_binary_sha256': verification['benchmark_binary_sha256'],
    'benchmark_source_sha256': verification['benchmark_source_sha256'],
    'performance_status': 'target_not_met' if any(run['performance_status'] == 'target_not_met' for run in records) else 'registered_library_target_met',
    'solver_performance_acceptance': 'not_evaluated', 'runs': records}
(OUT / 'performance-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({key: summary[key] for key in ['status', 'performance_status', 'baseline_commit']}))
for run in records:
    print(json.dumps({key: run[key] for key in ['tag', 'samples', 'minimum_recorded_ns', 'key_gmp_failures', 'primary_gmp_failures', 'regressions_vs_baseline']}))
    for row in run['comparisons']:
        if row['principal_workload']:
            print(json.dumps(row))

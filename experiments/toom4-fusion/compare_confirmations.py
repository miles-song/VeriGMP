"""Keep every comparison and check the registered four-mode recording order."""
from pathlib import Path
import csv
import hashlib
import json

OUT = Path(__file__).resolve().parent / 'evidence'
summary_path = OUT/'performance-summary.json'
summary = json.loads(summary_path.read_text())
assert summary['status'] == 'pass'
runs = [{(row['operation'], row['limbs'], row['top']): row for row in run['comparisons']}
        for run in summary['runs']]
assert len(runs) == 2 and set(runs[0]) == set(runs[1]) and len(runs[0]) == 52
orders = {}
for run in summary['runs']:
    raw = OUT/run['tag']/'benchmark.csv'
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == run['raw_sha256']
    groups = {}
    for row in csv.DictReader(raw.read_text().splitlines()):
        key = tuple(int(row[name]) for name in ['operation', 'limbs', 'top'])
        groups.setdefault(key, []).append(row)
    expected = [((j+rep) % 4, rep) for rep in range(7) for j in range(4)]
    for group in groups.values():
        assert [(int(row['mode']), int(row['repetition'])) for row in group] == expected
    orders[run['tag']] = {'all_52_groups_follow_registered_rotation': len(groups) == 52,
        'minimum_recorded_ns': run['minimum_recorded_ns'], 'samples': run['samples']}


def select(field, regress):
    return [{'operation': key[0], 'limbs': key[1], 'top': key[2],
             'ratios': [run[key][field] for run in runs]}
            for key in runs[0] if all((run[key][field] > 1 if regress else run[key][field] <= 1)
                                     for run in runs)]


record = {
    'status': 'complete_comparison_not_acceptance',
    'analysis_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'summary_sha256': hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    'recording_order': orders,
    'consistent_regressions_vs_e22': select('candidate_over_baseline', True),
    'consistent_regressions_vs_previous': select('candidate_over_previous', True),
    'consistent_improvements_vs_previous': select('candidate_over_previous', False),
    'confirmation_window_retries': 0,
    'result_based_reruns': 0,
    'batch_retry_boundary': 'The preregistered minimum-10ms rule may double per-mode iterations; this is not an additional confirmation run.',
    'performance_status': summary['performance_status']
}
(OUT/'performance-comparison.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({key: len(record[key]) for key in ['consistent_regressions_vs_e22',
    'consistent_regressions_vs_previous', 'consistent_improvements_vs_previous']}))

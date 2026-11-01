from pathlib import Path
import hashlib
import json

STAGE = Path(__file__).resolve().parent
EVIDENCE = STAGE / 'evidence'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

verification = EVIDENCE / 'verification.json'
target_path = STAGE / 'baseline/native/performance-target.json'
target = json.loads(target_path.read_text())
ops = {0: 'mul_mod', 1: 'square_mod'}
registered = {(op, n, top) for op in [0, 1] for n, top in target['key_shapes']['shapes']}
summary = {'status': 'running', 'verification_report_sha256': sha(verification),
           'performance_target_sha256': sha(target_path), 'runs': {}}
all_rows = []
for tag in ['default1', 'dense1', 'default2', 'dense2']:
    binding_path = EVIDENCE / (tag + '-binding.json')
    binding = json.loads(binding_path.read_text())
    report_path = EVIDENCE / tag / 'measurements.json'
    report = json.loads(report_path.read_text())
    if (binding['status'] != 'pass' or report['status'] != 'pass'
        or binding['verification_report_sha256'] != sha(verification)
        or binding['measurements_sha256'] != sha(report_path)
        or binding['raw_sha256'] != sha(EVIDENCE / tag / 'benchmark.csv')):
        raise RuntimeError('Unbound measurement: ' + tag)
    rows = report['measurements']
    entry = {'measurement_sha256': sha(report_path), 'binding_sha256': sha(binding_path),
             'raw_sha256': binding['raw_sha256'], 'samples': report['samples'],
             'minimum_observed_batch_ns': report['minimum_observed_batch_ns'],
             'all_measurements': rows,
             'all_observed_regressions_vs_baseline': [r for r in rows if r['candidate_over_baseline'] > 1]}
    if tag.startswith('default'):
        if {(r['operation'], r['limbs'], r['top']) for r in rows} != registered:
            raise RuntimeError('Incomplete registered shape coverage')
        entry['registered_shape_coverage_complete'] = True
        entry['principal_failures'] = [r for r in rows if r['limbs'] in target['principal_workloads']['limbs']
            and r['top'] == target['principal_workloads']['top']
            and r['candidate_over_gmp'] > target['principal_workloads']['per_workload_median_ratio_max']]
        entry['key_shape_failures'] = [r for r in rows if r['candidate_over_gmp'] > target['key_shapes']['per_shape_median_ratio_max']]
        entry['registered_target_status'] = 'target_not_met' if entry['principal_failures'] or entry['key_shape_failures'] else 'pass'
    summary['runs'][tag] = entry
    all_rows.extend((tag, row) for row in rows)

summary.update(status='pass', total_recorded_samples=sum(r['samples'] for r in summary['runs'].values()),
               minimum_observed_batch_ns=min(r['minimum_observed_batch_ns'] for r in summary['runs'].values()),
               registered_gmp_target_status='pass' if all(summary['runs'][tag]['registered_target_status'] == 'pass'
                   for tag in ['default1', 'default2']) else 'target_not_met',
               solver_backend_promotion=False)
dense = [row for tag, row in all_rows if tag.startswith('dense') and 9 <= row['limbs'] <= 64]
summary['selected_leaf_range_9_through_64'] = {
    'scope': 'Only the sampled dense sizes; no extrapolation beyond measured sizes or hardware',
    'candidate_over_baseline_min': min(r['candidate_over_baseline'] for r in dense),
    'candidate_over_baseline_max': max(r['candidate_over_baseline'] for r in dense),
    'both_runs_every_sampled_size_faster': all(r['candidate_over_baseline'] < 1 for r in dense),
}
(STAGE / 'performance-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
selected = {tag: [{'operation': ops[r['operation']], 'limbs': r['limbs'],
                  'candidate_over_baseline': r['candidate_over_baseline'], 'candidate_over_gmp': r['candidate_over_gmp']}
                 for r in run['all_measurements'] if r['limbs'] in [8, 9, 23, 64, 256, 512, 1024, 2048, 4096]]
            for tag, run in summary['runs'].items()}
print(json.dumps({'status': summary['status'], 'registered_gmp_target_status': summary['registered_gmp_target_status'],
                  'total_recorded_samples': summary['total_recorded_samples'],
                  'minimum_observed_batch_ns': summary['minimum_observed_batch_ns'],
                  'leaf': summary['selected_leaf_range_9_through_64'],
                  'selected_measurements': selected,
                  'performance_summary_sha256': sha(STAGE / 'performance-summary.json')}, indent=2))

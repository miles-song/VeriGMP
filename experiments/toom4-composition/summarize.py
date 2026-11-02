"""Report every confirmation shape and regression; keep feature and GMP gates separate."""
from pathlib import Path
import argparse
import json
import math
from common import now, sha, write


def summarize(stage):
    target = stage / 'decision.json'
    if target.exists():
        raise RuntimeError('Refusing to overwrite a final decision')
    selection = json.loads((stage / 'selection.json').read_text())
    selected = selection['selected']
    report = {'status': 'not_accepted', 'selected': selected, 'created_utc': now(),
        'selection_sha256': sha(stage / 'selection.json'), 'runs': {}, 'gmp_target_met': False,
        'independent_review': 'pending', 'exact_commit_ci': 'not_run'}
    passes = []
    small = []
    for tag in ['default1','default2']:
        path = stage / ('confirmation-' + tag) / 'measurement.json'
        measured = json.loads(path.read_text())
        if measured['status'] != 'pass':
            raise RuntimeError('Confirmation did not pass: ' + tag)
        rows = [row for row in measured['medians'] if row['mode'] == selected]
        affected = [row for row in rows if row['limbs'] >= 1024]
        principal = [row for row in affected if row['limbs'] in [1024,2048,4096] and row['top'] == 63]
        gm = math.exp(sum(math.log(row['over_baseline']) for row in affected)/len(affected))
        feature = gm <= 0.95 and all(row['over_baseline'] <= 0.99 for row in affected) and all(row['over_baseline'] <= 0.97 for row in principal)
        passes.append(feature)
        small.append({(row['operation'],row['limbs'],row['top']) for row in rows if row['limbs'] < 1024 and row['over_baseline'] > 1.05})
        report['runs'][tag] = {'measurement_sha256': sha(path), 'raw_sha256': measured['raw_sha256'],
            'affected_gate_pass': feature, 'affected_geomean_over_baseline': gm,
            'all_shapes': rows, 'all_baseline_regressions': [row for row in rows if row['over_baseline'] > 1],
            'affected_failures': [row for row in affected if row['over_baseline'] > 0.99],
            'gmp_principal_failures': [row for row in rows if row['limbs'] in [256,512,1024,2048,4096] and row['top'] == 63 and row['over_gmp'] > 1],
            'gmp_key_limit_failures': [row for row in rows if row['over_gmp'] > 1.2]}
    report['repeatable_below_cutoff_regressions_over_5_percent'] = [list(shape) for shape in sorted(small[0] & small[1])]
    if all(passes) and not small[0] & small[1]:
        report['status'] = 'feature_performance_pass_pending_independent_review_and_ci'
    report['gmp_target_met'] = all(not item['gmp_principal_failures'] and not item['gmp_key_limit_failures'] for item in report['runs'].values())
    write(target, report)
    print(json.dumps({key: report[key] for key in ['status','selected','gmp_target_met','repeatable_below_cutoff_regressions_over_5_percent']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    summarize(args.stage.resolve())

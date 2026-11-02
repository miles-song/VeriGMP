"""Apply the preregistered exploration rule once; never edit a selection in place."""
from pathlib import Path
import argparse
import json
import math
from common import now, sha, write


def select(stage, run):
    target = stage / 'selection.json'
    if target.exists():
        raise RuntimeError('Refusing to overwrite an immutable selection')
    policy = json.loads((stage / 'policy.json').read_text())
    path = stage / ('exploration-' + run) / 'measurement.json'
    measured = json.loads(path.read_text())
    if measured['status'] != 'pass' or measured['phase'] != 'exploration':
        raise RuntimeError('Exploration failed')
    report = {'status': 'no_candidate_eligible', 'selected': None, 'created_utc': now(),
        'policy_sha256': sha(stage / 'policy.json'), 'exploration_sha256': sha(path), 'candidates': {}}
    eligible = []
    for mode in policy['modes'][1:-1]:
        rows = [row for row in measured['medians'] if row['mode'] == mode and row['limbs'] >= 1024]
        principal = [row for row in rows if row['limbs'] in [1024,2048,4096] and row['top'] == 63]
        geomean_ns = math.exp(sum(math.log(row['ns']) for row in rows)/len(rows))
        passed = all(row['over_baseline'] <= 0.97 for row in principal) and all(row['over_baseline'] <= 0.99 for row in rows)
        report['candidates'][mode] = {'eligible': passed, 'geomean_ns': geomean_ns,
            'geomean_over_baseline': math.exp(sum(math.log(row['over_baseline']) for row in rows)/len(rows)),
            'affected_regressions': [row for row in rows if row['over_baseline'] > 1],
            'all_regressions': [row for row in measured['medians'] if row['mode'] == mode and row['over_baseline'] > 1],
            'failing_affected_shapes': [row for row in rows if row['over_baseline'] > 0.99],
            'failing_principal_shapes': [row for row in principal if row['over_baseline'] > 0.97]}
        if passed:
            eligible.append(mode)
    if eligible:
        fastest = min(report['candidates'][mode]['geomean_ns'] for mode in eligible)
        near = [mode for mode in eligible if report['candidates'][mode]['geomean_ns'] <= 1.02 * fastest]
        chosen = min(near, key=lambda mode: (len(policy['features'][mode]), policy['modes'].index(mode)))
        report.update(status='selected_pending_confirmation', selected=chosen,
            selected_features=policy['features'][chosen],
            selected_source_sha256=json.loads((stage / 'preparation.json').read_text())['variants'][chosen])
    write(target, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--run', default='exploration1')
    args = parser.parse_args()
    select(args.stage.resolve(), args.run)

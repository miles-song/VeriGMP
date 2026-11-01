#!/usr/bin/env python3
"""Evaluate the predeclared GMP target from accepted, immutable run evidence.

Library timing acceptance never authorizes replacing the solver backend: that
also requires representative, frozen solver traces and semantic compatibility.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def evaluate_samples(data, target):
    operations = {'mul_mod': 0, 'square_mod': 1}
    contract = target['measurement_contract']
    repetitions = contract['repetitions_per_shape']
    minimum_ns = contract['minimum_recorded_batch_ms'] * 1_000_000
    expected = {(operations[op], n, top, mode)
                for op in target['key_shapes']['operations']
                for n, top in target['key_shapes']['shapes'] for mode in (4, 5)}
    principal = {(operations[op], n, target['principal_workloads']['top'], mode)
                 for op in target['principal_workloads']['operations']
                 for n in target['principal_workloads']['limbs'] for mode in (4, 5)}
    if not expected or not principal or not principal <= expected:
        raise ValueError('Principal workloads must be included in nonempty registered shapes')
    groups = {}
    for row in csv.DictReader(io.StringIO(data.decode())):
        values = {k: int(v) for k, v in row.items()}
        key = tuple(values[k] for k in ('square', 'limbs', 'top', 'mode'))
        if key[-1] not in (4, 5):
            continue
        if key not in expected:
            raise ValueError(f'Unregistered benchmark group: {key}')
        if values['iterations'] <= 0 or values['ns'] < minimum_ns:
            raise ValueError(f'Insufficient measurement duration: {key}')
        groups.setdefault(key, []).append(values)
    if set(groups) != expected:
        raise ValueError('Missing registered workload or comparator')
    medians = {}
    for key, rows in groups.items():
        if len(rows) != repetitions or {r['repetition'] for r in rows} != set(range(repetitions)):
            raise ValueError(f'Missing or duplicate repetitions: {key}')
        if len({(r['threshold'], r['low_limit']) for r in rows}) != 1:
            raise ValueError(f'Mixed benchmark configurations: {key}')
        medians[key] = statistics.median(r['ns'] / r['iterations'] for r in rows)
    results = []
    for op in target['key_shapes']['operations']:
        for n, top in target['key_shapes']['shapes']:
            square = operations[op]
            gmp = medians[square, n, top, 4]
            actual = medians[square, n, top, 5]
            principal = (op in target['principal_workloads']['operations']
                         and n in target['principal_workloads']['limbs']
                         and top == target['principal_workloads']['top'])
            limit = (target['principal_workloads']['per_workload_median_ratio_max'] if principal
                     else target['key_shapes']['per_shape_median_ratio_max'])
            results.append({'operation': op, 'limbs': n, 'top': top,
                            'principal': principal, 'actual_ns_median': actual,
                            'gmp_ns_median': gmp, 'ratio': actual / gmp,
                            'limit': limit, 'passes': actual / gmp <= limit})
    return {'csv_sha256': digest(data), 'workloads': results,
            'all_registered_workloads_pass': all(r['passes'] for r in results)}


def accepted_run(csv_path, evidence_path, target, target_bytes):
    data = csv_path.read_bytes()
    evidence_bytes = evidence_path.read_bytes()
    evidence = json.loads(evidence_bytes)
    if evidence['status'] != 'pass' or evidence['toom']['status'] != 'pass':
        raise ValueError('Arithmetic verification is not accepted')
    if evidence['toom']['benchmark']['raw_csv_sha256'] != digest(data):
        raise ValueError('CSV does not match verified run evidence')
    if evidence['source_hashes_lf']['native/performance-target.json'] != digest(target_bytes.replace(b'\r\n', b'\n')):
        raise ValueError('Performance target was not part of the verified snapshot')
    checker = Path(__file__).read_bytes().replace(b'\r\n', b'\n')
    if evidence['source_hashes_lf']['scripts/check_performance_target.py'] != digest(checker):
        raise ValueError('Evaluator does not match the verified snapshot')
    result = evaluate_samples(data, target)
    result['evidence_sha256'] = digest(evidence_bytes)
    result['git'] = evidence['git']
    result['platform'] = evidence['toom']['benchmark']
    return result, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--confirmation-csv', type=Path)
    parser.add_argument('--confirmation-evidence', type=Path)
    parser.add_argument('--target', type=Path, default=ROOT / 'native/performance-target.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/performance-target.json')
    parser.add_argument('--require-library-target', action='store_true')
    args = parser.parse_args()
    report = {'status': 'running', 'backend_promotion_allowed': False,
              'solver_acceptance': 'pending representative trace and replacement checks'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report) + '\n')
    try:
        target_bytes = args.target.read_bytes(); target = json.loads(target_bytes)
        report['target_sha256'] = digest(target_bytes)
        primary, evidence = accepted_run(args.csv, args.evidence, target, target_bytes)
        report['runs'] = [primary]
        if bool(args.confirmation_csv) != bool(args.confirmation_evidence):
            raise ValueError('Confirmation needs both CSV and evidence')
        confirmed = args.confirmation_csv is not None
        if confirmed:
            confirmation, other = accepted_run(args.confirmation_csv, args.confirmation_evidence, target, target_bytes)
            if confirmation['csv_sha256'] == primary['csv_sha256']:
                raise ValueError('Confirmation must be a separate measurement')
            if evidence['source_hashes_lf'] != other['source_hashes_lf'] or evidence['actual_toolchain'] != other['actual_toolchain']:
                raise ValueError('Confirmation uses a different source or toolchain')
            for key in ('cpu_model', 'platform', 'pinned_cpu', 'seed', 'semantics'):
                if primary['platform'][key] != confirmation['platform'][key]:
                    raise ValueError(f'Confirmation context differs: {key}')
            if evidence['toom']['gmp_identity'] != other['toom']['gmp_identity']:
                raise ValueError('Confirmation uses a different GMP baseline')
            if primary['platform']['linked_library_sha256'] != confirmation['platform']['linked_library_sha256']:
                raise ValueError('Confirmation uses different linked-library builds')
            report['runs'].append(confirmation)
        passing = all(r['all_registered_workloads_pass'] for r in report['runs'])
        report['status'] = ('confirmed_library_pass' if confirmed else 'provisional_library_pass') if passing else 'target_not_met'
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.update(status='invalid_evidence', error=str(error))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'backend_promotion_allowed', 'error') if k in report}))
    if report['status'] == 'invalid_evidence':
        return 2
    return int(args.require_library_target and report['status'] != 'confirmed_library_pass')


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Enumerate retained scalar-product pairs and actual square-base loop visits."""
import argparse
from collections import Counter
import json
from pathlib import Path
from common import LABELS, checked_prepared, file_sha, write_json
from operations import PRIMARY, count, operation_rows, verify_anchors


def square_base_schedule(n):
    # Follow square_base::low's add_mul_word slices and its two-word diagonal
    # stride. No closed-form multiplication count is used in this enumeration.
    cross = []
    i = 1
    while i < n:
        width = i if i < n-i else n-i
        j = 0
        while j < width:
            cross.append((i, j))
            j += 1
        i += 1
    diagonal = []
    position = 0
    while position < n-1:
        diagonal.append((position//2, position//2))
        position += 2
    if n % 2 == 1:
        diagonal.append((n//2, n//2))
    return cross, diagonal


def schedule_fixtures():
    rows = []
    for n in range(1, 130):
        cross, diagonal = square_base_schedule(n)
        actual = cross + diagonal
        # Independently enumerate the unordered scalar pairs that can affect
        # the retained n limbs. Compare multiplicities, not just totals.
        expected = [(i, j) for i in range(n) for j in range(i+1) if i+j < n]
        if Counter(actual) != Counter(expected) or len(actual) != len(set(actual)):
            raise RuntimeError('square-base pair schedule mismatch: '+str(n))
        total = len(actual)
        if len(cross) != n*n//4 or len(diagonal) != (n+1)//2:
            raise RuntimeError('square-base closed-form mismatch: '+str(n))
        if 9 <= n <= 64:
            for label in LABELS:
                observed = count(2, n, label in ('double', 'both'), label in ('checks', 'both'))[0]
                if observed['base_low_square_calls'] != 1 or observed['base_word_multiplications'] != total:
                    raise RuntimeError('analytic square-base count mismatch: '+str(n)+'/'+label)
        rows.append(dict(n=n, cross_multiplications=len(cross),
                         diagonal_multiplications=len(diagonal), total_multiplications=total))
    anchors = {row['n']:row['total_multiplications'] for row in rows}
    if anchors[9] != 25 or anchors[64] != 1056:
        raise RuntimeError('odd/even anchor mismatch')
    # The superseded +n diagonal term must disagree with the actual schedule.
    rejected = [n for n in (9, 64) if n*n//4+n != anchors[n]]
    if rejected != [9, 64]:
        raise RuntimeError('incorrect diagonal-count mutation survived')
    return dict(status='pass', benchmark_executed=False, calibration_executed=False,
                basis='enumerated scalar pairs from square_base::low loop/slice schedule',
                independent_oracle='unordered pairs (i,j), j<=i and i+j<n, each exactly once',
                sizes=rows, analytic_leaf_cell_checks=56*4,
                rejected_plus_n_diagonal_mutation=rejected)


def validate_operation_report(report, prepared, shapes, anchors):
    if report['status'] != 'pass' or report['benchmark_run']:
        raise RuntimeError('operation receipt status mismatch')
    if report['rows'] != operation_rows(shapes):
        raise RuntimeError('exact 86-cell operation schedule mismatch')
    if tuple(report['primary_square_sizes']) != PRIMARY:
        raise RuntimeError('operation primary subset mismatch')
    if report['anchors'] != anchors:
        raise RuntimeError('operation source anchor binding mismatch')
    expected = {k:v['native_manifest_sha256'] for k,v in prepared['cells'].items()}
    if report['native_manifests'] != expected:
        raise RuntimeError('operation source identity mismatch')
    return schedule_fixtures()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--operations', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepared, data = checked_prepared(args.prepared)
    shapes = json.loads((prepared/'baseline/native/performance-target.json').read_text())['key_shapes']['shapes']
    report = json.loads(args.operations.read_text())
    fixture = validate_operation_report(report, data, shapes, verify_anchors(prepared))
    fixture.update(prepared_sha256=file_sha(prepared/'prepared.json'),
                   operation_counts_sha256=file_sha(args.operations))
    if args.output.exists():
        raise RuntimeError('use a fresh operation fixture receipt')
    write_json(args.output, fixture)
    print(json.dumps(dict(status='pass', sizes=129, analytic_leaf_cell_checks=224,
                         n9=25, n64=1056, operation_cells=len(report['rows'])), indent=2))


if __name__ == '__main__':
    main()

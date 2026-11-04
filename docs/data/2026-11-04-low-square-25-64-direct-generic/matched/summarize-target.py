#!/usr/bin/env python3
"""Validate and expose all registered default/GMP comparisons from retained raw data."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys


root=Path(sys.argv[1]).resolve()
output=Path(__file__).resolve().parent
target_path=root/'native/performance-target.json'
target=json.loads(target_path.read_text())
summary_path=output/'summary.json'
summary=json.loads(summary_path.read_text())
shapes=[tuple(shape) for shape in target['key_shapes']['shapes']]
operations=target['key_shapes']['operations']
principal=target['principal_workloads']
expected={(square,n,top,192,128,mode) for square,(n,top),mode in itertools.product(range(2),shapes,range(6))}
names=('square','limbs','top','threshold','low_limit','mode')
process_medians={'baseline':[],'candidate':[]}
for relative,expected_hash in summary['raw_sha256'].items():
    path=output/relative
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_hash:
        raise RuntimeError(f'Raw file changed: {relative}')
    groups={}
    for row in csv.DictReader(path.open()):
        groups.setdefault(tuple(int(row[name]) for name in names),[]).append(row)
    if set(groups)!=expected:
        raise RuntimeError(f'Incomplete or aliased benchmark groups: {relative}')
    medians={}
    for key,rows in groups.items():
        if len(rows)!=7 or {int(row['repetition']) for row in rows}!=set(range(7)):
            raise RuntimeError(f'Invalid repetitions: {relative}: {key}')
        if any(int(row['iterations'])<=0 or int(row['ns'])<10_000_000 for row in rows):
            raise RuntimeError(f'Invalid recorded batch: {relative}: {key}')
        medians[key]=statistics.median(int(row['ns'])/int(row['iterations']) for row in rows)
    role='baseline' if 'baseline' in relative else 'candidate'
    process_medians[role].append(medians)
if any(len(runs)!=4 for runs in process_medians.values()):
    raise RuntimeError('Expected four independent processes for each role')
pooled={role:{key:statistics.median(run[key] for run in runs) for key in expected}
    for role,runs in process_medians.items()}
comparisons=[]
for operation,(n,top) in itertools.product(operations,shapes):
    square={'mul_mod':0,'square_mod':1}[operation]
    is_principal=(operation in principal['operations'] and n in principal['limbs'] and top==principal['top'])
    limit=principal['per_workload_median_ratio_max'] if is_principal else target['key_shapes']['per_shape_median_ratio_max']
    comparison={'operation':operation,'limbs':n,'top':top,'principal':is_principal,'limit':limit}
    for role in ('baseline','candidate'):
        default=pooled[role][square,n,top,192,128,5]
        gmp=pooled[role][square,n,top,192,128,4]
        comparison[role]={'default_ns':default,'gmp_ns':gmp,'ratio':default/gmp,'passes':default/gmp<=limit}
    comparison['candidate_vs_baseline_delta_percent']=100*(comparison['candidate']['default_ns']/comparison['baseline']['default_ns']-1)
    comparisons.append(comparison)
official={(operation,n,top) for operation,(n,top) in itertools.product(operations,shapes)}
if len(comparisons)!=54 or {(row['operation'],row['limbs'],row['top']) for row in comparisons}!=official:
    raise RuntimeError('Registered target must have exactly 54 distinct official groups')
for role in ('baseline','candidate'):
    if sum(row[role]['passes'] for row in comparisons)!=summary[f'registered_target_{role}_passes']:
        raise RuntimeError(f'Published pass count mismatch: {role}')
    old_failures={(row['operation'],row['limbs'],row['top']):row['ratio']
        for row in summary[f'registered_target_{role}_failures']}
    failures={(row['operation'],row['limbs'],row['top']):row[role]['ratio']
        for row in comparisons if not row[role]['passes']}
    if set(failures)!=set(old_failures) or any(not math.isclose(ratio,old_failures[key],rel_tol=1e-13) for key,ratio in failures.items()):
        raise RuntimeError(f'Published failure ratios mismatch: {role}')
summary['registered_target']={'registry_source':'native/performance-target.json',
    'registry_sha256_lf':hashlib.sha256(target_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
    'operations':operations,'shapes':shapes,'principal_limbs':principal['limbs'],
    'default_mode':5,'gmp_mode':4,'comparison_count':len(comparisons),'comparisons':comparisons,
    'new_failures':[row for row in comparisons if row['baseline']['passes'] and not row['candidate']['passes']],
    'new_passes':[row for row in comparisons if not row['baseline']['passes'] and row['candidate']['passes']]}
summary_path.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:summary['registered_target'][key] for key in ('comparison_count','principal_limbs','new_failures','new_passes')},indent=2))

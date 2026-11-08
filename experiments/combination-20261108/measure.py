#!/usr/bin/env python3
"""Execute only in the prereviewed, explicitly granted quiet window."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
from common import *
from operations import cells, PRIMARY

_legacy_path = ROOT / 'experiments/arithmetic-precondition-checks-20261108/measure.py'
_spec = importlib.util.spec_from_file_location('combination_legacy_measure', _legacy_path)
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
invoke, record = _legacy.invoke, _legacy.record
SEED = 20261108


def sample_paths(index, repetition, phase):
    paths = list(LABELS)
    shift = (index + repetition) % 4
    paths = paths[shift:] + paths[:shift]
    if (repetition + phase) % 2:
        paths.reverse()
    paths.insert((index + repetition + phase) % 5, 'gmp')
    return paths


def ratios(medians):
    a,b,c,d = [medians[label] for label in LABELS]
    return dict(double_over_baseline=b/a,checks_over_baseline=c/a,both_over_baseline=d/a,
                both_over_double=d/b,both_over_checks=d/c,interaction=(d*a)/(b*c),
                **{label+'_over_gmp':medians[label]/medians['gmp'] for label in LABELS})


def decision(summaries):
    primary = [row for row in summaries if row['op']==2 and row['n'] in PRIMARY and row['top']==63]
    if len(summaries)!=86 or len(primary)!=11:
        raise RuntimeError('incomplete frozen decision matrix')
    geometric = lambda name: math.exp(statistics.mean(math.log(row['ratios'][name]) for row in primary))
    limits = dict(primary_both_baseline_geomean_max=0.98,primary_both_double_geomean_max=0.99,
                  all_cell_both_baseline_max=1.05,all_cell_both_double_max=1.05)
    actual = dict(primary_both_baseline_geomean=geometric('both_over_baseline'),
                  primary_both_double_geomean=geometric('both_over_double'),
                  all_cell_both_baseline_max=max(row['ratios']['both_over_baseline'] for row in summaries),
                  all_cell_both_double_max=max(row['ratios']['both_over_double'] for row in summaries))
    passed = all(actual[name] <= limit for name,limit in (
        ('primary_both_baseline_geomean',0.98),('primary_both_double_geomean',0.99),
        ('all_cell_both_baseline_max',1.05),('all_cell_both_double_max',1.05)))
    return dict(limits=limits,actual=actual,verdict='GO_THIS_RUN' if passed else 'NO-GO',
                historical_checked_recursion_verdict='NO-GO unchanged',
                final_acceptance='requires both independent complete runs and independent final review')


def validate_build(build_path, quiet_path, phase, cpu):
    build = json.loads(build_path.read_text())
    if build['status']!='static_pass' or build['seed']!=SEED or build['cell_count']!=86:
        raise RuntimeError('not a frozen static-passing matrix')
    # This record is written by the coordinating main agent after prereview.
    quiet = json.loads(quiet_path.read_text())
    required = dict(status='granted',phase=phase,cpu=cpu,build_sha256=file_sha(build_path),
                    independent_prereview='pass',known_heavy_jobs_quiescent=True)
    if any(quiet.get(k)!=v for k,v in required.items()):
        raise RuntimeError('quiet/prereview grant mismatch')
    if cpu not in os.sched_getaffinity(0):
        raise RuntimeError('requested CPU unavailable')
    files = {label:Path(build['binaries'][label]['path']) for label in LABELS}
    for label,path in files.items():
        if file_sha(path)!=build['binaries'][label]['sha256']:
            raise RuntimeError('frozen binary drift: '+label)
    for name,digest in build['inputs_sha256'].items():
        if file_sha(ROOT/name)!=digest:
            raise RuntimeError('frozen harness/protocol drift: '+name)
    return build,files,quiet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',required=True,type=Path)
    parser.add_argument('--quiet-grant',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--phase',required=True,type=int,choices=(0,1))
    parser.add_argument('--cpu',required=True,type=int)
    args=parser.parse_args()
    build_path=args.build.resolve();quiet_path=args.quiet_grant.resolve()
    # Validate prerequisites before creating a measurement run or launching anything.
    build,files,quiet=validate_build(build_path,quiet_path,args.phase,args.cpu)
    out=args.output.resolve()
    if out.is_relative_to(ROOT):
        raise RuntimeError('keep raw measurements outside repository')
    out.mkdir(exist_ok=False,parents=True)
    report=dict(status='running',run_id=args.run_id,phase=args.phase,seed=SEED,cpu=args.cpu,
                build_sha256=file_sha(build_path),build=build,quiet_grant=quiet,
                quiet_grant_sha256=file_sha(quiet_path),minimum_sample_ns=10_000_000,
                repetitions=7,summaries=[])
    raw=(out/'raw.jsonl').open('w')
    def call(cell,path,count,kind,repetition):
        op,n,top=cell
        binary=files['baseline' if path=='gmp' else path]
        command=[str(binary),str(op),str(n),str(top),str(SEED),str(path=='gmp').lower(),str(count),'registered']
        return invoke(command,raw,dict(op=op,n=n,top=top,path=path,kind=kind,repetition=repetition),args.cpu)
    try:
        for index,cell in enumerate(cells(build['key_shapes'])):
            counts={};groups={path:[] for path in (*LABELS,'gmp')};checksums=set()
            for path in groups:
                row=call(cell,path,0,'calibration',-1)
                if row['iterations']<=0 or row['ns']<=0:
                    raise RuntimeError('invalid calibration count/duration')
                counts[path]=row['iterations'];checksums.add(row['checksum'])
            for repetition in range(7):
                for path in sample_paths(index,repetition,args.phase):
                    row=call(cell,path,counts[path],'sample',repetition)
                    checksums.add(row['checksum'])
                    while row['ns']<10_000_000:
                        counts[path]*=2
                        row=call(cell,path,counts[path],'sample-retry',repetition)
                        checksums.add(row['checksum'])
                    if row['iterations']!=counts[path]:
                        raise RuntimeError('sample iteration count mismatch')
                    groups[path].append(row['ns']/row['iterations'])
            if len(checksums)!=1:
                raise RuntimeError('four-cell/GMP exact result checksum mismatch')
            medians={path:statistics.median(values) for path,values in groups.items()}
            report['summaries'].append(dict(op=cell[0],n=cell[1],top=cell[2],
                                            median_ns=medians,ratios=ratios(medians)))
            write_json(out/'measurement.json',report)
        validate_build(build_path,quiet_path,args.phase,args.cpu)
        report.update(status='pass',decision=decision(report['summaries']))
    except BaseException as error:
        report.update(status='fail',failure=repr(error))
        raise
    finally:
        raw.close();report['raw_sha256']=file_sha(out/'raw.jsonl')
        write_json(out/'measurement.json',report)
    print(json.dumps(dict(status=report['status'],cells=len(report['summaries']),
                          decision=report['decision'],report_sha256=file_sha(out/'measurement.json')),indent=2))


if __name__=='__main__':
    main()

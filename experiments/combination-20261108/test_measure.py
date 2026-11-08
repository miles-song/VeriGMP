#!/usr/bin/env python3
"""Pure schedules/decisions and controlled process fixtures; never a benchmark."""
import argparse
import json
from pathlib import Path
import sys
from common import *
from measure import sample_paths, ratios, decision, invoke
from operations import cells


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(exist_ok=False)
    shapes=json.loads((ROOT/'native/performance-target.json').read_text())['key_shapes']['shapes']
    frozen=cells(shapes);assert len(frozen)==86
    schedules=[]
    for phase in (0,1):
        for index in range(86):
            for repetition in range(7):
                original=list(LABELS);shift=(index+repetition)%4
                expected=original[shift:]+original[:shift]
                if (repetition+phase)%2:
                    expected=expected[::-1]
                expected.insert((index+repetition+phase)%5,'gmp')
                actual=sample_paths(index,repetition,phase)
                assert actual==expected and sorted(actual)==sorted((*LABELS,'gmp'))
                schedules.append(dict(phase=phase,cell=index,repetition=repetition,paths=actual))
    assert len(schedules)==1204
    # Synthetic ratios straddle every frozen acceptance threshold.
    def summaries(medians):
        return [dict(op=op,n=n,top=top,ratios=ratios(medians)) for op,n,top in frozen]
    good=dict(baseline=100.,double=98.,checks=100.,both=96.,gmp=90.)
    assert decision(summaries(good))['verdict']=='GO_THIS_RUN'
    assert decision(summaries(dict(good,both=98.)))['verdict']=='NO-GO'
    assert decision(summaries(dict(good,both=99.)))['verdict']=='NO-GO'
    for field in ('both_over_baseline','both_over_double'):
        rows=summaries(good);rows[0]['ratios'][field]=1.0500000001
        assert decision(rows)['verdict']=='NO-GO'
    incomplete=summaries(good)[:-1]
    try:decision(incomplete)
    except RuntimeError:pass
    else:raise AssertionError('incomplete matrix accepted')
    process_cases=[]
    cases=(('success','print(\'{"iterations":1,"ns":20000000,"checksum":7}\')',None),
           ('nonzero','import sys; print("retained"); sys.exit(3)',RuntimeError),
           ('timeout','import time; print("before-timeout",flush=True); time.sleep(1)',TimeoutError),
           ('bad-json','print("not-json")',ValueError))
    for name,source,error in cases:
        path=out/(name+'.jsonl')
        with path.open('w') as raw:
            try:
                invoke([sys.executable,'-c',source],raw,dict(fixture=name),None,timeout=.05 if name=='timeout' else 5)
            except BaseException as actual:
                if error is None or not isinstance(actual,error):raise
            else:
                if error is not None:raise AssertionError('fixture did not fail')
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        assert rows[0]['record']=='invocation' and rows[1]['record']=='outcome'
        assert 'stdout_hex' in rows[1] and 'stderr_hex' in rows[1]
        process_cases.append(dict(name=name,records=len(rows),sha256=file_sha(path)))
    write_json(out/'schedules.json',schedules)
    write_json(out/'verification.json',dict(status='pass',benchmark_executed=False,
        ordering_cases=len(schedules),synthetic_gate_checks=6,process_cases=process_cases,
        schedules_sha256=file_sha(out/'schedules.json')))
    print(json.dumps(dict(status='pass',ordering_cases=len(schedules),process_cases=4,benchmark_executed=False)))


if __name__=='__main__':
    main()

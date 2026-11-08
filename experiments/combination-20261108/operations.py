#!/usr/bin/env python3
"""Untimed source-schedule counts; these are analytic, not instrumented runtime."""
import argparse
from collections import Counter
import json
from pathlib import Path
from common import *

FULL_SIZES = (1,2,7,8,9,23,24,25,31,32,33,47,48,49,63,64,65,127,128,129,
              191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096)
PRIMARY = (255,256,257,511,512,513,1023,1024,1025,2048,4096)


def cells(shapes):
    return [(0,n,64) for n in FULL_SIZES] + [(op,n,top) for op in (1,2) for n,top in shapes]


def count(op, n, double, checks):
    result = Counter()
    lengths = Counter()
    def base_full(m):
        result['base_full_calls'] += 1
        result['base_word_multiplications'] += m*m
    def base_low(m, square=False):
        result['base_low_square_calls' if square else 'base_low_product_calls'] += 1
        if square:
            result['base_word_multiplications'] += (m*m)//4 + m
        else:
            result['base_word_multiplications'] += m*(m+1)//2
    def full(m, inner=False):
        result['full_worker_calls' if inner else 'full_public_calls'] += 1
        lengths['worker:' + str(m) if inner else 'public:' + str(m)] += 1
        if m <= 24:
            base_full(m)
        elif checks and not inner:
            full(m, True)
        else:
            result['karatsuba_product_nodes'] += 1
            h = m//2
            k = m-h
            for child in (k,h,k):
                full(child, checks)
    def square(m):
        result['square_full_calls'] += 1
        if m <= 24:
            if m < 8:
                base_full(m)
            else:
                result['base_full_square_calls'] += 1
                result['base_word_multiplications'] += m*(m+1)//2
        else:
            h = m//2
            k = m-h
            for child in (k,h,k):
                square(child)
    def toom(m, sqr=False):
        result['toom_square_calls' if sqr else 'toom_product_calls'] += 1
        if m <= 192:
            if sqr:
                square(m)
            else:
                full(m)
        else:
            k = (m+2)//3
            for child in (k,m-2*k,k+1,k+1,k+1):
                toom(child, sqr)
    def low(m, kind, limit, mode):
        result[{'fast':'fast_low_calls','toom':'toom_low_calls','square':'square_low_calls'}[kind]] += 1
        if m <= limit:
            base_low(m, kind == 'square' and m >= 9)
            return
        h = (9*m)//40 if mode == 2 else (11*m)//36 if mode == 1 else m//2
        k = m-h
        result['low_copy_word_visits'] += m
        if kind == 'fast':
            full(k)
        else:
            toom(k, kind == 'square')
        if kind == 'square':
            low(h, 'toom', limit, mode)
            result['square_correction_word_visits'] += h if double else 2*h
            result['square_correction_passes'] += 1 if double else 2
            result['doubled_correction_sites'] += 1
        else:
            low(h, kind, limit, mode)
            low(h, kind, limit, mode)
            result['product_correction_word_visits'] += 2*h
    if op == 0:
        full(n)
    elif op == 1:
        if n < 512:
            low(n, 'fast', 64, 1)
        else:
            low(n, 'toom', 128, 2)
    elif op == 2:
        low(n, 'square', 64, 1)
    else:
        raise ValueError('operation')
    # Four public assert! statements (six Boolean facts) per full entry.
    result['full_public_assert_statements'] = 4*result['full_public_calls']
    return dict(sorted(result.items())), dict(sorted(lengths.items()))


def verify_anchors(prepared):
    anchors = {
        'native/verified/arithmetic.rs': ['if a.len()<512', 'modular(dst,a,b,scratch,top,192,128,2)',
                                          'square_low::low(dst,a,scratch,192,64,1)'],
        'native/verified/fast_multiply.rs': ['if n<=threshold {base_full(dst,a,b);return;}',
                                             'modular(dst,a,b,scratch,top,24,64,true)',
                                             'let h=n/2;', 'let k=n-h;'],
        'native/verified/toom_multiply.rs': ['if n<=threshold {fast_multiply::full(dst,a,b,scratch,24);return;}',
                                             'let k=n/3+if n%3==0{0}else{1};let m=k+1;',
                                             'full(&mut p0[..2*k],a0,b0,work,threshold)',
                                             'full(&mut p4[..2*h],a2,b2,work,threshold)',
                                             'full(p1,ax,bx,work,threshold)', 'full(pm,ax,bx,work,threshold)',
                                             'full(p2,ax,bx,work,threshold)'],
        'native/verified/square_low.rs': ['if n<=low_limit', 'if n<9', 'crate::square_base::low(dst,a)',
                                          'toom_square::full(product,&a[..k],work,threshold)',
                                          'toom_low::low(temp,&a[k..],&b[..h],work,threshold,low_limit,split_mode)'],
        'native/verified/toom_low.rs': ['if n<=low_limit {fast_multiply::base_low(dst,a,b);return;}',
                                       'toom_multiply::full(product,&a[..k],&b[..k],work,threshold)']}
    checked = []
    for label in LABELS:
        for name, strings in anchors.items():
            text = (prepared / label / name).read_text()
            for string in strings:
                if string not in text:
                    raise RuntimeError('source schedule anchor missing: ' + label + '/' + string)
            checked.append(dict(cell=label, source=name, sha256=file_sha(prepared / label / name), anchors=strings))
    return checked


def generate(prepared, data, output):
    shapes = json.loads((prepared / 'baseline/native/performance-target.json').read_text())['key_shapes']['shapes']
    rows = []
    for op,n,top in cells(shapes):
        counts = {}
        for label in LABELS:
            visits, lengths = count(op,n,label in ('double','both'),label in ('checks','both'))
            counts[label] = dict(visits=visits, full_call_lengths=lengths)
        both = counts['both']['visits']
        reachable = both.get('doubled_correction_sites',0)>0 and both.get('full_worker_calls',0)>0
        if op==2 and (n in PRIMARY) != reachable:
            raise RuntimeError('registered intersection drift')
        multiplies = {row['visits']['base_word_multiplications'] for row in counts.values()}
        if len(multiplies)!=1:
            raise RuntimeError('arithmetic multiplication count changed')
        rows.append(dict(op=op,n=n,top=top,both_factors_reached=reachable,cells=counts))
    report = dict(status='pass', benchmark_run=False, basis='analytic source-control schedule; no dynamic instrumentation',
                  omitted=['evaluation/interpolation operations','data-dependent carry/comparison branches',
                           'machine instructions','cache misses','whole-program peak space'],
                  anchors=verify_anchors(prepared), prepared_sha256=file_sha(prepared/'prepared.json'),
                  primary_square_sizes=PRIMARY, rows=rows,
                  native_manifests={k:v['native_manifest_sha256'] for k,v in data['cells'].items()})
    write_json(output, report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    prepared,data=checked_prepared(args.prepared)
    if args.output.exists():
        raise RuntimeError('use fresh operation receipt')
    report=generate(prepared,data,args.output)
    print(json.dumps(dict(status='pass',cells=len(report['rows']),primary=PRIMARY),indent=2))


if __name__ == '__main__':
    main()

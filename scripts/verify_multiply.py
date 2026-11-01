"""Truncated product: independent integers, semantic mutants and native timing.

GMP is an unverified experimental baseline, never part of the production proof.
"""
import csv
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
from verify_limbs import normalized_function

SEED = 20261103
BENCH_SEED = 16438731
MAX = (1 << 64) - 1
SHAPES = [(1,63),(1,64),(2,1),(2,63),(2,64),(4,63),(8,63),(16,63),
          (32,63),(64,63),(128,63),(256,63),(512,63),(1024,63)]


def integer(words):
    return int.from_bytes(b''.join(x.to_bytes(8, 'little') for x in words), 'little')


def words(value, n):
    return [(value >> (64*i)) & MAX for i in range(n)]


def cases():
    rng = random.Random(SEED)
    rows, gmp_rows = [], []
    def add(op, args, expected):
        rows.append((' '.join([op, *map(str, args)]), ' '.join(map(str, expected))))
    edge = [0,1,2,(1<<63)-1,1<<63,MAX-1,MAX]
    for a,b,acc,carry in itertools.chain(itertools.product(edge,repeat=4),
            (tuple(rng.getrandbits(64) for _ in range(4)) for _ in range(2000))):
        exact = a*b+acc+carry
        add('mac', [a,b,acc,carry], [exact & MAX, exact >> 64])

    def product(a,b,top):
        n = len(a)
        initial = [rng.getrandbits(64) for _ in range(n)]
        exact = integer(a)*integer(b)
        expected = words(exact % (1 << (64*(n-1)+top)), n)
        add('mul', [top,*initial,*a,*b], expected)
        add('mul', [top,*initial,*b,*a], expected)
        add('low', [top,*initial,*a,*b], words(exact,n))
        add('square', [top,*a], words(integer(a)**2 % (1 << (64*(n-1)+top)),n))
        gmp_rows.append((' '.join(map(str,[n,top,*a,*b])), ' '.join(map(str,expected))))

    add('low',[64],[])
    for n in (1,2,3,4,7,8,16,31,32,64,127,256,1024):
        tops = range(1,65) if n <= 4 else (1,7,31,63,64)
        for top in tops:
            for a,b in [([0]*n,[MAX]*n),([MAX]*n,[MAX]*n),([1]+[0]*(n-1),[MAX]*n)]:
                product(a,b,top)
            for _ in range(12 if n<=32 else 3):
                product([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(64) for _ in range(n)],top)
    # Every impulse pair, including just inside/outside the discarded boundary.
    for n in range(1,10):
        for i in range(n):
            for j in range(n):
                a,b = [0]*n,[0]*n
                a[i],b[j] = MAX,MAX
                product(a,b,63)
    for n in (0,1,2,3,8,31,64,257):
        for offset in range(n+1):
            a = [rng.getrandbits(64) for _ in range(n)]
            b = [rng.getrandbits(64) for _ in range(n)]
            word = MAX if offset%2 else rng.getrandbits(64)
            exact = integer(a)+word*(1 << (64*offset))*integer(b)
            add('row',[offset,word,*a,*b],words(exact,n))
        for extra in (0,1,7):
            a = [MAX]*n
            b = [rng.getrandbits(64) for _ in range(n+extra)]
            exact = integer(a)+MAX*integer(b[:n])
            add('word',[n,MAX,*a,*b],[exact >> (64*n),*words(exact,n)])
    # Explicit previous user-facing example: (2^65-1)*3 mod 2^65.
    product([MAX,1],[3,0],1)
    return rows,gmp_rows


def check_multiply(snapshot, verifier, env, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {'status':'running','scope':'Truncated schoolbook modular multiplication basecase',
              'complete_library_refined':False,'fast_multiplication_backend_complete':False}
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def run(command, log=None, timeout=180, **kwargs):
        result = subprocess.run([str(x) for x in command], cwd=snapshot, env=env,
                                capture_output=True,text=True,timeout=timeout,**kwargs)
        text = result.stdout+result.stderr
        if log: (output/log).write_text(text,encoding='utf-8')
        return result,text
    def compile(source,binary,log,*flags):
        result,text = run([verifier,snapshot/source,'--compile','-O',*flags,'-o',binary],log)
        match = re.search(r'verification results:: (\d+) verified, 0 errors',text)
        if result.returncode or not match: raise RuntimeError(f'Verus compile failed: {source}')
        return int(match[1])
    def check_output(binary,rows):
        before = digest(binary)
        input_text = '\n'.join(row[0] for row in rows)+'\n'
        result,_ = run([binary],input=input_text)
        expected = [row[1] for row in rows]
        if result.returncode or result.stdout.splitlines()!=expected:
            actual = result.stdout.splitlines()
            bad = next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
            raise RuntimeError(f'Oracle mismatch: {binary.name}, first mismatch {bad}, exit {result.returncode}')
        if digest(binary)!=before: raise RuntimeError('Executed binary changed')
        return {'cases':len(rows),'binary_sha256':before,
                'input_sha256':hashlib.sha256(input_text.encode()).hexdigest(),
                'output_sha256':hashlib.sha256(result.stdout.encode()).hexdigest()}
    try:
        binary = snapshot/'multiply-native'
        report['verification_items_including_imports'] = compile('native/multiply_runner.rs',binary,'proof.log')
        rows,gmp_rows = cases()
        report['oracle'] = dict(check_output(binary,rows),seed=SEED,max_limbs=1024)
        invalid = ['mul 0 1 2 3','mul 65 1 2 3','mul 1','badshape',
                   'row 2 1 2 3','word 2 1 2 3 4']
        for i,command in enumerate(invalid):
            result,_ = run([binary],f'invalid-{i}.log',input=command+'\n')
            if result.returncode==0 or result.stdout.strip(): raise RuntimeError(f'Invalid domain accepted: {command}')
        report['invalid_domains_rejected'] = len(invalid)

        source = snapshot/'native/verified/multiply.rs'
        original = source.read_bytes()
        report['mutations'] = []
        try:
            for name,before,after in (
                ('drop_mac_carry','+ (acc as u128) + (carry as u128);','+ (acc as u128);'),
                ('drop_row_carry','carry = high;','carry = 0;'),
                ('wrong_row_offset','&mut dst[offset..]','&mut dst[..]'),
                ('skip_zeroing','dst[z] = 0;','// destination deliberately left unchanged'),
                ('omit_cross_terms','while i < n','while i + 1 < n'),
                ('skip_top_mask','pow2::normalize_top(dst, top);','// top mask deliberately omitted'),
            ):
                text = original.decode()
                if text.count(before)!=1: raise RuntimeError(f'Mutation anchor: {name}')
                source.write_text(text.replace(before,after),encoding='utf-8')
                result,log = run([verifier,snapshot/'native/multiply_runner.rs'],name+'.log')
                detected = (result.returncode!=0
                    and re.search(r'verification results:: \d+ verified, [1-9]\d* errors',log)
                    and any(s in log for s in ('invariant not satisfied','assertion failed','postcondition not satisfied','requires not satisfied'))
                    and not any(s in log.lower() for s in ('timed out','resource limit','unexpected token')))
                report['mutations'].append({'name':name,'rejected_by_proof':bool(detected)})
                if not detected: raise RuntimeError(f'Mutation not semantically rejected: {name}')
        finally: source.write_bytes(original)

        assembly_path = snapshot/'multiply-codegen.s'
        compile('native/multiply_codegen.rs',assembly_path,'codegen.log','--emit=asm')
        assembly = assembly_path.read_text()
        if not re.search(r'(?m)^verified_mac\s*=\s*ordinary_mac$',assembly):
            raise RuntimeError('MAC code is not shared by verified/ordinary exports')
        comparisons = {}
        for name in ('word','row','low','mul'):
            verified = normalized_function(assembly,'verified_'+name)
            ordinary = normalized_function(assembly,'ordinary_'+name)
            text = '\n'.join(verified)
            if any(s in text for s in ('__rust_alloc','__rust_realloc','malloc','memcpy','memmove','panic_bounds_check')):
                raise RuntimeError(f'Unexpected allocation, copying or per-element bounds check in {name}')
            if any(re.match(r'i?div[bwlq]?\s',line) or re.search(r'__(u?div|u?mod)ti3',line) for line in verified):
                raise RuntimeError(f'General division in {name}')
            for line in verified:
                if re.match(r'callq?\s',line) and not ('memset@GOTPCREL' in line or re.search(r'core\w*panicking\w*5panic@GOTPCREL',line)):
                    raise RuntimeError(f'Uninspected out-of-line call in {name}: {line}')
                if re.match(r'jmp\s',line) and not re.match(r'jmp\s+BLOCK_\d+$',line):
                    raise RuntimeError(f'Uninspected tail call in {name}: {line}')
            comparisons[name] = {'normalized_equal':verified==ordinary,'verified':verified,'ordinary':ordinary}
        (output/'codegen-comparison.json').write_text(json.dumps(comparisons,indent=2)+'\n')
        (output/'multiply-codegen.s').write_text(assembly)
        report['codegen'] = {'mac_exact_alias':True,'normalized_equal':[k for k,v in comparisons.items() if v['normalized_equal']],
            'no_allocator_copy_division_or_element_bounds_panic_in_verified_exports':True,
            'verified_exports_out_of_line_calls':'Only memset and entry-assertion panic; no hidden arithmetic helper',
            'memset_allowed':'Necessary output initialization; included in timing',
            'assembly_sha256':digest(assembly_path),
            'comparison_scope':'Per-export instruction inspection; ordinary iterator/control-flow differences retained, not normalized away'}

        gmp = snapshot/'gmp-multiply'
        command = ['c++','-O3','-std=c++17',snapshot/'native/controls/gmp_multiply.cpp','-lgmp','-o',gmp]
        result,log = run(command,'gmp-build.log')
        if result.returncode: raise RuntimeError('GMP comparator build failed: install libgmp-dev and c++')
        result,version = run([gmp,'--version'],'gmp-version.log')
        if result.returncode: raise RuntimeError('Cannot read GMP version')
        result,compiler = run(['c++','--version'],'gmp-compiler.log')
        if result.returncode: raise RuntimeError('Cannot identify comparator compiler')
        result,linked = run(['ldd',gmp],'gmp-linked-libraries.log')
        if result.returncode: raise RuntimeError('Cannot identify GMP library')
        libraries = re.findall(r'=> (\S+) \(',linked)
        report['gmp'] = {'oracle':check_output(gmp,gmp_rows),'version':version.strip(),
            'compiler':compiler,'flags':['-O3','-std=c++17'],'library_sha256':{p:digest(Path(p)) for p in libraries},
            'scope':'Unverified comparator only; full 2n-limb product plus low-n copy and mask, with preallocated output/scratch'}

        bench = snapshot/'multiply-bench'
        compile('native/multiply_bench.rs',bench,'bench-build.log')
        bench_hash = digest(bench)
        cpu = min(os.sched_getaffinity(0))
        affinity = lambda: os.sched_setaffinity(0,{cpu})
        result,_ = run([bench,str(BENCH_SEED)],'benchmark.csv',preexec_fn=affinity)
        if result.returncode or digest(bench)!=bench_hash: raise RuntimeError('Rust benchmark failed/changed')
        samples = list(csv.DictReader(io.StringIO(result.stdout)))
        result,_ = run([gmp,'--bench',str(BENCH_SEED)],'gmp-benchmark.csv',preexec_fn=affinity)
        if result.returncode or digest(gmp)!=report['gmp']['oracle']['binary_sha256']:
            raise RuntimeError('GMP benchmark failed/changed')
        gmp_samples = list(csv.DictReader(io.StringIO(result.stdout)))
        if len(samples)!=98 or len(gmp_samples)!=98: raise RuntimeError('Incomplete benchmark')
        summaries = []
        for n,top in SHAPES:
            group = [s for s in samples if (int(s['limbs']),int(s['top']))==(n,top)]
            other = [s for s in gmp_samples if (int(s['limbs']),int(s['top']))==(n,top)]
            if len(group)!=7 or len(other)!=7: raise RuntimeError('Missing repetitions')
            v = [int(s['verified_ns'])/int(s['iterations']) for s in group]
            o = [int(s['ordinary_ns'])/int(s['iterations']) for s in group]
            g = [int(s['gmp_ns'])/int(s['iterations']) for s in other]
            summaries.append({'limbs':n,'top':top,'precision_bits':64*(n-1)+top,
                'verified_ns_per_product_median':statistics.median(v),
                'ordinary_ns_per_product_median':statistics.median(o),
                'paired_verified_over_ordinary_median':statistics.median(x/y for x,y in zip(v,o)),
                'gmp_ns_per_product_median':statistics.median(g),
                'verified_over_gmp_medians':statistics.median(v)/statistics.median(g)})
        model = next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                     if line.startswith('model name')),'unknown')
        report['benchmark'] = {'compiler_flags':['-O'],'platform':platform.platform(),'cpu_model':model,
            'pinned_cpu':cpu,'runtime_seed':BENCH_SEED,'repetitions':7,'binary_sha256':bench_hash,
            'timing_is_observational':True,'includes':'Required output zeroing, product, mask, calls and black_box; caller allocation/input setup/I/O excluded',
            'order':'Rust pairs alternate; GMP is a separate later process, not interleaved',
            'gmp_allocation_scope':'Caller output and 2n scratch preallocated; internal GMP allocation not instrumented',
            'summary':summaries}
        report['cost_scope'] = {'mac_count':'n*(n+1)/2; inner and outer ghost visit invariants checked',
            'initialization':'n zero writes; separate loop','word_time':'O(n^2)','extra_words':'O(1), excluding caller output',
            'fast_dispatch_threshold':'Not established; no automatic full-scale backend selection',
            'composed_cost_proved':False}
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='error',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

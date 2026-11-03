"""Evidence for Toom evaluation/interpolation, dedicated squares and row unrolling."""
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
from verify_multiply import integer, words, MAX

SEED = 20261101
BENCH_SEED = 16438731
LOW_SQUARE_SEED = 20261103
SHAPES = [(1,1),(1,64),(2,1),*((n,63) for n in (23,24,25,63,64,65,127,128,129,
    191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096))]
MODES = {0:'previous_karatsuba',1:'low_9_40',2:'low_11_36',3:'full_then_truncate',
         4:'gmp_full_then_truncate',5:'default'}


def cases():
    rng=random.Random(SEED); rows=[]
    def add(op,args,result):
        rows.append((' '.join([op,*map(str,args)]),' '.join(map(str,result))))
    for n in [0,1,2,MAX//12,MAX//12+1,MAX//10,MAX//10+1,MAX]:
        add('workspace',[n],[12*n if 0<n<=MAX//12 else 0,10*n if 0<n<=MAX//10 else 0])
    for n in [*range(17),23,24,25,63,64,65,128,512]:
        for m in [n,n+3]:
            for w in [0,1,3,1<<63,MAX]:
                for pattern in range(3):
                    a=[0 if pattern==0 else MAX if pattern==1 else rng.getrandbits(64) for _ in range(n)]
                    b=[MAX if pattern==1 else rng.getrandbits(64) for _ in range(m)]
                    total=integer(a)+w*integer(b[:n]);add('row',[w,n,m,*a,*b],[*words(total,n),total>>(64*n)])
        for divisor in [1,2,3,7,MAX]:
            a=[rng.getrandbits(64) for _ in range(n)]
            for a in [a,[MAX]*n]:
                q,rem=divmod(integer(a),divisor);add('divide',[divisor,*a],[*words(q,n),rem])
    sizes=[*range(1,42),63,64,65,95,96,97,127,128,129,191,192,193,255,256,257,
           383,384,385,511,512,513,1023,1024,1025,2047,2048,2049,4095,4096,4097]
    for n in sizes:
        pairs=[([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)]),
               ([MAX]*n,[MAX]*n),([0]*n,[MAX]*n)]
        if n in [25,26,27,193,513]:
            k=(n+2)//3;h=n-2*k
            signs=[[MAX]*k+[0]*(n-k),[0]*k+[MAX]*k+[0]*h,[MAX]*k+[MAX]*k+[0]*h]
            pairs+=list(itertools.product(signs,repeat=2))
        for a,b in pairs:
            product=integer(a)*integer(b);square=integer(a)**2
            if n<=257:
                add('squarebase',a,words(square,2*n))
            for threshold in [24,192]:
                add('full',[64,threshold,24,0,*a,*b],words(product,2*n))
                add('squarefull',[64,threshold,24,0,*a,*b],words(square,2*n))
            add('squarek',[64,8,24,0,*a,*b],words(square,2*n))
            for top in [1,63,64]:
                modulus=1<<(64*(n-1)+top)
                for split in range(3):
                    add('low',[top,24,24,split,*a,*b],words(product%modulus,n))
                    add('squarelow',[top,24,24,split,*a,*b],words(square%modulus,n))
                add('default',[top,192,128,2,*a,*b],words(product%modulus,n))
                add('square',[top,192,128,2,*a,*b],words(square%modulus,n))
                add('same',[top,192,128,2,*a,*b],words(square%modulus,n))
    for n in [1,25,513]:
        a=[MAX]*n;b=[rng.getrandbits(64) for _ in range(n)]
        for top in range(1,65):
            q=1<<(64*(n-1)+top)
            add('default',[top,192,128,2,*a,*b],words(integer(a)*integer(b)%q,n))
            add('square',[top,192,128,2,*a,*b],words(integer(a)**2%q,n))
    low_rng=random.Random(LOW_SQUARE_SEED)
    for n in [*range(1,131),191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096]:
        arrays=[[0]*n,[MAX]*n,[1]*n,[MAX if i%2 else 0 for i in range(n)],[1<<(i%64) for i in range(n)]]
        arrays += [[low_rng.getrandbits(64) for _ in range(n)] for _ in range(5)]
        for a in arrays:add('squarebaselow',a,words(integer(a)**2,n))
    return rows


def reachable_code(assembly):
    bodies={m[1]:m[2] for m in re.finditer(r'(?m)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,',assembly,re.S)}
    def inspect(roots,allow_element_checks=False):
        pending=list(roots);seen=set();externals=set();element_checks=[]
        while pending:
            name=pending.pop()
            if name in seen:continue
            if name not in bodies:raise RuntimeError(f'Missing reachable function {name}')
            seen.add(name);body=bodies[name]
            if re.search(r'__rust_(alloc|realloc)|malloc|calloc|free@|__(u?div|u?mod)ti3',body):
                raise RuntimeError(f'Allocation or wide division in {name}')
            if 'panic_bounds_check' in body:
                if not allow_element_checks:raise RuntimeError(f'Element bounds panic in production {name}')
                element_checks.append(name)
            if re.search(r'(?m)^\s*i?div[bwlq]?\s',body):raise RuntimeError(f'General division in {name}')
            for target in re.findall(r'(?m)^\s*(?:callq?|jmp)\s+([^\s]+)',body):
                if target.startswith('.LBB'):continue
                if target in bodies:pending.append(target);continue
                if target in ('*memcpy@GOTPCREL(%rip)','*memset@GOTPCREL(%rip)') or ('core' in target and ('panicking' in target or 'slice_index_fail' in target)):
                    externals.add(target);continue
                raise RuntimeError(f'Uninspected call from {name}: {target}')
        return {'reachable_functions':sorted(seen),'external_calls':sorted(externals),
                'element_bounds_check_functions':sorted(element_checks)}
    production=inspect(['verified_product','verified_square'])
    candidate=inspect(['verified_mac4'],allow_element_checks=True)
    return dict(production,no_allocator_general_division_element_bounds_panic=True,
        scope='Actual fixed product/square dispatch; arbitrary-divisor API excluded from division-free claim',
        retained_checks='Entry assertions and slice-region checks; required copying and zero fill retained',
        mac4_candidate=dict(candidate,selected_by_default=False,
            limitation='Experimental unrolling retains per-element checks on this compiler; measured separately'))



def summarize(text,tuning=False):
    rows=list(csv.DictReader(io.StringIO(text)));groups={}
    names=('square','limbs','top','threshold','low_limit','mode')
    for row in rows:groups.setdefault(tuple(int(row[x]) for x in names),[]).append(row)
    shapes=[(n,63) for n in [128,256,512,1024,2048,4096]] if tuning else SHAPES
    expected={(sq,n,top,t,low,mode) for sq,(n,top),t,low,mode in itertools.product(
        range(2),shapes,[96,192,384] if tuning else [192],[64,128] if tuning else [128],range(6))}
    if set(groups)!=expected:raise RuntimeError('Incomplete benchmark groups')
    result=[]
    for key,group in sorted(groups.items()):
        reps=3 if tuning else 7
        if len(group)!=reps or {int(r['repetition']) for r in group}!=set(range(reps)):
            raise RuntimeError('Incomplete repetitions')
        if any(int(r['iterations'])<=0 or int(r['ns'])<=0 for r in group):raise RuntimeError('Invalid duration')
        result.append(dict(zip(names,key),name=MODES[key[-1]],
            ns_median=statistics.median(int(r['ns'])/int(r['iterations']) for r in group)))
    return result


def check_toom(snapshot,verifier,env,output):
    output.mkdir(parents=True,exist_ok=True);target=output/'verification.json'
    report={'status':'running','scope':'Toom-3, dedicated recursive squaring, fixed production dispatch, MAC4 candidate'}
    target.write_text(json.dumps(report)+'\n')
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def run(cmd,log=None,timeout=240,**kwargs):
        r=subprocess.run(list(map(str,cmd)),cwd=snapshot,env=env,text=True,capture_output=True,timeout=timeout,**kwargs)
        text=r.stdout+r.stderr
        if log:(output/log).write_text(text,encoding='utf-8')
        return r,text
    def compile(source,binary,log,*flags):
        r,text=run([verifier,snapshot/source,'--compile','-O',*flags,'-o',binary],log)
        m=re.search(r'verification results:: (\d+) verified, 0 errors',text)
        if r.returncode or not m:raise RuntimeError(f'Verification/compile failed: {source}')
        return int(m[1])
    try:
        binary=snapshot/'toom-native';report['verification_items_including_imports']=compile('native/toom_words_runner.rs',binary,'proof.log')
        binary_hash=digest(binary);rows=cases();inputs='\n'.join(x for x,_ in rows)+'\n'
        r,_=run([binary],input=inputs)
        expected=[y for _,y in rows];actual=r.stdout.splitlines()
        if r.returncode or actual!=expected:
            i=next((i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y),None)
            raise RuntimeError(f'Integer oracle mismatch {i}; exit={r.returncode}; {r.stderr[:400]}')
        if digest(binary)!=binary_hash:raise RuntimeError('Oracle binary changed')
        report['oracle']={'cases':len(rows),'seed':SEED,'max_limbs':4097,'binary_sha256':binary_hash,
            'direct_low_square_seed':LOW_SQUARE_SEED,'direct_low_square_cases':sum(x.startswith('squarebaselow ') for x,_ in rows),
            'input_sha256':hashlib.sha256(inputs.encode()).hexdigest(),'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),
            'coverage':'Default and forced recursion, three low splits, n mod 3, signed/zero evaluations, full MAX carry chains, all top bits, immutable input alias, nonzero storage, exact scratch and surrounding canaries, row tails including empty, quotient/remainder, direct symmetric low squares including odd/even lengths and cutoff 8/9'}
        invalid=['default 0 192 128 2 1 2','default 65 192 128 2 1 2','square 4294967297 192 128 2 1 2',
            'full 64 23 24 0 1 2','low 64 24 23 0 1 2','low 64 24 24 3 1 2',
            'squarek 64 7 24 0 1 2','shortscratch 64 192 128 2 1 2','divide 0 1','row 1 2 1 1 2 3','squarebase','squarebaselow']
        for i,line in enumerate(invalid):
            r,_=run([binary],f'invalid-{i}.log',input=line+'\n')
            if r.returncode==0 or r.stdout.strip():raise RuntimeError(f'Invalid input accepted: {line}')
        report['invalid_commands_rejected']=len(invalid)
        report['mutations']=[]
        low_square_mutants={'drop_low_row_carry', 'omit_odd_diagonal', 'drop_odd_output', 'omit_low_cross_row', 'truncate_retained_row'}
        mutations=[
            ('square_base.rs', 'omit_low_cross_row', 'while i<n\n        invariant a@.len()==n,dst@.len()==n', 'while i<n-1\n        invariant a@.len()==n,dst@.len()==n', 1),
            ('square_base.rs', 'truncate_retained_row', 'let count=if i<n-i {i}else{n-i};', 'let count=if i<n-i {i-1}else{n-i};', 1),
            ('square_base.rs', 'drop_low_row_carry', 'dst[i+count]=carry;', 'dst[i+count]=0;', 1),
            ('square_base.rs', 'omit_odd_diagonal', 'double_diagonal(dst[n-1],0,a[n/2],carry)', 'double_diagonal(dst[n-1],0,0,carry)', 1),
            ('square_base.rs', 'drop_odd_output', 'double_diagonal(dst[n-1],0,a[n/2],carry);dst[n-1]=low;', 'double_diagonal(dst[n-1],0,a[n/2],carry);dst[n-1]=0;', 1),
            ('square_base.rs','omit_square_cross_double','let low=2*(lo as u128)','let low=1*(lo as u128)',1),
            ('square_base.rs','wrong_square_diagonal','let square=(a as u128)*(a as u128);','let square=a as u128;',1),
            ('square_base.rs','drop_square_row_carry','dst[2*i]=carry;','dst[2*i]=0;',1),
            ('square_base.rs','drop_square_diagonal_carry',
             'carry=next;j+=1;\n    }\n    assert(j==n/2);',
             'carry=0;j+=1;\n    }\n    assert(j==n/2);',1),
            ('toom_multiply.rs','wrong_evaluation_sign','let negative=na!=nb;','let negative=na==nb;',1),
            ('toom_multiply.rs','omit_top_padding','toom_words::zero(&mut p4[2*h..]);','// high padding omitted',1),
            ('toom_multiply.rs','wrong_coefficient_offset','add_shifted(dst,p2,3*k)','add_shifted(dst,p2,2*k)',1),
            ('toom_interpolate.rs','wrong_high_coefficient','scale_exact(scratch,16)','scale_exact(scratch,8)',1),
            ('toom_interpolate.rs','wrong_exact_division','divide_exact(p2,3)','divide_exact(p2,2)',1),
            ('toom_evaluate.rs','wrong_evaluation_point','let xx=x*x;','let xx=x;',1),
            ('square.rs','wrong_difference_sign','let negative=neg_a!=neg_b;','let negative=neg_a==neg_b;',1),
            ('toom_square.rs','negative_square_product','let negative=na!=nb;','let negative=na;',1),
            ('square_low.rs','missing_double_cross','let ghost c2=value(temp@);\n    let _carry=limbs::add_assign(&mut dst[k..],temp);','let ghost c2=value(temp@);',1),
            ('mac4.rs','drop_carry','carry = high;','carry = 0;',5),
            ('mac4.rs','omit_tail','while j < dst.len()','while dst.len() - j > 1',1),
            ('arithmetic.rs','wrong_default_precision','scratch,top,192,128,2','scratch,64,192,128,2',1),
        ]
        for file,name,before,after,count in mutations:
            source=snapshot/'native/verified'/file;original=source.read_bytes();text=original.decode().replace('\r\n','\n')
            if text.count(before)!=count:raise RuntimeError(f'Mutant anchor mismatch: {name}: {text.count(before)}')
            try:
                source.write_text(text.replace(before,after,1))
                flags=['--verify-module','square_base'] if name in low_square_mutants else []
                r,log=run([verifier,snapshot/'native/toom_words_runner.rs',*flags,'--multiple-errors','0'],name+'.log')
                detected=bool(r.returncode and re.search(r'verification results:: \d+ verified, [1-9]\d* errors',log)
                    and any(x in log for x in ('postcondition not satisfied','assertion failed','invariant not satisfied','requires not satisfied','precondition not satisfied'))
                    and not any(x in log.lower() for x in ('resource limit','timed out','unexpected token')))
                report['mutations'].append({'name':name,'rejected_by_semantic_proof':detected,'diagnostics':'first semantic error per function',
                    'scope':'square_base module after complete positive library/runner verification' if name in low_square_mutants else 'complete runner imports'})
                if not detected:raise RuntimeError(f'Mutant not rejected semantically: {name}')
            finally:source.write_bytes(original)
        asm=snapshot/'toom-codegen.s';compile('native/toom_codegen.rs',asm,'codegen.log','--emit=asm')
        report['codegen']=dict(reachable_code(asm.read_text()),assembly_sha256=digest(asm))
        (output/'toom-codegen.s').write_bytes(asm.read_bytes())
        abi=snapshot/'toom-gmp-abi';r,_=run(['c++','-std=c++17',snapshot/'native/controls/gmp_abi.cpp','-lgmp','-o',abi],'gmp-abi-build.log')
        if r.returncode:raise RuntimeError('GMP ABI build failed')
        r,identity=run([abi],'gmp-abi.log')
        if r.returncode:raise RuntimeError('GMP ABI mismatch')
        report['gmp_identity']=identity.strip()
        bench=snapshot/'toom-bench';compile('native/toom_bench.rs',bench,'bench-build.log')
        rowbench=snapshot/'mac4-bench';compile('native/mac4_bench.rs',rowbench,'mac4-build.log')
        squarebench=snapshot/'square-base-bench';compile('native/square_base_bench.rs',squarebench,'square-base-build.log')
        binary_hashes={str(p):digest(p) for p in (bench,rowbench,squarebench)}
        r,linked=run(['ldd',bench],'linked.log')
        if r.returncode:raise RuntimeError('Linkage inspection failed')
        library_hashes={p:digest(Path(p)) for p in re.findall(r'=> (\S+) \(',linked)}
        cpu=min(os.sched_getaffinity(0));affinity=lambda:os.sched_setaffinity(0,{cpu})
        r,_=run([bench,str(BENCH_SEED),'tune'],'tuning.csv',timeout=360,preexec_fn=affinity)
        if r.returncode:raise RuntimeError('Tuning failed')
        report['tuning']=summarize(r.stdout,True)
        r,_=run([bench,str(BENCH_SEED)],'benchmark.csv',timeout=360,preexec_fn=affinity)
        if r.returncode:raise RuntimeError('Benchmark failed')
        report['measurements']=summarize(r.stdout)
        benchmark_csv_sha256=hashlib.sha256(r.stdout.encode()).hexdigest()
        r,_=run([rowbench],'mac4.csv',timeout=120,preexec_fn=affinity)
        if r.returncode:raise RuntimeError('MAC4 benchmark failed')
        row_groups={}
        for row in csv.DictReader(io.StringIO(r.stdout)):
            row_groups.setdefault((int(row['limbs']),int(row['mode'])),[]).append(row)
        expected={(n,m) for n,m in itertools.product([1,2,3,4,5,7,8,12,16,24,32,64,128,256,512],range(3))}
        if set(row_groups)!=expected:raise RuntimeError('Incomplete MAC4 groups')
        report['mac4_measurements']=[]
        for (n,m),group in sorted(row_groups.items()):
            if len(group)!=7 or {int(r['repetition']) for r in group}!=set(range(7)):raise RuntimeError('Incomplete MAC4 repetitions')
            report['mac4_measurements'].append({'limbs':n,'mode':m,'ns_median':statistics.median(int(r['ns'])/int(r['iterations']) for r in group)})
        r,_=run([squarebench],'square-base.csv',timeout=120,preexec_fn=affinity)
        if r.returncode:raise RuntimeError('Square basecase benchmark failed')
        groups={}
        for row in csv.DictReader(io.StringIO(r.stdout)):
            groups.setdefault((int(row['limbs']),int(row['mode'])),[]).append(row)
        expected={(n,m) for n,m in itertools.product([1,2,4,5,6,7,8,9,10,12,15,16,17,23,24,25,32,48,64,128,256],range(3))}
        if set(groups)!=expected:raise RuntimeError('Incomplete square basecase benchmark')
        report['square_base_measurements']=[]
        for (n,m),group in sorted(groups.items()):
            if len(group)!=7 or {int(r['repetition']) for r in group}!=set(range(7)):raise RuntimeError('Incomplete square repetitions')
            report['square_base_measurements'].append({'limbs':n,'mode':m,'ns_median':statistics.median(int(r['ns'])/int(r['iterations']) for r in group)})
        if any(digest(Path(p))!=h for p,h in (binary_hashes|library_hashes).items()):raise RuntimeError('Measured code changed')
        cpuinfo=Path('/proc/cpuinfo').read_text()
        report['benchmark']={'flags':['-O'],'platform':platform.platform(),'cpu_model':next(x.split(':',1)[1].strip() for x in cpuinfo.splitlines() if x.startswith('model name')),
            'raw_csv_sha256':benchmark_csv_sha256,'minimum_recorded_batch_ms':10,
            'pinned_cpu':cpu,'seed':BENCH_SEED,'repetitions':7,'calibration_target_ms':10,'mode_names':MODES,
            'binary_sha256':binary_hashes,'linked_library_sha256':library_hashes,'timing_is_observational':True,
            'semantics':'Multiplication or square modulo 2^p, including required copying/masking. Public GMP mul_n/sqr computes full product first. Allocation setup excluded, GMP internal allocation not instrumented.',
            'controls':'Previous verified Karatsuba, forced Toom splits, full Toom, GMP, actual default; no isolated proof-overhead inference. Row control uses original loop and public GMP addmul_1.',
            'parameter_columns':'threshold/low_limit describe forced modes 1-3; modes 0,4,5 ignore scan context. Default product: K below 512, else 192/128/9:40. Default square: 192/64/11:36.',
            'mac4_workload':'Same initial destination and common iteration count across modes; destination reset outside timing and final states compared.',
            'mac4_default':False,'mac4_policy':'Kept as verified candidate; no consistent win over original carry loop in local measurements.',
            'square_base_modes':{0:'previous_generic_full',1:'symmetric_full',2:'gmp_sqr'},
            'square_base_policy':'Full-square leaves use the symmetric kernel from 8 limbs; below 8 retain generic multiplication. Low-square leaves use the symmetric truncated kernel from 9 limbs; below 9 retain the generic low product.'}
        report['cost']={'toom_full':'T(n)=2T(at most ceil(n/3))+3T(ceil(n/3)+1)+O(n)',
            'low':'L(n)=T(n-h)+2L(h)+O(n), h=floor(9n/40) or floor(11n/36) or floor(n/2)',
            'square':'Dedicated five-point squares; low square computes one cross multiplication and adds it twice',
            'square_base':'Triangular n(n-1)/2 cross products plus n diagonal products, one zero fill and one fused doubling/diagonal pass; O(n^2) operations and O(1) extra words, no extra scratch. Operation formula is analytic.',
            'square_low_base':'floor(n*n/4) retained cross products plus ceil(n/2) diagonal products, O(n^2) word operations and O(1) extra words, no added scratch; analytic operation count.',
            'bound':'O(n^log3(5)) word operations for fixed Toom/base thresholds and all three low splits; analytic derivation, not checked cost theorem',
            'scratch_words':'Full/low product 12n, full/low square 10n; checked recursive capacity; O(log n) call depth',
            'composed_cost_proved':False,'all_gmp_optimizations_implemented':False}
        report['status']='pass'
    except Exception as error:
        report.update(status='error',error=f'{type(error).__name__}: {error}');raise
    finally:target.write_text(json.dumps(report,indent=2)+'\n')
    return report

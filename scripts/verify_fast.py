"""Reproducible refinement, integration and performance checks for fast products."""
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

SEED=20261104
BENCH_SEED=16438731
MODES={0:'previous_schoolbook',1:'balanced_low',2:'unbalanced_low',3:'full_then_truncate',
       4:'gmp_full_then_truncate',5:'ordinary_unbalanced',6:'default_verified'}
SHAPES=[(1,1),(1,64),(2,1),*((n,63) for n in (15,16,17,23,24,25,31,32,33,63,64,65,
    127,128,129,255,256,257,511,512,513,1023,1024,1025,2048,4096))]


def cases():
    rng=random.Random(SEED);rows=[]
    def add(op,args,expected):rows.append((' '.join([op,*map(str,args)]),' '.join(map(str,expected))))
    for a,b,c in itertools.product([0,1,2,(1<<63)-1,1<<63,MAX-1,MAX],[0,1,2,(1<<63)-1,1<<63,MAX-1,MAX],[0,1]):
        x=a-b-c;add('subword',[a,b,c],[x&MAX,int(x<0)])
    for n in [0,1,2,8,64,MAX//4-1,MAX//4,MAX//4+1,MAX]:
        add('workspace',[n],[4*n if 0<n<=MAX//4 else 'none'])
    for n in [1,2,3,8,9,16,17,32,33,65,257]:
        for h in [n,max(0,n-1)]:
            for _ in range(16):
                a=[rng.getrandbits(64) for _ in range(n)];b=[rng.getrandbits(64) for _ in range(h)]
                if _%4==0:a=[0]*n
                x=integer(a)-integer(b);add('abs',[n,*a,*b],[int(x<0),*words(abs(x),n)])
    sizes=list(range(1,74))+[95,96,97,127,128,129,191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096]
    for n in sizes:
        k=n-n//2;h=n//2
        inputs=[([MAX]*n,[MAX]*n),([0]*n,[MAX]*n),([1]+[0]*(n-1),[MAX]*n)]
        # All four difference-sign combinations and zero differences.
        for sa,sb in itertools.product([False,True],repeat=2):
            a=([0]*k+[MAX]*h) if sa else ([MAX]*k+[0]*h)
            b=([0]*k+[MAX]*h) if sb else ([MAX]*k+[0]*h)
            inputs.append((a,b))
        v=[rng.getrandbits(64) for _ in range(h)]
        inputs.append((v+[0]*(k-h)+v,v+[0]*(k-h)+v))
        inputs.extend(([rng.getrandbits(64) for _ in range(n)],[rng.getrandbits(64) for _ in range(n)]) for _ in range(5 if n<257 else 2))
        for index,(a,b) in enumerate(inputs):
            top=[1,7,31,63,64][index%5];exact=integer(a)*integer(b)
            add('full',[top,8,0,*a,*b],words(exact,2*n))
            for split in [0,1]:
                add('mul',[top,8,split,*a,*b],words(exact%(1<<(64*(n-1)+top)),n))
            add('default',[top,24,1,*a,*b],words(exact%(1<<(64*(n-1)+top)),n))
            add('default',[top,24,1,*b,*a],words(exact%(1<<(64*(n-1)+top)),n))
            add('square',[top,8,1,*a,*b],words(integer(a)**2%(1<<(64*(n-1)+top)),n))
        # Isolated cross terms at and across the truncation boundary.
        for i,j in [(k-1,h),(k,h-1),(n-1,1),(n-1,0)]:
            if 0<=i<n and 0<=j<n:
                a=[0]*n;b=[0]*n;a[i]=MAX;b[j]=MAX
                add('default',[63,24,1,*a,*b],words(integer(a)*integer(b)%(1<<(64*n-1)),n))
    return rows


def reachable_code(assembly):
    bodies={m[1]:m[2] for m in re.finditer(r'(?m)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,',assembly,re.S)}
    pending=['verified_fast'];seen=set();externals=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        if name not in bodies:raise RuntimeError(f'Missing reachable function {name}')
        seen.add(name);body=bodies[name]
        if re.search(r'__rust_(alloc|realloc)|malloc|calloc|free@|memmove|panic_bounds_check|__(u?div|u?mod)ti3',body):
            raise RuntimeError(f'Unexpected allocation/general division/element bounds panic in {name}')
        if re.search(r'(?m)^\s*i?div[bwlq]?\s',body):raise RuntimeError(f'Unexpected division in {name}')
        for target in re.findall(r'(?m)^\s*(?:callq?|jmp)\s+([^\s]+)',body):
            if target.startswith('.LBB'):continue
            if target in bodies:pending.append(target);continue
            if target=='*memcpy@GOTPCREL(%rip)' or ('core' in target and ('panicking' in target or 'slice_index_fail' in target)):
                externals.add(target);continue
            raise RuntimeError(f'Uninspected call from {name}: {target}')
    if not re.search(r'(?m)^verified_sub\s*=\s*ordinary_sub$',assembly):raise RuntimeError('Subtraction does not share ordinary machine code')
    return {'reachable_functions':sorted(seen),'external_calls':sorted(externals),'subtraction_exact_alias':True,
        'no_allocator_general_division_element_bounds_panic':True,
        'copy_scope':'One required low-product copy per non-leaf low call; no operand padding or recursive heap allocation',
        'retained_checks':'Entry assertions and slice-region checks; not a claim that all checks disappear'}


def summarize(csv_text,tuning=False):
    rows=list(csv.DictReader(io.StringIO(csv_text)));groups={}
    for r in rows:
        key=tuple(int(r[k]) for k in ('limbs','top','threshold','low_limit','mode'))
        groups.setdefault(key,[]).append(r)
    expected_shapes=[(n,63) for n in [32,64,128,256,512,1024,2048]] if tuning else SHAPES
    expected=set(itertools.product(expected_shapes,[16,24,32] if tuning else [24], [32,64,96,128] if tuning else [64],range(6) if tuning else range(7)))
    expected={(shape[0],shape[1],t,l,m) for shape,t,l,m in expected}
    if set(groups)!=expected:raise RuntimeError('Benchmark shape set incomplete')
    summaries=[]
    for key,group in sorted(groups.items()):
        reps=3 if tuning else 7
        if len(group)!=reps or {int(r['repetition']) for r in group}!=set(range(reps)):
            raise RuntimeError('Benchmark repetition set incomplete')
        if any(int(r['iterations'])<=0 or int(r['ns'])<=0 for r in group):raise RuntimeError('Invalid benchmark duration')
        samples=[int(r['ns'])/int(r['iterations']) for r in group]
        summaries.append(dict(zip(('limbs','top','karatsuba_threshold','low_threshold','mode'),key),
            name=MODES[key[-1]],ns_per_product_median=statistics.median(samples)))
    return summaries


def check_fast(snapshot,verifier,env,output):
    output.mkdir(parents=True,exist_ok=True)
    report={'status':'running','scope':'Difference Karatsuba and low-product divide-and-conquer',
        'complete_library_refined':False,'gmp_performance_parity_established':False}
    target=output/'verification.json';target.write_text(json.dumps(report)+'\n')
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
        binary=snapshot/'fast-native'
        report['verification_items_including_imports']=compile('native/fast_runner.rs',binary,'proof.log')
        binary_hash=digest(binary);rows=cases();input_text='\n'.join(x for x,_ in rows)+'\n'
        r,_=run([binary],input=input_text)
        actual=r.stdout.splitlines();expected=[x for _,x in rows]
        if r.returncode or actual!=expected:
            i=next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
            raise RuntimeError(f'Integer oracle mismatch at {i}; exit={r.returncode}; stderr={r.stderr[:500]}')
        if digest(binary)!=binary_hash:raise RuntimeError('Oracle binary changed')
        report['oracle']={'cases':len(rows),'seed':SEED,'max_limbs':4096,'binary_sha256':binary_hash,
            'input_sha256':hashlib.sha256(input_text.encode()).hexdigest(),'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),
            'coverage':'Full, both low splits, default dispatch, same-input squaring, all sign combinations, zero differences, nonzero initial storage, exact scratch capacities and canaries'}
        invalid=['default 0 24 1 1 2','default 65 24 1 1 2','default 4294967297 24 1 1 2',
            'default 64 24 1','full 64 7 0 1 2','shortscratch 64 24 1 1 2']
        for i,line in enumerate(invalid):
            r,_=run([binary],f'invalid-{i}.log',input=line+'\n')
            if r.returncode==0 or r.stdout.strip():raise RuntimeError(f'Invalid command accepted: {line}')
        report['invalid_commands_rejected']=len(invalid)

        report['mutations']=[]
        for path,name,before,after in [
            ('kernel.rs','drop_second_borrow','(low,(first||second) as u64)','(low,first as u64)'),
            ('fast_words.rs','accumulate_old_first_row','multiply::mac(word,rhs[i],0,carry)','multiply::mac(word,rhs[i],dst[i],carry)'),
            ('fast_multiply.rs','flip_difference_sign','let negative=neg_a!=neg_b;','let negative=neg_a==neg_b;'),
            ('fast_multiply.rs','drop_cross_high','words::add_cross(&mut dst[k..],diff_product,high);','words::add_cross(&mut dst[k..],diff_product,0);'),
            ('fast_multiply.rs','wrong_high_block','full(&mut dst[2*k..],&a[k..],&b[k..],child_scratch,threshold);','full(&mut dst[2*k..],&a[..h],&b[k..],child_scratch,threshold);'),
            ('fast_multiply.rs','wrong_scratch_partition','let (temp,work)=scratch.split_at_mut(h);','let (temp,work)=scratch.split_at_mut(2*h);'),
            ('fast_multiply.rs','omit_cross_product','let _carry=limbs::add_assign(&mut dst[k..],temp);\n    proof {','// second cross product omitted\n    proof {'),
            ('fast_multiply.rs','wrong_default_precision','modular(dst,a,b,scratch,top,24,64,true);','modular(dst,a,b,scratch,64,24,64,true);'),
        ]:
            source=snapshot/'native/verified'/path;original=source.read_bytes();text=original.decode().replace('\r\n','\n')
            if text.count(before)!=1:raise RuntimeError(f'Mutant anchor mismatch: {name}')
            try:
                source.write_text(text.replace(before,after),encoding='utf-8')
                r,log=run([verifier,snapshot/'native/fast_runner.rs'],name+'.log')
                detected=bool(r.returncode and re.search(r'verification results:: \d+ verified, [1-9]\d* errors',log)
                    and any(x in log for x in ('postcondition not satisfied','assertion failed','invariant not satisfied','requires not satisfied','precondition not satisfied'))
                    and not any(x in log.lower() for x in ('resource limit','timed out','unexpected token')))
                report['mutations'].append({'name':name,'rejected_by_semantic_proof':detected})
                if not detected:raise RuntimeError(f'Mutant not rejected semantically: {name}')
            finally:source.write_bytes(original)
        asm=snapshot/'fast-codegen.s';compile('native/fast_codegen.rs',asm,'codegen.log','--emit=asm')
        report['codegen']=dict(reachable_code(asm.read_text()),assembly_sha256=digest(asm))
        (output/'fast-codegen.s').write_bytes(asm.read_bytes())
        abi=snapshot/'gmp-abi'
        r,_=run(['c++','-std=c++17',snapshot/'native/controls/gmp_abi.cpp','-lgmp','-o',abi],'gmp-abi-build.log')
        if r.returncode:raise RuntimeError('GMP ABI is incompatible')
        r,abi_identity=run([abi],'gmp-abi-check.log')
        if r.returncode:raise RuntimeError('GMP ABI check failed')
        report['gmp_abi']='Header-checked 64-bit unsigned limb, zero nails, signed pointer-sized mp_size_t; FFI only in unverified benchmark'
        report['gmp_identity']=abi_identity.strip()
        bench=snapshot/'fast-bench';compile('native/fast_bench.rs',bench,'bench-build.log')
        bench_hash=digest(bench)
        r,linked=run(['ldd',bench],'gmp-linked-libraries.log')
        if r.returncode:raise RuntimeError('Cannot inspect benchmark linkage')
        libraries=re.findall(r'=> (\S+) \(',linked)
        hashes={p:digest(Path(p)) for p in libraries}
        cpu=min(os.sched_getaffinity(0));affinity=lambda:os.sched_setaffinity(0,{cpu})
        r,_=run([bench,str(BENCH_SEED),'tune'],'tuning.csv',timeout=360,preexec_fn=affinity)
        if r.returncode:raise RuntimeError('Threshold experiment failed')
        report['tuning']={'candidate_summary':summarize(r.stdout,True),
            'selection':'Fixed default K=24, low=64, unbalanced=11/36; measured compromise, not asserted universal optimum'}
        r,_=run([bench,str(BENCH_SEED)],'benchmark.csv',timeout=360,preexec_fn=affinity)
        if r.returncode:raise RuntimeError('Performance experiment failed')
        summaries=summarize(r.stdout)
        if digest(bench)!=bench_hash or any(digest(Path(p))!=h for p,h in hashes.items()):raise RuntimeError('Benchmark code/library changed')
        comparisons=[]
        for n,top in SHAPES:
            group={s['mode']:s['ns_per_product_median'] for s in summaries if s['limbs']==n and s['top']==top}
            comparisons.append({'limbs':n,'top':top,'precision_bits':64*(n-1)+top,
                'verified_ns':group[6],'ordinary_ns':group[5],'gmp_ns':group[4],'previous_schoolbook_ns':group[0],
                'speedup_over_previous':group[0]/group[6],'verified_over_gmp':group[6]/group[4],
                'default_over_parameterized_ordinary':group[6]/group[5],
                'parameterized_verified_ns':group[2],'parameterized_verified_over_ordinary':group[2]/group[5]})
        cpuinfo=Path('/proc/cpuinfo').read_text()
        report['benchmark']={'flags':['-O'],'platform':platform.platform(),'cpu_model':next(x.split(':',1)[1].strip() for x in cpuinfo.splitlines() if x.startswith('model name')),
            'cpu_flags':next(x.split(':',1)[1].strip() for x in cpuinfo.splitlines() if x.startswith('flags')),
            'pinned_cpu':cpu,'runtime_seed':BENCH_SEED,'repetitions':7,'calibration_target_ms':15,
            'mode_names':MODES,'binary_sha256':bench_hash,'linked_library_sha256':hashes,
            'timing_is_observational':True,'order':'Same process, modes rotate across seven repetitions; all results checked against GMP outside timing',
            'included':'All arithmetic, required copying, normalization and dispatch; caller allocations/input setup/I/O excluded',
            'ordinary_comparison':'Modes 2/5 share dynamic thresholds and algorithm; default mode 6 has constants visible to the compiler, so 6/5 is an entry-point comparison rather than isolated proof overhead',
            'gmp_scope':'Public mpn_mul_n full 2n product followed by copy/mask; internal GMP allocation not instrumented',
            'summary':comparisons,'all_modes':summaries}
        report['cost']={'default':'K(n)=2K(ceil(n/2))+K(floor(n/2))+O(n); low(n)=K(k)+2low(h)+O(n)',
            'scratch_words':'Full needs 3n, low needs 4n, checked for every actual recursive call; O(log n) recursion depth',
            'derived_word_bound':'O(n^log2(3)) for fixed thresholds and either supported split; analytic consequence of source recurrence, not a machine-checked closed-form cost theorem',
            'parameterized_limit':'Arbitrary caller thresholds are functionally verified but may deliberately choose a quadratic path',
            'composed_cost_proved':False}
        report['status']='pass'
    except Exception as error:
        report.update(status='error',error=f'{type(error).__name__}: {error}');raise
    finally:target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

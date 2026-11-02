"""Immutable full-u64 odd-division feature gate; never performs timing."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,sys,time
import newton_oracle,newton_codegen
S=Path(__file__).resolve().parent
MUTANTS=[
    ('even-wrong-rhs','even_phase_0','toom_words::sub_exact(a5,a4);','toom_words::sub_exact(a5,a3);'),
    ('even-wrong-power','even_phase_0','toom_words::divide_exact(a5,256u64);','toom_words::divide_exact(a5,64u64);'),
    ('even-wrong-odd','even_phase_0','wide_odd_division::divide_toom8_odd(a5,3u64);','wide_odd_division::divide_toom8_odd(a5,15u64);'),
    ('even-wrong-conversion','even_phase_5','scaled_subtraction::sub_scaled_exact(a4,a5,256u64);','scaled_subtraction::sub_scaled_exact(a4,a5,64u64);'),
    ('even-wrong-recovery','even_phase_10','toom_words::divide_exact(a0,1073741824u64);','toom_words::divide_exact(a0,268435456u64);'),
    ('odd-wrong-divisor4095','odd_phase_5','wide_odd_division::divide_toom8_odd(a6,4095u64);','wide_odd_division::divide_toom8_odd(a6,1023u64);'),
    ('odd-wrong-conversion','odd_phase_6','scaled_subtraction::sub_scaled_exact(a5,a6,1024u64);','scaled_subtraction::sub_scaled_exact(a5,a6,256u64);'),
    ('odd-wrong-recovery','odd_phase_12','toom_words::divide_exact(a0,68719476736u64);','toom_words::divide_exact(a0,17179869184u64);'),
]
def mutate(text,function,before,after):
    start=text.index('fn '+function+'(');end=text.index('\n}',start)+2
    body=text[start:end]
    if body.count(before)!=1:raise ValueError('Non-unique scoped mutation anchor: '+function+' / '+before)
    return text[:start]+body.replace(before,after)+text[end:]
original_text=(S/'candidate/native/verified/toom8_newton.rs').read_text()
for name,function,before,after in MUTANTS:mutate(original_text,function,before,after)
tag=sys.argv[1]
if not re.fullmatch('[a-z0-9-]+',tag):raise ValueError('Use a new simple gate tag')
OUT=S/'feature-gates'/tag;OUT.mkdir(parents=True,exist_ok=False)
SNAP=OUT/'inputs'
paths=sorted(p for p in (S/'candidate/native').rglob('*') if p.is_file())+[S/n for n in ['check_newton.py','newton_oracle.py','newton_codegen.py','origin.json','newton-operations.json','modularize_newton.py','prepare_test_bridge.py','parent-newton-proof.json','parent-wide-odd-gate.json','parent-wide-odd-audit.json']]
inputs={p.relative_to(S).as_posix():p.read_bytes() for p in paths}
for name,data in inputs.items():
    dest=SNAP/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
ROOT=SNAP/'candidate';verifier=Path(os.environ['VERUS_BIN']).resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report={'status':'running','scope':'Six/seven-buffer factored Newton interpolation; not a completed Toom8 kernel',
    'source_sha256':{p:hashlib.sha256(b).hexdigest() for p,b in inputs.items()},'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'benchmark_run':False,'production_modified':False,'cpu_affinity':sorted(os.sched_getaffinity(0)),'commands':[]}
def save(): (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
def run(command,log,**kwargs):
    command=list(map(str,command));entry={'argv':command,'log':log,'status':'running'};report['commands'].append(entry);save();start=time.monotonic()
    try:r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=300,**kwargs)
    except subprocess.TimeoutExpired as error:
        (OUT/log).write_text(str(error));entry.update(status='timeout',returncode=None,elapsed_seconds=time.monotonic()-start,log_sha256=sha(OUT/log));save()
        raise RuntimeError('Process timeout: '+log) from error
    text=r.stdout+r.stderr;(OUT/log).write_text(text)
    entry.update(status='completed',returncode=r.returncode,elapsed_seconds=time.monotonic()-start,log_sha256=sha(OUT/log));save()
    return r,text
def compile(args,log):
    r,text=run([verifier,*args],log)
    summaries=re.findall(r'verification results:: (\d+) verified, (\d+) errors',text)
    if r.returncode!=0 or len(summaries)!=1 or summaries[0][1]!='0' or 'partial verification' in text or re.search(r'(?im)^error(?:\[|:)|timed out|resource limit|internal compiler error',text):raise RuntimeError('Full compile failed: '+log)
    return int(summaries[0][0])
def strict_vc(text,returncode):
    errors=re.findall(r'(?m)^error(?:\[[^\]]*\])?: (.*)$',text)
    failures=[e for e in errors if not e.startswith('aborting due to ')]
    allowed=('assertion failed','postcondition not satisfied','precondition not satisfied','requires not satisfied','invariant not satisfied','loop invariant not satisfied','possible arithmetic underflow/overflow','possible arithmetic overflow','possible arithmetic underflow')
    summaries=re.findall(r'verification results:: (\d+) verified, (\d+) errors',text)
    return returncode==1 and bool(failures) and all(any(e.startswith(a) for a in allowed) for e in failures) and len(summaries)==1 and int(summaries[0][1])>0 and '(partial verification with `--verify-*`)' in text and 'note: verifying module toom8_newton' in text and not re.search(r'(?i)timed out|time limit|resource limit|internal error|panicked at|error\[E\d+\]|could not (?:load|compile)|failed to load',text)
save()
try:
    diagnostic_prefix='verification results:: 10 verified, 1 errors (partial verification with `--verify-*`)\nnote: verifying module toom8_newton\n'
    for message in ['assertion failed','postcondition not satisfied','requires not satisfied','invariant not satisfied at end of loop body']:
        assert strict_vc(diagnostic_prefix+'error: '+message+'\nerror: aborting due to 1 previous error\n',1)
    for message in ['unexpected token','internal compiler error','resource limit exceeded','could not compile','verification timed out']:
        assert not strict_vc(diagnostic_prefix+'error: '+message+'\n',1)
    assert not strict_vc('verification results:: 10 verified, 0 errors\n',0)
    assert not strict_vc(diagnostic_prefix+'error[E0308]: mismatched types\n',1)
    assert not strict_vc(diagnostic_prefix+'error: assertion failed\n',0)
    assert not strict_vc(diagnostic_prefix+'error: assertion failed\n',2)
    assert not strict_vc(diagnostic_prefix.replace('toom8_newton','wrong_module')+'error: assertion failed\n',1)
    report['strict_classifier_selfcheck']='pass'
    origin=json.loads((S/'origin.json').read_text())
    for path,h in origin['parent_core_sha256'].items():
        if sha(ROOT/path)!=h:raise RuntimeError('Inherited verified core changed: '+path)
    source_text=(ROOT/'native/verified/toom8_newton.rs').read_text()
    tokens=['toom_words::sub_exact(','wide_odd_division::divide_toom8_odd(','toom_words::divide_exact(','scaled_subtraction::sub_scaled_exact(']
    counts={token:source_text.count(token) for token in tokens}
    if list(counts.values())!=[36,36,36,36]:raise RuntimeError('Unexpected runtime arithmetic schedule')
    even_text=source_text[:source_text.index('fn odd_phase_0(')]
    if sum(even_text.count(token) for token in tokens)!=60:raise RuntimeError('Unexpected even schedule')
    report['static_schedule']={'mathematical_updates':72,'primitive_calls':144,'even':60,'odd':84,'counts':counts,'runtime_matrix':False,'benchmark_run':False}
    pin=json.loads((ROOT/'native/toolchain.json').read_text())
    r,text=run([verifier,'--version'],'toolchain.log');assert r.returncode==0 and pin['verus_version'] in text and pin['rust_toolchain'] in text
    report['toolchain']=text
    r,text=run(['rustup','which','--toolchain',pin['rust_toolchain'],'rustc'],'rustc-path.log');assert r.returncode==0
    rustc=Path(r.stdout.strip()).resolve();r,text=run([rustc,'-vV'],'rustc.log');assert r.returncode==0;report['rustc']=text
    r,text=run(['ldd',rustc],'rustc-linked.log');assert r.returncode==0
    tools=[verifier.parent/n for n in ['verus','rust_verify','z3','vstd.vir','libvstd.rlib','libverus_builtin.rlib','libverus_builtin_macros.so','libverus_state_machines_macros.so']]
    tools += [rustc,Path(shutil.which('rustup')).resolve(),Path(sys.executable).resolve()]
    tools += [Path(p).resolve() for p in re.findall(r'(?:=>\s+|\s)(/\S+)\s+\(',text)]
    report['toolchain_file_sha256']={str(p):sha(p) for p in sorted(set(tools))}
    forbidden=r'\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)'
    for p,b in inputs.items():
        if p.endswith('.rs') and re.search(forbidden,b.decode()):raise RuntimeError('Proof escape '+p)
    report['library_verified']=compile([ROOT/'native/lib.rs','--crate-name','newton_candidate','--crate-type','lib','--export',OUT/'candidate.vir','--compile','-O','-o',OUT/'libcandidate.rlib'],'library.log')
    binary=OUT/'oracle-runner';report['runner_verified']=compile([ROOT/'native/toom8_newton_runner.rs','--compile','-O','-o',binary],'runner-build.log')
    r,text=run(['ldd',binary],'runner-linked.log')
    if r.returncode or 'not found' in text:raise RuntimeError('Runner dependency resolution failed')
    runtime=sorted(set(Path(p).resolve() for p in re.findall(r'(?:=>\s+|\s)(/\S+)\s+\(',text)))
    if len(runtime)!=3 or not any('ld-linux' in p.name for p in runtime):raise RuntimeError('Unexpected runner runtime linkage')
    report['runtime_library_sha256']={str(p):sha(p) for p in runtime}
    rows,counts=newton_oracle.cases();commands='\n'.join(row[0] for row in rows)+'\n'
    r,text=run([binary],'oracle.log',input=commands)
    if r.returncode:raise RuntimeError('Oracle runner failed')
    actual=r.stdout.splitlines();expected=[row[1] for row in rows]
    if actual!=expected:
        mismatches=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
        raise RuntimeError('Oracle mismatch: '+str(mismatches[:10])+' lengths '+str((len(actual),len(expected))))
    report['oracle']={'cases':len(rows),'counts':counts,'input_sha256':hashlib.sha256(commands.encode()).hexdigest(),
        'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),'oracle_model':'Independent Python polynomial evaluations and original nonnegative coefficients'}
    report['invalid']=[]
    for i,command in enumerate(newton_oracle.invalid()):
        r,text=run([binary],f'invalid-{i:02}.log',input=command+'\n')
        if r.returncode==0 or 'panicked at' not in text:raise RuntimeError('Invalid harness command accepted')
        report['invalid'].append({'command':command,'returncode':r.returncode,'log_sha256':sha(OUT/f'invalid-{i:02}.log')})
    codegen=OUT/'codegen.s';report['codegen_verified']=compile([ROOT/'native/toom8_newton_codegen.rs','--compile','-O','--emit=asm','-o',codegen],'codegen-build.log')
    report['codegen']=newton_codegen.inspect(codegen.read_text())
    source=ROOT/'native/verified/toom8_newton.rs';original=source.read_bytes();report['mutations']=[]
    for name,function,before,after in MUTANTS:
        changed=mutate(original.decode(),function,before,after).encode();source.write_bytes(changed)
        try:r,diagnostic=run([verifier,ROOT/'native/toom8_newton_runner.rs','--verify-module','toom8_newton','--multiple-errors','0'],name+'.log')
        finally:source.write_bytes(original)
        rejected=strict_vc(diagnostic,r.returncode)
        report['mutations'].append({'name':name,'function':function,'semantically_rejected':rejected,'source_sha256':hashlib.sha256(changed).hexdigest(),'before':before,'after':after,'log_sha256':sha(OUT/(name+'.log'))})
        save()
        if not rejected:raise RuntimeError('Mutation did not produce a strict VC failure: '+name)
    report['artifact_sha256']={p.name:sha(p) for p in [OUT/'libcandidate.rlib',OUT/'candidate.vir',binary,codegen]}
    if any(sha(S/name)!=h or sha(SNAP/name)!=h for name,h in report['source_sha256'].items()):raise RuntimeError('Source changed during frozen gate')
    if any(sha(p)!=h for p,h in report['toolchain_file_sha256'].items()):raise RuntimeError('Tool changed during gate')
    if any(sha(p)!=h for p,h in report['runtime_library_sha256'].items()):raise RuntimeError('Runner runtime changed during gate')
    report['status']='pass'
except Exception as error:
    report['status']='error';report['error']=f'{type(error).__name__}: {error}'
finally:
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
print(json.dumps({k:report[k] for k in ['status','scope','benchmark_run','finished_utc']}))
if report['status']!='pass':print(report.get('error'))
raise SystemExit(report['status']!='pass')

"""Immutable signed-pair feature gate; never performs timing."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,sys,time,types
if not globals().get('_EXECUTING_CAPTURED_CHECKER',False):
    checker_path=Path(__file__).resolve();checker_bytes=checker_path.read_bytes()
    namespace={'__name__':'__main__','__file__':str(checker_path),'_EXECUTING_CAPTURED_CHECKER':True,'_EXECUTING_CHECKER_BYTES':checker_bytes}
    exec(compile(checker_bytes,str(checker_path),'exec'),namespace)
    raise SystemExit(0)
S=Path(__file__).resolve().parent
MUTANTS=[('ignore-sum-carry', 'kernel::add_limb(x,y,carry)', 'kernel::add_limb(x,y,0)'), ('ignore-difference-borrow', 'kernel::sub_limb(x,y,borrow)', 'kernel::sub_limb(x,y,0)'), ('ignore-plus-sign', 'plus[i]=if negative {difference}else{sum};', 'plus[i]=sum;'), ('ignore-minus-sign', 'minus[i]=if negative {sum}else{difference};', 'minus[i]=difference;'), ('zero-loop-carry', 'carry=next_sum;borrow=next_difference;i+=1;', 'carry=0;borrow=next_difference;i+=1;'), ('zero-loop-borrow', 'carry=next_sum;borrow=next_difference;i+=1;', 'carry=next_sum;borrow=0;i+=1;'), ('ignore-magnitude', 'let x=plus[i];let y=minus[i];', 'let x=plus[i];let y=0u64;'), ('skip-plus-halving', 'toom_words::divide_exact(plus,2);', 'toom_words::divide_exact(plus,1);'), ('wrong-minus-divisor', 'toom_words::divide_exact(minus,2);', 'toom_words::divide_exact(minus,4);'), ('ignore-half-sign', 'sum_difference(plus,minus,negative);', 'sum_difference(plus,minus,false);')]
tag=sys.argv[1]
if not re.fullmatch('[a-z0-9-]+',tag):raise ValueError('Use a new simple gate tag')
OUT=S/'feature-gates'/tag;OUT.mkdir(parents=True,exist_ok=False)
SNAP=OUT/'inputs'
paths=sorted(p for p in (S/'candidate/native').rglob('*') if p.is_file())+[S/n for n in ['check_pair.py','pair_oracle.py','pair_codegen.py','origin.json']]
inputs={p.relative_to(S).as_posix():p.read_bytes() for p in paths}
inputs['check_pair.py']=_EXECUTING_CHECKER_BYTES
for name,data in inputs.items():
    dest=SNAP/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
for module_name in ['pair_oracle','pair_codegen']:
    module=types.ModuleType(module_name);module.__file__=str(SNAP/(module_name+'.py'))
    exec(compile(inputs[module_name+'.py'],module.__file__,'exec'),module.__dict__)
    globals()[module_name]=module
original_text=inputs['candidate/native/verified/toom8_pair.rs'].decode('utf-8')
for name,before,after in MUTANTS:
    if original_text.count(before)!=1:raise ValueError('Non-unique captured mutation anchor: '+name)
ROOT=SNAP/'candidate';verifier=Path(os.environ['VERUS_BIN']).resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report={'status':'running','scope':'Actual simultaneous signed sum/difference and exact parity normalization; not a completed Toom8 kernel',
    'source_sha256':{p:hashlib.sha256(b).hexdigest() for p,b in inputs.items()},'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'benchmark_run':False,'production_modified':False,'cpu_affinity':sorted(os.sched_getaffinity(0)),'commands':[]}
def save(): (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
FATAL_DIAGNOSTIC=r'(?i)\bunknown\b|\brlimit\b|resource\s+limit|timed?\s*out|\btimeout\b|time\s*limit|failed\s+to\s+typecheck|type[- ]?checking?\s+(?:failed|error)|mismatched\s+types|internal\s+(?:compiler\s+)?error|panicked\s+at|error\[E\d+\]|(?:could\s+not|failed\s+to)\s+(?:load|compile)|out\s+of\s+memory|segmentation\s+fault|LLVM\s+ERROR'
def fatal_diagnostic(text):return re.search(FATAL_DIAGNOSTIC,text) is not None
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
    if r.returncode!=0 or len(summaries)!=1 or summaries[0][1]!='0' or 'partial verification' in text or re.search(r'(?im)^error(?:\[|:)',text) or fatal_diagnostic(text):raise RuntimeError('Full compile failed: '+log)
    return int(summaries[0][0])
def strict_vc(text,returncode):
    errors=re.findall(r'(?m)^error(?:\[[^\]]*\])?: (.*)$',text)
    failures=[e for e in errors if not e.startswith('aborting due to ')]
    allowed=('assertion failed','postcondition not satisfied','precondition not satisfied','requires not satisfied','invariant not satisfied','loop invariant not satisfied','possible arithmetic underflow/overflow','possible arithmetic overflow','possible arithmetic underflow')
    summaries=re.findall(r'verification results:: (\d+) verified, (\d+) errors',text)
    return returncode==1 and bool(failures) and all(any(e.startswith(a) for a in allowed) for e in failures) and len(summaries)==1 and int(summaries[0][1])>0 and '(partial verification with `--verify-*`)' in text and 'note: verifying module toom8_pair' in text and not fatal_diagnostic(text)
save()
try:
    diagnostic_prefix='verification results:: 10 verified, 1 errors (partial verification with `--verify-*`)\nnote: verifying module toom8_pair\n'
    for message in ['assertion failed','postcondition not satisfied','requires not satisfied','invariant not satisfied at end of loop body']:
        assert strict_vc(diagnostic_prefix+'error: '+message+'\nerror: aborting due to 1 previous error\n',1)
    for message in ['unexpected token','internal compiler error','resource limit exceeded','could not compile','verification timed out']:
        assert not strict_vc(diagnostic_prefix+'error: '+message+'\n',1)
    assert not strict_vc('verification results:: 10 verified, 0 errors\n',0)
    assert not strict_vc(diagnostic_prefix+'error[E0308]: mismatched types\n',1)
    assert not strict_vc(diagnostic_prefix+'error: assertion failed\n',0)
    assert not strict_vc(diagnostic_prefix+'error: assertion failed\n',2)
    assert not strict_vc(diagnostic_prefix.replace('toom8_pair','wrong_module')+'error: assertion failed\n',1)
    normal_vc=diagnostic_prefix+'error: assertion failed\nerror: aborting due to 1 previous error\n'
    appended_failures=['solver returned unknown','rlimit','failed to typecheck','failed to load metadata','could not compile crate','internal compiler error','verification timed out','out of memory','segmentation fault']
    for message in appended_failures:
        assert not strict_vc(normal_vc+message+'\n',1)
        assert fatal_diagnostic('verification results:: 10 verified, 0 errors\n'+message+'\n')
    report['appended_failure_fixtures_rejected']=appended_failures
    report['executed_snapshot_binding']={'checker':'captured bytes compiled and executed before workload setup','oracle':'captured bytes compiled and executed','codegen_inspector':'captured bytes compiled and executed','origin':'captured bytes parsed'}
    report['strict_classifier_selfcheck']='pass'
    origin=json.loads(inputs['origin.json'])
    for name,digest in origin['inherited_native_sha256'].items():
        if sha(SNAP/name)!=digest:raise RuntimeError('Inherited verified arithmetic changed: '+name)
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
    report['library_verified']=compile([ROOT/'native/lib.rs','--crate-name','pair_candidate','--crate-type','lib','--export',OUT/'candidate.vir','--compile','-O','-o',OUT/'libcandidate.rlib'],'library.log')
    binary=OUT/'oracle-runner';report['runner_verified']=compile([ROOT/'native/toom8_pair_runner.rs','--compile','-O','-o',binary],'runner-build.log')
    r,text=run(['ldd',binary],'runner-linked.log')
    if r.returncode or 'not found' in text:raise RuntimeError('Runner dependency resolution failed')
    runtime=sorted(set(Path(p).resolve() for p in re.findall(r'(?:=>\s+|\s)(/\S+)\s+\(',text)))
    if len(runtime)!=3 or not any('ld-linux' in p.name for p in runtime):raise RuntimeError('Unexpected runner runtime linkage')
    report['runtime_library_sha256']={str(p):sha(p) for p in runtime}
    rows,counts=pair_oracle.cases();commands='\n'.join(row[0] for row in rows)+'\n'
    r,text=run([binary],'oracle.log',input=commands)
    if r.returncode:raise RuntimeError('Oracle runner failed')
    actual=r.stdout.splitlines();expected=[row[1] for row in rows]
    if actual!=expected:
        mismatches=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
        raise RuntimeError('Oracle mismatch: '+str(mismatches[:10])+' lengths '+str((len(actual),len(expected))))
    report['oracle']={'cases':len(rows),'counts':counts,'input_sha256':hashlib.sha256(commands.encode()).hexdigest(),
        'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),'oracle_model':'Independent Python unbounded signed sum/difference and exact halving'}
    report['invalid']=[]
    for i,command in enumerate(pair_oracle.invalid()):
        r,text=run([binary],f'invalid-{i:02}.log',input=command+'\n')
        if r.returncode==0 or 'panicked at' not in text:raise RuntimeError('Invalid harness command accepted')
        report['invalid'].append({'command':command,'returncode':r.returncode,'log_sha256':sha(OUT/f'invalid-{i:02}.log')})
    codegen=OUT/'codegen.s';report['codegen_verified']=compile([ROOT/'native/toom8_pair_codegen.rs','--compile','-O','--emit=asm','-o',codegen],'codegen-build.log')
    report['codegen']=pair_codegen.inspect(codegen.read_text())
    source=ROOT/'native/verified/toom8_pair.rs';original=source.read_bytes();report['mutations']=[]
    for name,before,after in MUTANTS:
        text=original.decode();assert text.count(before)==1,(name,text.count(before))
        changed=text.replace(before,after).encode();source.write_bytes(changed)
        try:r,diagnostic=run([verifier,ROOT/'native/toom8_pair_runner.rs','--verify-module','toom8_pair','--multiple-errors','0'],name+'.log')
        finally:source.write_bytes(original)
        rejected=strict_vc(diagnostic,r.returncode)
        report['mutations'].append({'name':name,'semantically_rejected':rejected,'source_sha256':hashlib.sha256(changed).hexdigest(),'before':before,'after':after,'log_sha256':sha(OUT/(name+'.log'))})
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

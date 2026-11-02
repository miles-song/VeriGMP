"""Immutable actual recursive Toom8 full-product feature gate; never performs timing."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,sys,time,types
if not globals().get('_EXECUTING_CAPTURED_CHECKER',False):
    checker_path=Path(__file__).resolve();checker_bytes=checker_path.read_bytes()
    namespace={'__name__':'__main__','__file__':str(checker_path),'_EXECUTING_CAPTURED_CHECKER':True,'_EXECUTING_CHECKER_BYTES':checker_bytes}
    exec(compile(checker_bytes,str(checker_path),'exec'),namespace)
    raise SystemExit(0)
S=Path(__file__).resolve().parent
MUTANTS=[('skip-recursive-composition', 'candidate/native/verified/toom8_recursive_square.rs', 'toom8_recursive_square', '    balanced(dst,a,k,scratch,threshold);', ''), ('truncate-leaf', 'candidate/native/verified/toom8_recursive_square.rs', 'toom8_recursive_square', 'toom4_square::full(dst,a,scratch,24);', 'toom4_square::full(dst,&a[..a.len()-1],scratch,24);'), ('skip-leaf', 'candidate/native/verified/toom8_recursive_square.rs', 'toom8_recursive_square', 'toom4_square::full(dst,a,scratch,24);', ''), ('misdirect-positive-child', 'candidate/native/verified/toom8_square_producer.rs', 'toom8_square_producer', 'toom8_recursive_square::full(even,ax,work,threshold);', 'toom8_recursive_square::full(odd,ax,work,threshold);'), ('skip-negative-child', 'candidate/native/verified/toom8_square_producer.rs', 'toom8_square_producer', '    toom8_recursive_square::full(odd,ax,work,threshold);', ''), ('flip-signed-product', 'candidate/native/verified/toom8_square_producer.rs', 'toom8_square_producer', 'let negative=na!=nb;', 'let negative=na==nb;'), ('drop-reciprocal-direction', 'candidate/native/verified/toom8_square_dyadic_producer.rs', 'toom8_square_dyadic_producer', 'dyadic_weights(exponent,reciprocal)', 'dyadic_weights(exponent,false)'), ('wrong-dyadic-exponent', 'candidate/native/verified/toom8_square_normalization.rs', 'toom8_square_normalization', 'k,exponent,reciprocal,scratch,threshold);', 'k,0,reciprocal,scratch,threshold);'), ('skip-sixth-pair', 'candidate/native/verified/toom8_square_even.rs', 'toom8_square_even', '    toom8_square_normalization::with_endpoints(e5,o5,a,low,high,k,5,scratch,threshold);', ''), ('wrong-seventh-input', 'candidate/native/verified/toom8_square_seventh.rs', 'toom8_square_seventh', 'toom8_recursive_square::full(dst,ax,work,threshold);', 'toom8_recursive_square::full(dst,a,work,threshold);'), ('skip-seventh-node', 'candidate/native/verified/toom8_square_interpolation.rs', 'toom8_square_interpolation', '    toom8_square_seventh::prepare_seventh(o6,a,low,e0,e1,e2,e3,e4,e5,high,k,scratch,threshold);', ''), ('swap-odd-coefficients', 'candidate/native/verified/toom8_square_interpolation.rs', 'toom8_square_interpolation', 'toom8_newton::odd(o0,o1,o2,o3,o4,o5,o6,', 'toom8_newton::odd(o1,o0,o2,o3,o4,o5,o6,'), ('swap-product-endpoints', 'candidate/native/verified/toom8_recursive_square.rs', 'toom8_recursive_square', 'dst,low,o0,e0,o1,e1,o2,e2,o3,e3,o4,e4,o5,e5,o6,high,a,a,k', 'dst,high,o0,e0,o1,e1,o2,e2,o3,e3,o4,e4,o5,e5,o6,low,a,a,k'), ('nondecreasing-helper-rank', 'candidate/native/verified/toom8_square_producer.rs', 'toom8_square_dyadic_producer', 'decreases a.len(),1nat,', 'decreases a.len(),9nat,')]
tag=sys.argv[1]
if not re.fullmatch('[a-z0-9-]+',tag):raise ValueError('Use a new simple gate tag')
OUT=S/'feature-gates'/tag;OUT.mkdir(parents=True,exist_ok=False)
SNAP=OUT/'inputs'
paths=sorted(p for p in (S/'candidate/native').rglob('*') if p.is_file())+[S/n for n in ['check_square.py','square_oracle.py','square_codegen.py','origin.json','scope.json']]
inputs={p.relative_to(S).as_posix():p.read_bytes() for p in paths}
inputs['check_square.py']=_EXECUTING_CHECKER_BYTES
for name,data in inputs.items():
    dest=SNAP/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
for module_name in ['square_oracle','square_codegen']:
    module=types.ModuleType(module_name);module.__file__=str(SNAP/(module_name+'.py'))
    exec(compile(inputs[module_name+'.py'],module.__file__,'exec'),module.__dict__)
    globals()[module_name]=module
for name,source,module,before,after in MUTANTS:
    original_text=inputs[source].decode('utf-8')
    if original_text.count(before)!=1:raise ValueError('Non-unique captured mutation anchor: '+name)
ROOT=SNAP/'candidate';verifier=Path(os.environ['VERUS_BIN']).resolve()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report={'status':'running','scope':'Dedicated fifteen-square recursive Toom8 kernel with one evaluation per point, lexicographic termination and10n caller scratch; low square, default dispatch and measured performance remain outside this feature.',
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
def strict_vc(text,returncode,module='toom8_recursive_square'):
    errors=re.findall(r'(?m)^error(?:\[[^\]]*\])?: (.*)$',text)
    failures=[e for e in errors if not e.startswith('aborting due to ')]
    allowed=('assertion failed','postcondition not satisfied','precondition not satisfied','requires not satisfied','invariant not satisfied','loop invariant not satisfied','possible arithmetic underflow/overflow','possible arithmetic overflow','possible arithmetic underflow','could not prove termination')
    summaries=re.findall(r'verification results:: (\d+) verified, (\d+) errors',text)
    return returncode==1 and bool(failures) and all(any(e.startswith(a) for a in allowed) for e in failures) and len(summaries)==1 and int(summaries[0][1])>0 and '(partial verification with `--verify-*`)' in text and text.count('note: verifying module ')==1 and re.search(r'(?m)^note: verifying module '+re.escape(module)+r'$',text) is not None and not fatal_diagnostic(text)
save()
try:
    diagnostic_prefix='verification results:: 10 verified, 1 errors (partial verification with `--verify-*`)\nnote: verifying module toom8_recursive_square\n'
    for message in ['assertion failed','postcondition not satisfied','requires not satisfied','invariant not satisfied at end of loop body','could not prove termination']:
        assert strict_vc(diagnostic_prefix+'error: '+message+'\nerror: aborting due to 1 previous error\n',1)
    for message in ['unexpected token','internal compiler error','resource limit exceeded','could not compile','verification timed out']:
        assert not strict_vc(diagnostic_prefix+'error: '+message+'\n',1)
    assert not strict_vc('verification results:: 10 verified, 0 errors\n',0)
    assert not strict_vc(diagnostic_prefix+'error[E0308]: mismatched types\n',1)
    assert not strict_vc(diagnostic_prefix+'error: assertion failed\n',0)
    assert not strict_vc(diagnostic_prefix+'error: assertion failed\n',2)
    assert not strict_vc(diagnostic_prefix.replace('toom8_recursive_square','wrong_module')+'error: assertion failed\n',1)
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
    report['library_verified']=compile([ROOT/'native/lib.rs','--crate-name','producer_candidate','--crate-type','lib','--export',OUT/'candidate.vir','--compile','-O','-o',OUT/'libcandidate.rlib'],'library.log')
    binary=OUT/'oracle-runner';report['runner_verified']=compile([ROOT/'native/toom8_recursive_square_runner.rs','--compile','-O','-o',binary],'runner-build.log')
    r,text=run(['ldd',binary],'runner-linked.log')
    if r.returncode or 'not found' in text:raise RuntimeError('Runner dependency resolution failed')
    runtime=sorted(set(Path(p).resolve() for p in re.findall(r'(?:=>\s+|\s)(/\S+)\s+\(',text)))
    if len(runtime)!=3 or not any('ld-linux' in p.name for p in runtime):raise RuntimeError('Unexpected runner runtime linkage')
    report['runtime_library_sha256']={str(p):sha(p) for p in runtime}
    rows,counts=square_oracle.cases();commands='\n'.join(row[0] for row in rows)+'\n'
    r,text=run([binary],'oracle.log',input=commands)
    if r.returncode:raise RuntimeError('Oracle runner failed')
    actual=r.stdout.splitlines();expected=[row[1] for row in rows]
    if actual!=expected:
        mismatches=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
        raise RuntimeError('Oracle mismatch: '+str(mismatches[:10])+' lengths '+str((len(actual),len(expected))))
    report['oracle']={'cases':len(rows),'counts':counts,'input_sha256':hashlib.sha256(commands.encode()).hexdigest(),
        'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),'oracle_model':'Independent Python unbounded integer square defines full output from original input only'}
    report['invalid']=[]
    for i,command in enumerate(square_oracle.invalid()):
        r,text=run([binary],f'invalid-{i:02}.log',input=command+'\n')
        if r.returncode==0 or 'panicked at' not in text:raise RuntimeError('Invalid harness command accepted')
        report['invalid'].append({'command':command,'returncode':r.returncode,'log_sha256':sha(OUT/f'invalid-{i:02}.log')})
    codegen=OUT/'codegen.s';report['codegen_verified']=compile([ROOT/'native/toom8_recursive_square_codegen.rs','--compile','-O','--emit=asm','-o',codegen],'codegen-build.log')
    report['codegen']=square_codegen.inspect(codegen.read_text())
    report['mutations']=[]
    for name,source_name,module,before,after in MUTANTS:
        source=SNAP/source_name;original=source.read_bytes();text=original.decode();assert text.count(before)==1
        changed=text.replace(before,after).encode();source.write_bytes(changed)
        try:r,diagnostic=run([verifier,ROOT/'native/toom8_recursive_square_runner.rs','--verify-module',module,'--multiple-errors','0'],name+'.log')
        finally:source.write_bytes(original)
        rejected=strict_vc(diagnostic,r.returncode,module)
        report['mutations'].append({'name':name,'source_path':source_name,'verified_module':module,'semantically_rejected':rejected,'source_sha256':hashlib.sha256(changed).hexdigest(),'before':before,'after':after,'log_sha256':sha(OUT/(name+'.log'))})
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

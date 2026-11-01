from pathlib import Path
import hashlib,json,os,random,re,subprocess,sys,shutil,datetime
STAGE=Path(__file__).resolve().parent
ROOT=STAGE/'candidate';OUT=STAGE/'evidence';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from verify_toom import cases,reachable_code
from verify_multiply import integer,words,MAX
verifier=Path(os.environ['VERUS_BIN']).resolve();report={'status':'running','scope':'Isolated cutoff9 low-square candidate; no production source mutation',
    'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'benchmark_run':False,
    'cpu_affinity':sorted(os.sched_getaffinity(0)),'candidate_cutoff':9}
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
files=[p for name in ['baseline','candidate'] for p in (STAGE/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [STAGE/name for name in ['check.py','compare.rs','compare_dense.rs','measure.py','origin.json']]
inputs={p:p.read_bytes() for p in files}
report['source_hashes_lf']={p.relative_to(ROOT).as_posix():hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest() for p,b in inputs.items() if p.is_relative_to(ROOT)}
report['source_sha256']={p.relative_to(STAGE).as_posix():hashlib.sha256(b).hexdigest() for p,b in inputs.items()}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,log,**kwargs):
    r=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,text=True,timeout=300,**kwargs)
    text=r.stdout+r.stderr;(OUT/log).write_text(text)
    return r,text
def compile(args,log):
    r,text=run([verifier,*args],log)
    m=re.search(r'verification results:: (\d+) verified, 0 errors',text)
    if r.returncode or not m or 'partial verification' in text:raise RuntimeError('Full compilation failed: '+log)
    return int(m[1])
try:
    origin=json.loads((STAGE/'origin.json').read_text())
    for name,hashes in origin['source_bytes'].items():
        if any(sha(STAGE/name/p)!=h for p,h in hashes.items()):raise RuntimeError('Source differs from prepared snapshot: '+name)
    pin=json.loads((ROOT/'native/toolchain.json').read_text())
    r,version=run([verifier,'--version'],'toolchain.log')
    if r.returncode or pin['verus_version'] not in version or pin['rust_toolchain'] not in version:raise RuntimeError('Pinned verifier mismatch')
    report['toolchain']=version
    r,text=run(['rustup','which','--toolchain',pin['rust_toolchain'],'rustc'],'rustc-path.log')
    if r.returncode:raise RuntimeError('Fixed compiler not found')
    rustc=Path(r.stdout.strip()).resolve()
    r,text=run([rustc,'-vV'],'rustc.log')
    if r.returncode:raise RuntimeError('Compiler identity failed')
    report['rustc']=text
    r,text=run(['ldd',rustc],'rustc-linked.log')
    if r.returncode:raise RuntimeError('Compiler linkage failed')
    tools=[verifier.parent/name for name in ['verus','rust_verify','z3','vstd.vir','libvstd.rlib','libverus_builtin.rlib',
        'libverus_builtin_macros.so','libverus_state_machines_macros.so']]
    tools += [rustc,Path(shutil.which('rustup')).resolve()]
    tools += [Path(p).resolve() for p in re.findall(r'=> (\S+) \(',text)]
    tool_hashes={str(p):sha(p) for p in sorted(set(tools))};report['toolchain_file_sha256']=tool_hashes
    for p,b in inputs.items():
        if p.suffix=='.rs' and re.search(r'\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)',b.decode()):
            raise RuntimeError('Proof escape: '+str(p))
    report['libraries']={}
    for name in ['baseline','candidate']:
        lib=OUT/('lib'+name+'.rlib');vir=OUT/(name+'.vir')
        items=compile([STAGE/name/'native/lib.rs','--crate-name',name,'--crate-type','lib','--export',vir,'--compile','-O','-o',lib],name+'-library.log')
        if items<=0:raise RuntimeError('No library items verified: '+name)
        report['libraries'][name]={'verified':items,'rlib_sha256':sha(lib),'vir_sha256':sha(vir)}
    runner=OUT/'oracle-runner'
    report['verified_runner']=compile([ROOT/'native/toom_words_runner.rs','--compile','-O','-o',runner],'runner-build.log')
    rows=cases();existing=len(rows);rng=random.Random(20261103)
    for n in [*range(1,131),191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096]:
        arrays=[[0]*n,[MAX]*n,[1]*n,[MAX if i%2 else 0 for i in range(n)],[1<<(i%64) for i in range(n)]]
        arrays += [[rng.getrandbits(64) for _ in range(n)] for _ in range(5)]
        for a in arrays:rows.append(('squarebaselow '+' '.join(map(str,a)),' '.join(map(str,words(integer(a)**2,n)))))
    text='\n'.join(c for c,_ in rows)+'\n';expected=[x for _,x in rows]
    r,_=run([runner],'oracle.log',input=text)
    if r.returncode or r.stdout.splitlines()!=expected:raise RuntimeError('Independent oracle mismatch')
    report['oracle']={'cases':len(rows),'existing_suite':existing,'new_direct_low':len(rows)-existing,'max_limbs':4097,'seed':20261103,
        'binary_sha256':sha(runner),'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest()}
    r,_=run([runner],'empty-low.log',input='squarebaselow\n')
    if r.returncode==0 or r.stdout.strip():raise RuntimeError('Empty input accepted')
    report['mutations']=[]
    source=ROOT/'native/verified/square_base.rs';original=source.read_bytes();original_text=original.decode()
    mutants=[
        ('omit_low_cross_row','while i<n\n        invariant a@.len()==n,dst@.len()==n','while i<n-1\n        invariant a@.len()==n,dst@.len()==n'),
        ('truncate_retained_row','let count=if i<n-i {i}else{n-i};','let count=if i<n-i {i-1}else{n-i};'),
        ('drop_low_row_carry','dst[i+count]=carry;','dst[i+count]=0;'),
        ('omit_odd_diagonal','double_diagonal(dst[n-1],0,a[n/2],carry)','double_diagonal(dst[n-1],0,0,carry)'),
        ('drop_odd_output','double_diagonal(dst[n-1],0,a[n/2],carry);dst[n-1]=low;','double_diagonal(dst[n-1],0,a[n/2],carry);dst[n-1]=0;'),
    ]
    try:
        for name,before,after in mutants:
            if original_text.count(before)!=1:raise RuntimeError('Mutation anchor '+name)
            source.write_text(original_text.replace(before,after))
            r,text=run([verifier,ROOT/'native/lib.rs','--crate-type','lib','--verify-module','square_base','--multiple-errors','0'],name+'.log')
            ok=bool(r.returncode and re.search(r'verification results:: \d+ verified, [1-9]\d* errors',text)
                and any(x in text for x in ['requires not satisfied','invariant not satisfied','postcondition not satisfied','assertion failed'])
                and not any(x in text.lower() for x in ['resource limit','timed out','unexpected token']))
            report['mutations'].append({'name':name,'semantically_rejected':ok,'scope':'square_base module after complete positive library verification'})
            if not ok:raise RuntimeError('Mutation did not fail semantically: '+name)
    finally:source.write_bytes(original)
    asm=OUT/'codegen.s';compile([ROOT/'native/toom_codegen.rs','--compile','-O','--emit=asm','-o',asm],'codegen.log')
    report['codegen']=reachable_code(asm.read_text())
    args=[STAGE/'compare.rs','--compile','-O','-o',OUT/'compare']
    for name in ['baseline','candidate']:args += ['--import',str(name)+'='+str(OUT/(name+'.vir')),'--extern',str(name)+'='+str(OUT/('lib'+name+'.rlib'))]
    report['benchmark_driver_verified_items']=compile(args,'compare-build.log')
    report['benchmark_driver_scope']='Ordinary unverified driver importing two independently verified libraries; no benchmark run by this script'
    report['benchmark_source_sha256']=sha(STAGE/'compare.rs');report['benchmark_binary_sha256']=sha(OUT/'compare')
    args=[STAGE/'compare_dense.rs','--compile','-O','-o',OUT/'compare-dense']
    for name in ['baseline','candidate']:args += ['--import',str(name)+'='+str(OUT/(name+'.vir')),'--extern',str(name)+'='+str(OUT/('lib'+name+'.rlib'))]
    report['dense_driver_verified_items']=compile(args,'compare-dense-build.log')
    dense={'benchmark_source_sha256':sha(STAGE/'compare_dense.rs'),'benchmark_binary_sha256':sha(OUT/'compare-dense'),
        'scope':'Ordinary unverified driver importing the same verified baseline/candidate library and metadata pairs'}
    (OUT/'dense-driver.json').write_text(json.dumps(dense,indent=2)+'\n')
    for name,identity in report['libraries'].items():
        if sha(OUT/('lib'+name+'.rlib'))!=identity['rlib_sha256'] or sha(OUT/(name+'.vir'))!=identity['vir_sha256']:
            raise RuntimeError('Paired library artifacts changed: '+name)
    if sha(runner)!=report['oracle']['binary_sha256']:raise RuntimeError('Oracle runner changed')
    if any(p.read_bytes()!=b for p,b in inputs.items()):raise RuntimeError('Candidate inputs changed during verification')
    if any(sha(Path(p))!=h for p,h in tool_hashes.items()):raise RuntimeError('Tool identity changed')
    report['artifact_sha256']={p.name:sha(p) for p in [runner,asm,OUT/'compare',OUT/'compare-dense',OUT/'dense-driver.json']}
    report['identity_checks_before_after']=True
    report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    report['status']='pass'
except Exception as e:
    report.update(status='error',error=f'{type(e).__name__}: {e}')
finally:(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','error','libraries','oracle'] if k in report}))
raise SystemExit(report['status']!='pass')

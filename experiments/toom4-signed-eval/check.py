"""Same-source isolated acceptance; this script never runs timing benchmarks."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys

STAGE=Path(__file__).resolve().parent;ROOT=STAGE/'candidate';OUT=STAGE/'evidence';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from verify_toom import cases,reachable_code
spec=importlib.util.spec_from_file_location('scaled_oracle',STAGE/'oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
import odd_oracle, fusion_oracle, signed_oracle
from signed_codegen import inspect_signed
from fusion_codegen import inspect_fusion
from odd_codegen import inspect_odd
verifier=Path(os.environ['VERUS_BIN']).resolve()
report={'status':'running','scope':'Single-pass signed Toom-4 evaluation; unchanged policies and Toom-3; e22 and frozen interpolation-fusion controls',
    'baseline_commit':'e22a4dd00a28681fd27d68e2a78fa304cf17563e','production_source_modified':False,
    'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'benchmark_run':False,
    'cpu_affinity':sorted(os.sched_getaffinity(0))}
target=OUT/'verification.json';target.write_text(json.dumps(report,indent=2)+'\n')
files=[p for name in ['baseline','previous','candidate'] for p in (STAGE/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
files += [STAGE/name for name in ['check.py','oracle.py','compare.rs','mutations.json','measure_interpolation.py','time_verified.py','run_confirmations.py','summarize_confirmations.py','origin.json','gmp-toom4-reference.json','scope.json','gmp-odd-reference.json','odd_oracle.py','odd_codegen.py','compare_confirmations.py','fusion_oracle.py','fusion_codegen.py','signed_oracle.py','signed_codegen.py']]
inputs={p:p.read_bytes() for p in files}
report['source_sha256']={p.relative_to(STAGE).as_posix():hashlib.sha256(b).hexdigest() for p,b in inputs.items()}
report['source_hashes_lf']={p.relative_to(ROOT).as_posix():hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest() for p,b in inputs.items() if p.is_relative_to(ROOT)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(command,log,**kwargs):
    r=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,text=True,timeout=300,**kwargs)
    text=r.stdout+r.stderr;(OUT/log).write_text(text);return r,text
def compile(args,log):
    r,text=run([verifier,*args],log)
    match=re.search(r'verification results:: (\d+) verified, 0 errors',text)
    if r.returncode or not match or 'partial verification' in text:raise RuntimeError('Full compile failed: '+log)
    return int(match[1])
try:
    origin=json.loads((STAGE/'origin.json').read_text())
    for name,hashes in origin['source_bytes'].items():
        if any(sha(STAGE/name/p)!=h for p,h in hashes.items()):raise RuntimeError('Source differs from prepared snapshot: '+name)
    pin=json.loads((ROOT/'native/toolchain.json').read_text())
    r,text=run([verifier,'--version'],'toolchain.log')
    if r.returncode or pin['verus_version'] not in text or pin['rust_toolchain'] not in text:raise RuntimeError('Verifier identity mismatch')
    report['toolchain']=text
    r,text=run(['rustup','which','--toolchain',pin['rust_toolchain'],'rustc'],'rustc-path.log')
    if r.returncode:raise RuntimeError('Missing pinned rustc')
    rustc=Path(r.stdout.strip()).resolve();r,text=run([rustc,'-vV'],'rustc.log')
    if r.returncode:raise RuntimeError('Rust identity failure')
    report['rustc']=text
    r,text=run(['ldd',rustc],'rustc-linked.log')
    if r.returncode:raise RuntimeError('Rust linkage failure')
    tools=[verifier.parent/name for name in ['verus','rust_verify','z3','vstd.vir','libvstd.rlib','libverus_builtin.rlib',
        'libverus_builtin_macros.so','libverus_state_machines_macros.so']]
    tools += [rustc,Path(shutil.which('rustup')).resolve(),Path(shutil.which('c++')).resolve(),Path(sys.executable).resolve()]
    tools += [Path(p).resolve() for p in re.findall(r'=> (\S+) \(',text)]
    tool_hashes={str(p):sha(p) for p in sorted(set(tools))};report['toolchain_file_sha256']=tool_hashes
    forbidden=r'\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)'
    for p,b in inputs.items():
        if p.suffix=='.rs' and p.is_relative_to(ROOT/'native') and re.search(forbidden,b.decode()):raise RuntimeError('Proof escape '+str(p))
    report['libraries']={}
    for name in ['baseline','previous','candidate']:
        lib=OUT/('lib'+name+'.rlib');vir=OUT/(name+'.vir')
        items=compile([STAGE/name/'native/lib.rs','--crate-name',name,'--crate-type','lib','--export',vir,'--compile','-O','-o',lib],name+'-library.log')
        if items<=0:raise RuntimeError('No positive proof items')
        report['libraries'][name]={'verified':items,'rlib_sha256':sha(lib),'vir_sha256':sha(vir)}
    binary=OUT/'oracle-runner';report['verified_runner']=compile([ROOT/'native/toom4_runner.rs','--compile','-O','-o',binary],'runner-build.log')
    rows=cases();existing=len(rows);direct=oracle.cases();odd_cases=odd_oracle.cases();fusion_cases=fusion_oracle.cases();signed_cases=signed_oracle.cases();rows+=direct+odd_cases+fusion_cases+signed_cases
    data='\n'.join(x for x,y in rows)+'\n';expected=[y for x,y in rows];binary_hash=sha(binary)
    r,text=run([binary],'oracle.log',input=data)
    if r.returncode or r.stdout.splitlines()!=expected:raise RuntimeError('Independent integer oracle mismatch')
    report['oracle']={'cases':len(rows),'existing_suite':existing,'direct_toom4_cases':len(direct),'seed':oracle.SEED,'max_limbs':4097,
        'binary_sha256':binary_hash,'input_sha256':hashlib.sha256(data.encode()).hexdigest(),'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),
        'signed_cases':len(signed_cases),'signed_coverage':signed_oracle.summary(),
        'fusion_cases':len(fusion_cases),'fusion_coverage':fusion_oracle.summary(),
        'odd_division_cases':len(odd_cases),'odd_division_coverage':odd_oracle.summary(),
        'coverage':'Forced thresholds 24/192/256; full products, dedicated squares, aliased read-only operands, low products at all split modes and top-bit boundaries, exact workspace and output canaries, four-block weighted and signed evaluation including empty/short top blocks; unchanged existing suite retained'}
    invalid=[
        'full4 64 23 24 0 1 1', 'squarefull4 64 23 24 0 1 1',
        'candidate4 0 256 128 2 1 1', 'candidate4square 65 256 128 2 1 1',
        'shortscratch4 64 24 24 0 1 1', 'weighted4 8 8 0 0 1 1 1 2 3 4',
        'signed4 2 1 1 1 2 3 4', 'full4 64 24 24 0 1 1 1']
    invalid+=odd_oracle.invalid()+fusion_oracle.invalid()+signed_oracle.invalid()
    for i,command in enumerate(invalid):
        r,text=run([binary],f'invalid-{i}.log',input=command+'\n')
        if r.returncode==0 or r.stdout.strip():raise RuntimeError('Invalid command accepted')
    report['invalid_commands_rejected']=len(invalid)
    mutations=json.loads((STAGE/'mutations.json').read_text())
    report['mutations']=[]
    for file,name,before,after,module in mutations:
        source=ROOT/'native/verified'/file;original=source.read_bytes();text=original.decode().replace('\r\n','\n')
        if text.count(before)!=1:raise RuntimeError('Ambiguous mutation '+name)
        try:
            source.write_text(text.replace(before,after))
            r,text=run([verifier,ROOT/'native/lib.rs','--crate-type','lib','--verify-module',module,'--multiple-errors','0'],name+'.log')
            rejected=bool(r.returncode and re.search(r'verification results:: \d+ verified, [1-9]\d* errors',text)
                and any(x in text for x in ['requires not satisfied','precondition not satisfied','invariant not satisfied','postcondition not satisfied','assertion failed'])
                and not re.search(r'error\[E\d+\]|solver returned unknown|resource limit|timed out|timeout|unexpected token|could not compile|failed to load|panicked at|segmentation fault|internal compiler error',text,re.I))
            report['mutations'].append({'name':name,'semantically_rejected':rejected,'scope':module+' after complete positive library and runner verification'})
            if not rejected:raise RuntimeError('Mutation not semantically rejected '+name)
        finally:source.write_bytes(original)
    asm=OUT/'codegen.s';compile([ROOT/'native/toom4_codegen.rs','--compile','-O','--emit=asm','-o',asm],'codegen.log')
    report['codegen']=reachable_code(asm.read_text())
    report['odd_codegen']=inspect_odd(asm.read_text())
    report['fusion_codegen']=inspect_fusion(asm.read_text())
    report['signed_codegen']=inspect_signed(asm.read_text())
    for required in ['toom4_multiply','toom4_square']:
        if not any(required in name for name in report['codegen']['reachable_functions']):raise RuntimeError('Forced Toom-4 code is not reachable: '+required)
    report['legacy_entrypoints']={}
    for entry in ['mac4_bench.rs','square_base_bench.rs','toom_codegen.rs','toom_words_runner.rs','toom_bench.rs']:
        output=OUT/('legacy-'+Path(entry).stem)
        count=compile([ROOT/'native'/entry,'--compile','-O','-o',output],'legacy-'+entry+'.log')
        report['legacy_entrypoints'][entry]={'verified':count,'binary_sha256':sha(output),'executed':False,
            'scope':'Existing standalone entry imports and whole crate verification/optimized compile; no benchmark execution'}
    abi=OUT/'gmp-abi';r,text=run(['c++','-std=c++17',ROOT/'native/controls/gmp_abi.cpp','-lgmp','-o',abi],'gmp-abi-build.log')
    if r.returncode:raise RuntimeError('GMP ABI build failed')
    r,text=run([abi],'gmp-abi.log')
    if r.returncode:raise RuntimeError('GMP ABI mismatch')
    report['gmp_abi']=text.strip()
    for driver,output in [('compare.rs','compare')]:
        args=[STAGE/driver,'--compile','-O','-o',OUT/output]
        for name in ['baseline','previous','candidate']:args += ['--import',name+'='+str(OUT/(name+'.vir')),'--extern',name+'='+str(OUT/('lib'+name+'.rlib'))]
        compile(args,output+'-build.log')
    report['benchmark_source_sha256']=sha(STAGE/'compare.rs');report['benchmark_binary_sha256']=sha(OUT/'compare')
    r,text=run(['ldd',OUT/'compare'],'benchmark-linked.log')
    if r.returncode:raise RuntimeError('GMP linkage failure')
    libraries={str(Path(p).resolve()):sha(Path(p).resolve()) for p in re.findall(r'=> (\S+) \(',text)}
    if len([p for p in libraries if Path(p).name.startswith('libgmp')])!=1:raise RuntimeError('Ambiguous GMP linkage')
    report['runtime_library_sha256']=libraries
    for name,identity in report['libraries'].items():
        if sha(OUT/('lib'+name+'.rlib'))!=identity['rlib_sha256'] or sha(OUT/(name+'.vir'))!=identity['vir_sha256']:raise RuntimeError('Changed library pair')
    if sha(binary)!=binary_hash:raise RuntimeError('Changed oracle binary')
    if any(p.read_bytes()!=b for p,b in inputs.items()):raise RuntimeError('Changed inputs')
    if any(sha(Path(p))!=h for p,h in (tool_hashes|libraries).items()):raise RuntimeError('Changed tools or libraries')
    report['artifact_sha256']={p.name:sha(p) for p in [binary,asm,abi,OUT/'compare']}
    for entry,item in report['legacy_entrypoints'].items():
        output=OUT/('legacy-'+Path(entry).stem)
        if sha(output)!=item['binary_sha256']:raise RuntimeError('Changed legacy entry artifact')
        report['artifact_sha256'][output.name]=item['binary_sha256']
    report.update(status='pass',identity_checks_before_after=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as error:report.update(status='error',error=f'{type(error).__name__}: {error}')
finally:target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','error','libraries','oracle'] if k in report},indent=2))
raise SystemExit(report['status']!='pass')

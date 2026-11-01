from pathlib import Path
import argparse,csv,datetime,hashlib,io,json,os,platform,re,statistics,subprocess
STAGE=Path(__file__).resolve().parent;EVIDENCE=STAGE/'evidence'
parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--cpu',type=int,default=0);args=parser.parse_args()
if not re.fullmatch('[a-z0-9_-]+',args.tag):raise RuntimeError('Invalid run tag')
output=EVIDENCE/args.tag;output.mkdir(exist_ok=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
verification=json.loads((EVIDENCE/'verification.json').read_text());binary=EVIDENCE/'compare'
driver=verification
source=STAGE/'compare.rs'
if verification['status']!='pass' or sha(binary)!=driver['benchmark_binary_sha256'] or sha(source)!=driver['benchmark_source_sha256']:raise RuntimeError('Unverified or changed benchmark executable/source')
for p,h in verification['source_hashes_lf'].items():
    if hashlib.sha256((STAGE/'candidate'/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=h:raise RuntimeError('Changed candidate source: '+p)
for name,identity in verification['libraries'].items():
    if sha(EVIDENCE/('lib'+name+'.rlib'))!=identity['rlib_sha256'] or sha(EVIDENCE/(name+'.vir'))!=identity['vir_sha256']:raise RuntimeError('Changed imported library')
linked=subprocess.check_output(['ldd',binary],text=True)
(output/'linked.log').write_text(linked)
libraries={p:sha(Path(p)) for p in re.findall(r'=> (\S+) \(',linked)}
verifier=Path(os.environ['VERUS_BIN']);tool_version=subprocess.check_output([verifier,'--version'],text=True)
tool_hashes={p.name:sha(p) for p in [verifier,*[verifier.parent/n for n in ['rust_verify','z3','vstd.vir','libvstd.rlib']]]}
report={'status':'running','scope':'isolated Toom-4 entry candidate, previous forced policy and unchanged production baseline',
    'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'cpu':args.cpu,
    'cpu_model':next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
    'verified_library_identities':verification['libraries'],'tool_version':tool_version,'tool_sha256':tool_hashes,
    'flags':['-O'],'benchmark_binary_sha256':sha(binary),'benchmark_source_sha256':sha(source),
    'linked_library_sha256':libraries,'mode_names':{'0':'baseline_actual_dispatch','1':'previous_forced_toom4_same_algorithm_proof_stabilized','2':'entry_candidate','3':'gmp_full_then_copy_and_mask'},
    'precision_policy':'same top bits and result words for every mode','seed':16438731,'repetitions':7,'minimum_actual_batch_ns':10_000_000,
    'sample_policy':'mode order rotates by repetition; sub-10ms batches are retried after doubling that mode count; allocation outside timing; every recorded result equals GMP'}
try:
    command=[binary]
    r=subprocess.run(command,capture_output=True,text=True,timeout=240,preexec_fn=lambda:os.sched_setaffinity(0,{args.cpu}))
    (output/'benchmark.csv').write_text(r.stdout);(output/'stderr.log').write_text(r.stderr)
    if r.returncode:raise RuntimeError('Benchmark runtime failure')
    rows=list(csv.DictReader(io.StringIO(r.stdout)));groups={}
    for row in rows:groups.setdefault(tuple(int(row[k]) for k in ['operation','limbs','top','mode']),[]).append(row)
    shapes=[(1,1),(1,64),(2,1),*[(n,63) for n in [23,24,25,63,64,65,127,128,129,191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096]]]
    operations=[0,1]
    if set(groups)!={(op,n,t,mode) for op in operations for n,t in shapes for mode in range(4)}:raise RuntimeError('Incomplete shape matrix')
    medians={}
    for key,group in groups.items():
        if len(group)!=7 or {int(r['repetition']) for r in group}!=set(range(7)):raise RuntimeError('Incomplete repetitions')
        if any(int(r['iterations'])<=0 or int(r['ns'])<10_000_000 for r in group):raise RuntimeError('Incomplete actual recording duration')
        medians[key]=statistics.median(int(r['ns'])/int(r['iterations']) for r in group)
    report['measurements']=[{'operation':op,'limbs':n,'top':top,
        'baseline_ns':medians[op,n,top,0],'previous_ns':medians[op,n,top,1],
        'candidate_ns':medians[op,n,top,2],'gmp_ns':medians[op,n,top,3],
        'candidate_over_baseline':medians[op,n,top,2]/medians[op,n,top,0],
        'candidate_over_previous':medians[op,n,top,2]/medians[op,n,top,1],
        'candidate_over_gmp':medians[op,n,top,2]/medians[op,n,top,3]}
        for op in operations for n,top in shapes]
    report['raw_sha256']=sha(output/'benchmark.csv');report['samples']=len(rows);report['minimum_observed_batch_ns']=min(int(r['ns']) for r in rows)
    if sha(binary)!=report['benchmark_binary_sha256'] or any(sha(Path(p))!=h for p,h in libraries.items()):raise RuntimeError('Code/library identity changed during timing')
    report['status']='pass'
except Exception as e:report.update(status='error',error=f'{type(e).__name__}: {e}')
(output/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','error','samples','minimum_observed_batch_ns'] if k in report}))
raise SystemExit(report['status']!='pass')

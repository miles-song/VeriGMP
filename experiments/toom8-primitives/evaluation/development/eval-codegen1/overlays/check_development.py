from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
S=Path(__file__).resolve().parent;tag=sys.argv[1];mode=sys.argv[2] if len(sys.argv)>2 else 'focused'
O=S/'development'/tag;O.mkdir(parents=True,exist_ok=False);snap=O/'inputs'
paths=sorted(p for p in (S/'candidate/native').rglob('*') if p.is_file())+[Path(__file__),S/'origin.json']
hashes={}
for p in paths:
    name=p.relative_to(S).as_posix();d=snap/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d);hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
entry='toom8_evaluation_runner.rs' if mode=='runner' else 'toom8_evaluation_codegen.rs' if mode=='codegen' else 'lib.rs'
cmd=[os.environ['VERUS_BIN'],str(snap/'candidate/native'/entry),'--crate-name','toom8_evaluation_candidate']
if mode not in ['runner','codegen']:cmd+=['--crate-type','lib']
if mode=='focused':cmd+=['--verify-module','toom8_evaluation']
if mode=='spec':cmd+=['--verify-module','toom8_evaluation_spec']
if mode=='compile':cmd+=['--compile','-O','--export',str(O/'candidate.vir'),'-o',str(O/'libcandidate.rlib')]
if mode=='runner':cmd+=['--compile','-O','-o',str(O/'oracle-runner')]
if mode=='codegen':cmd+=['--compile','-O','--emit=asm','-o',str(O/'codegen.s')]
r={'status':'running','command':cmd,'source_sha256':hashes,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpu_affinity':sorted(os.sched_getaffinity(0)),'benchmark_run':False}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n')
p=subprocess.run(cmd,cwd=snap/'candidate',capture_output=True,text=True);raw=p.stdout+p.stderr;(O/'proof.log').write_text(raw)
r.update(status='pass' if p.returncode==0 else 'error',returncode=p.returncode,log_sha256=hashlib.sha256((O/'proof.log').read_bytes()).hexdigest(),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(raw);raise SystemExit(p.returncode)

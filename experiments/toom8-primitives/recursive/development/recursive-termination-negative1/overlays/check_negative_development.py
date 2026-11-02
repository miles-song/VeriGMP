from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
S=Path(__file__).resolve().parent;O=S/'development/recursive-termination-negative1';O.mkdir(parents=True,exist_ok=False);snap=O/'inputs'
paths=sorted(p for p in (S/'candidate/native').rglob('*') if p.is_file())+[Path(__file__),S/'origin.json']
for p in paths:
    d=snap/p.relative_to(S);d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
target=snap/'candidate/native/verified/toom8_recursive_producer.rs';raw=target.read_bytes();before=b'decreases a.len(),1nat,';after=b'decreases a.len(),9nat,'
assert raw.count(before)==1;target.write_bytes(raw.replace(before,after))
hashes={p.relative_to(snap).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.rglob('*') if p.is_file()}
cmd=[os.environ['VERUS_BIN'],str(snap/'candidate/native/lib.rs'),'--crate-name','toom8_recursive_product_candidate','--crate-type','lib','--verify-module','toom8_recursive_dyadic_producer','--multiple-errors','0']
r={'status':'running','purpose':'Deliberate helper-rank increase must fail actual caller termination; discovery only, not final gate acceptance.','command':cmd,'source_sha256':hashes,'changed_source':'candidate/native/verified/toom8_recursive_producer.rs','original_source_sha256':hashlib.sha256(raw).hexdigest(),'before':before.decode(),'after':after.decode(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'benchmark_run':False}
(O/'report.json').write_text(json.dumps(r,indent=2)+'\n')
p=subprocess.run(cmd,cwd=snap/'candidate',capture_output=True,text=True);log=p.stdout+p.stderr;(O/'proof.log').write_text(log)
r.update(status='diagnostic_recorded',returncode=p.returncode,log_sha256=hashlib.sha256((O/'proof.log').read_bytes()).hexdigest(),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(O/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(log);print('raw_returncode',p.returncode)

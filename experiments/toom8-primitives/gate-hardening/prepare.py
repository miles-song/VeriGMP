"""Reconstruct one repaired checker snapshot using only public archived files."""
from pathlib import Path,PurePosixPath
import argparse,datetime,hashlib,json,os,subprocess,sys
A=Path(__file__).resolve().parent;ARCHIVES=A.parent
parser=argparse.ArgumentParser();parser.add_argument('--feature',required=True,choices=['wide-odd','newton']);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
index=json.loads((A/'index.json').read_text());feature=index['features'][args.feature];out=args.output.resolve()
if out.exists():raise SystemExit('Choose a new output directory')
out.mkdir(parents=True,exist_ok=False);sources={}
for name,identity in feature['source_map'].items():
    source=(ARCHIVES/identity['archive_path']).resolve()
    if not source.is_relative_to(ARCHIVES.resolve()):raise ValueError('Source leaves archive root')
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!=identity['published_sha256']:raise ValueError('Source hash mismatch '+name)
    relative=PurePosixPath(name)
    if not relative.parts or relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError('Unsafe destination name')
    target=(out/Path(*relative.parts)).resolve()
    if not target.is_relative_to(out):raise ValueError('Destination leaves output directory')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);sources[name]=digest
report={'status':'accepted_code_and_public_provenance_reconstructed','feature':args.feature,
    'accepted_gate':feature['accepted_gate'],'original_verification_sha256':feature['original_verification_sha256'],
    'source_sha256':sources,'redacted_provenance_inputs':[n for n,v in feature['source_map'].items() if not v['bytes_exact']],
    'fresh_verification':'not_run','benchmark_run':False}
(out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
if args.verify:
    if os.name!='posix' or 'VERUS_BIN' not in os.environ:raise SystemExit('Fresh verification requires Linux, the pinned toolchain, and VERUS_BIN')
    tag='public-replay-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    result=subprocess.run([sys.executable,str(out/feature['checker']),tag],cwd=out)
    report['fresh_verification']='pass' if result.returncode==0 else 'failed';report['fresh_gate']=tag
    (out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    if result.returncode:raise SystemExit(result.returncode)
print(json.dumps({'status':report['status'],'feature':args.feature,'files':len(sources),'fresh_verification':report['fresh_verification'],'redacted_provenance_inputs':report['redacted_provenance_inputs']}))

"""Reconstruct the accepted public source snapshot and optionally run a fresh gate."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent

def destination(out,name):
    relative=PurePosixPath(name)
    if not relative.parts or relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError('Unsafe destination name')
    target=(out/Path(*relative.parts)).resolve()
    if not target.is_relative_to(out):raise ValueError('Destination leaves output directory')
    return target

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    out=args.output.resolve()
    if out.exists():raise ValueError('Refusing to overwrite a stage')
    verification=json.loads((HERE/'evidence/verification.json').read_bytes())
    targets={name:destination(out,name) for name in verification['source_sha256']}
    from audit import audit,captured,read
    audit();out.mkdir(parents=True,exist_ok=False)
    for name,digest in verification['source_sha256'].items():
        raw=captured(name)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Source identity mismatch')
        targets[name].parent.mkdir(parents=True,exist_ok=True);targets[name].write_bytes(raw)
    result={'status':'exact_source_reconstructed','files':len(targets),'accepted_original_gate_sha256':read('publication.json')['accepted_gate_original_sha256'],'fresh_verification':'not_run','benchmark_run':False}
    try:
        if args.verify:
            if os.name!='posix' or not os.environ.get('VERUS_BIN'):raise ValueError('Fresh verification requires Linux and the pinned VERUS_BIN')
            result['fresh_verification']='running'
            subprocess.run([sys.executable,str(out/'check_interpolation.py'),'public-reproduction'],cwd=out,check=True)
            result['fresh_verification']='pass'
    except Exception as error:
        result.update(status='error',error=f'{type(error).__name__}: {error}')
        if result['fresh_verification']=='running':result['fresh_verification']='failed'
        raise
    finally:
        (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()

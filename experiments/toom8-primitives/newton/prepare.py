"""Reconstruct the accepted code and explicitly redacted provenance bundle and optionally verify it anew."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
from audit import HERE,audit,read,safe
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--verify',action='store_true');args=p.parse_args()
    audit();out=args.output.resolve()
    if out.exists():raise ValueError('Refusing to overwrite a stage')
    v=read('evidence/verification.json');out.mkdir(parents=True)
    for name,digest in v['source_sha256'].items():
        raw=safe(name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=read('publication.json')['files'][name]['published_sha256']:raise ValueError('Source identity mismatch')
        target=(out/name).resolve()
        if not target.is_relative_to(out):raise ValueError('Unsafe output path')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    result={'status':'accepted_code_and_redacted_provenance_reconstructed','files':len(v['source_sha256']),'accepted_original_gate_sha256':read('publication.json')['accepted_gate_original_sha256'],'fresh_verification':'not_run','benchmark_run':False,'redacted_provenance_inputs':read('publication.json')['redacted_provenance_inputs']}
    try:
        if args.verify:
            if not os.environ.get('VERUS_BIN'):raise ValueError('Set VERUS_BIN to the pinned verifier')
            result['fresh_verification']='running'
            subprocess.run([sys.executable,out/'check_newton.py','public-reproduction'],cwd=out,check=True)
            result['fresh_verification']='pass'
    except Exception as error:
        result.update(status='error',error=f'{type(error).__name__}: {error}')
        if result['fresh_verification']=='running':result['fresh_verification']='error'
        raise
    finally:(out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

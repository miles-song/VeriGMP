"""Reconstruct exact historical source bytes in a fresh, isolated directory.

Preparation and archive audit do not constitute re-verification. --verify reruns
the historical same-source gate. --benchmark implies --verify and records two
new complete runs, with no retry selected by favorable performance outcomes.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
from audit import audit,safe,HERE,BASE

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('variant',choices=['double-carry','single-carry','split-slow-path'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--benchmark',action='store_true')
    args=parser.parse_args();audit();archive=HERE/args.variant
    output=args.output.resolve()
    if output.exists():raise ValueError('Refusing to overwrite an existing stage')
    repo=HERE.parents[1]
    subprocess.run(['git','cat-file','-e',BASE+'^{commit}'],cwd=repo,check=True)
    verification=json.loads((archive/'evidence/verification.json').read_text())
    publication=json.loads((archive/'publication.json').read_text())
    output.mkdir(parents=True)
    for relative,wanted in verification['source_sha256'].items():
        if relative.startswith(('baseline/','candidate/')):
            side,source=relative.split('/',1)
            if not source.startswith(('native/','scripts/')):raise ValueError('Unexpected source namespace')
            overlay=archive/'overlay'/source
            git_bytes=subprocess.check_output(['git','show',BASE+':'+source],cwd=repo)
            original=archive/'baseline-byte-overrides'/source
            baseline_bytes=original.read_bytes() if original.exists() else git_bytes
            if baseline_bytes.replace(b'\r\n',b'\n')!=git_bytes.replace(b'\r\n',b'\n'):raise ValueError('Baseline source differs from commit')
            raw=overlay.read_bytes() if side=='candidate' and overlay.exists() else baseline_bytes
            candidates=[raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
            matching=[data for data in candidates if sha(data)==wanted]
            if not matching:raise ValueError('Cannot reconstruct exact source: '+relative)
            data=matching[0]
        else:
            data=safe(archive,relative).read_bytes()
            if sha(data)!=wanted:raise ValueError('Historical script bytes differ')
        target=safe(output,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for name in ['time_verified.py','measure_interpolation.py','audit_small_paths.py','audit_split_mechanism.py']:
        if (archive/name).exists():shutil.copyfile(archive/name,output/name)
    # The continuous-session controller was recorded with the third candidate;
    # fresh reproduction applies the same preflight to every candidate.
    shutil.copyfile(HERE/'split-slow-path/run_confirmations.py',output/'run_confirmations.py')
    checked={p:sha(safe(output,p).read_bytes()) for p in verification['source_sha256']}
    if checked!=verification['source_sha256']:raise ValueError('Reconstructed snapshot mismatch')
    result={'status':'exact_source_reconstructed','variant':args.variant,'baseline_commit':BASE,'source_files':len(checked),
            'historical_original_gate_sha256':publication['historical_verification_original_sha256'],
            'fresh_verification_run':False,'fresh_benchmark_run':False}
    (output/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.verify or args.benchmark:
        if not os.environ.get('VERUS_BIN'):raise ValueError('Set VERUS_BIN to the pinned installed verifier')
        subprocess.run([sys.executable,output/'check.py'],cwd=output,check=True)
        result['fresh_verification_run']=True
    if args.benchmark:
        subprocess.run([sys.executable,output/'run_confirmations.py'],cwd=output,check=True)
        result['fresh_benchmark_run']=True
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

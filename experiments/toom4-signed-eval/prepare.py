"""Reconstruct exact frozen sources; optionally rerun proof and two benchmarks."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from audit import audit, safe, HERE, BASE


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    audit(require_preparation_record=False)
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Refusing to overwrite an existing stage')
    repo = HERE.parents[1]
    subprocess.run(['git', 'cat-file', '-e', BASE + '^{commit}'], cwd=repo, check=True)
    verification = json.loads((HERE / 'evidence/verification.json').read_text())
    publication = json.loads((HERE / 'publication.json').read_text())
    output.mkdir(parents=True)
    for relative, wanted in verification['source_sha256'].items():
        if relative.startswith(('baseline/', 'previous/', 'candidate/')):
            side, source = relative.split('/', 1)
            if not source.startswith(('native/', 'scripts/')):
                raise ValueError('Unexpected source namespace')
            overlay = safe(HERE / 'overlay' / side, source)
            if side != 'baseline' and overlay.exists():
                raw = overlay.read_bytes()
            else:
                git_bytes = subprocess.check_output(['git', 'show', BASE + ':' + source], cwd=repo)
                override = safe(HERE / 'baseline-byte-overrides', source)
                raw = override.read_bytes() if override.exists() else git_bytes
                if raw.replace(b'\r\n', b'\n') != git_bytes.replace(b'\r\n', b'\n'):
                    raise ValueError('Baseline source differs from commit')
            choices = [raw, raw.replace(b'\r\n', b'\n'), raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')]
            matching = [data for data in choices if sha(data) == wanted]
            if not matching:
                raise ValueError('Cannot reconstruct exact source: ' + relative)
            data = matching[0]
        else:
            data = safe(HERE, relative).read_bytes()
            if sha(data) != wanted:
                raise ValueError('Historical script bytes differ')
        path = safe(output, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    actual = {path: sha(safe(output, path).read_bytes()) for path in verification['source_sha256']}
    if actual != verification['source_sha256']:
        raise ValueError('Reconstructed snapshot mismatch')
    result = {'status': 'exact_source_reconstructed', 'baseline_commit': BASE,
        'source_files': len(actual), 'historical_original_gate_sha256': publication['historical_verification_original_sha256'],
        'fresh_verification_status': 'not_run', 'fresh_benchmark_status': 'not_run'}
    try:
        if args.verify or args.benchmark:
            if not os.environ.get('VERUS_BIN'):
                raise ValueError('Set VERUS_BIN to the pinned installed verifier')
            result['fresh_verification_status'] = 'running'
            subprocess.run([sys.executable, output / 'check.py'], cwd=output, check=True)
            result['fresh_verification_status'] = 'pass'
        if args.benchmark:
            result['fresh_benchmark_status'] = 'running'
            subprocess.run([sys.executable, output / 'run_confirmations.py'], cwd=output, check=True)
            subprocess.run([sys.executable, output / 'summarize_confirmations.py'], cwd=output, check=True)
            subprocess.run([sys.executable, output / 'compare_confirmations.py'], cwd=output, check=True)
            result['fresh_benchmark_status'] = 'pass'
    except Exception as error:
        result['status'] = 'error'
        for field in ['fresh_verification_status', 'fresh_benchmark_status']:
            if result[field] == 'running':
                result[field] = 'error'
        result['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        (output / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

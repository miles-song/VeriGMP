#!/usr/bin/env python3
"""Run a source-bound gate from a frozen copy of every local input."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
COMMON = [
    'experiments/toom4-scoped/freeze_gate.py',
    'experiments/combination-20261108/common.py',
    *['experiments/packed-convolution/' + name for name in
      ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')],
]
INPUTS = {
    'oracle': ['experiments/toom4-scoped/check_oracle.py', 'experiments/toom4-scoped/runner.rs',
               'experiments/toom4-entry/oracle.py', 'scripts/verify_toom.py',
               'scripts/verify_multiply.py', 'scripts/verify_limbs.py'],
    'mutations': ['experiments/toom4-scoped/check_mutations.py', 'experiments/toom4-entry/mutations.json'],
    'codegen': ['experiments/toom4-scoped/check_codegen.py',
                'experiments/toom4-entry/overlay/candidate/native/toom4_codegen.rs',
                'scripts/verify_toom.py', 'scripts/verify_multiply.py', 'scripts/verify_limbs.py'],
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def manifest(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def write(path, report):
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gate', choices=INPUTS)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof, out = args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    target = out / 'frozen-gate.json'
    report = {'status': 'running', 'gate': args.gate, 'benchmark_run': False}
    write(target, report)
    try:
        proof_file = proof / 'verification.json'
        data = json.loads(proof_file.read_text())
        report['proof_sha256'] = sha(proof_file)
        if data['status'] != 'full_library_pass':
            raise RuntimeError('full library proof missing')
        native = manifest(ROOT / 'native')
        if {'native/' + k: v for k, v in native.items()} != data['native_sha256']:
            raise RuntimeError('workspace native differs from proof')
        source = out / 'source'
        shutil.copytree(proof / 'snapshot/native', source / 'native')
        inputs = sorted(set(COMMON + INPUTS[args.gate]))
        original = {name: sha(ROOT / name) for name in inputs}
        for name in inputs:
            dest = source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        frozen = manifest(source)
        if ({'native/' + k: v for k, v in native.items()} !=
                {k: v for k, v in frozen.items() if k.startswith('native/')}):
            raise RuntimeError('frozen native differs from proof')
        if any(frozen[name] != digest for name, digest in original.items()):
            raise RuntimeError('frozen gate source differs')
        report['frozen_source_sha256'] = frozen
        report['python'] = {'path': sys.executable, 'sha256': sha(Path(sys.executable).resolve()),
                            'version': sys.version}
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', RAYON_NUM_THREADS='2', OMP_NUM_THREADS='2')
        script = source / 'experiments/toom4-scoped' / ('check_' + args.gate + '.py')
        command = [sys.executable, str(script), '--proof', str(proof), '--output', str(out / 'gate')]
        report['argv'] = command
        write(target, report)
        result = subprocess.run(command, cwd=source, env=env, capture_output=True, timeout=2400)
        (out / 'stdout.log').write_bytes(result.stdout)
        (out / 'stderr.log').write_bytes(result.stderr)
        report['returncode'] = result.returncode
        report['stdout_sha256'] = sha(out / 'stdout.log')
        report['stderr_sha256'] = sha(out / 'stderr.log')
        if result.returncode:
            raise RuntimeError('frozen gate failed')
        if manifest(source) != frozen or manifest(ROOT / 'native') != native:
            raise RuntimeError('frozen or workspace native source changed during gate')
        if any(sha(ROOT / name) != digest for name, digest in original.items()):
            raise RuntimeError('workspace gate input changed during gate')
        if sha(proof_file) != report['proof_sha256']:
            raise RuntimeError('proof report changed during gate')
        report['gate_report_sha256'] = sha(out / 'gate' / (args.gate + '.json'))
        report['status'] = 'frozen_gate_pass'
        write(target, report)
        print(json.dumps({'status': report['status'], 'gate': args.gate}, indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write(target, report)
        raise


if __name__ == '__main__':
    main()

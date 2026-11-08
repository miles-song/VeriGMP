#!/usr/bin/env python3
"""Freeze all local proof inputs before verifying a source snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
INPUTS = [
    'experiments/toom4-scoped/freeze_proof.py',
    'experiments/toom4-scoped/prove.py',
    'experiments/combination-20261108/common.py',
    *['experiments/packed-convolution/' + name for name in
      ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')],
]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def manifest(root):
    return {path.relative_to(root).as_posix(): sha(path) for path in sorted(root.rglob('*')) if path.is_file()}


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def head(root, env):
    code = ("import sys;sys.path.insert(0,sys.argv[1]);from common import git;"
            "head=git('rev-parse','HEAD').decode().strip();"
            "git('merge-base','--is-ancestor','2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba',head);print(head)")
    return subprocess.check_output([sys.executable, '-c', code, str(root / 'experiments/combination-20261108')],
                                   cwd=root, env=env, timeout=60, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report_path = out / 'frozen-proof.json'
    report = dict(status='running', benchmark_run=False)
    write(report_path, report)
    try:
        pointer = ROOT / '.git'
        if not pointer.is_file():
            raise RuntimeError('a linked Git worktree pointer is required')
        native = manifest(ROOT / 'native')
        original = {name: sha(ROOT / name) for name in INPUTS}
        original['.git'] = sha(pointer)
        source = out / 'source'
        shutil.copytree(ROOT / 'native', source / 'native')
        for name in INPUTS + ['.git']:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        frozen = manifest(source)
        if ({'native/' + key: value for key, value in native.items()} !=
                {key: value for key, value in frozen.items() if key.startswith('native/')}):
            raise RuntimeError('frozen native source differs')
        if any(frozen[name] != digest for name, digest in original.items()):
            raise RuntimeError('frozen proof helper differs')
        report['frozen_source_sha256'] = frozen
        report['python'] = {'path': sys.executable, 'sha256': sha(Path(sys.executable).resolve()),
                            'version': sys.version}
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', RAYON_NUM_THREADS='2', OMP_NUM_THREADS='2',
                   GIT_OPTIONAL_LOCKS='0')
        report['git_head'] = head(ROOT, env)
        if head(source, env) != report['git_head']:
            raise RuntimeError('frozen source resolves a different Git head')
        script = source / 'experiments/toom4-scoped/prove.py'
        if args.prepare_only:
            report['status'] = 'prepared_no_proof'
            write(report_path, report)
            print(json.dumps({'status': report['status']}))
            return
        command = [sys.executable, str(script), '--deps-root', str(args.deps_root.resolve()),
                   '--output', str(out / 'gate')]
        report['argv'] = command
        write(report_path, report)
        result = subprocess.run(command, cwd=source, env=env, capture_output=True, timeout=2400)
        (out / 'stdout.log').write_bytes(result.stdout)
        (out / 'stderr.log').write_bytes(result.stderr)
        report['returncode'] = result.returncode
        report['stdout_sha256'] = sha(out / 'stdout.log')
        report['stderr_sha256'] = sha(out / 'stderr.log')
        if result.returncode:
            raise RuntimeError('frozen proof failed')
        if manifest(source) != frozen or manifest(ROOT / 'native') != native:
            raise RuntimeError('frozen or workspace native source changed during proof')
        if any(sha(ROOT / name) != digest for name, digest in original.items()):
            raise RuntimeError('workspace proof input changed during proof')
        if sha(Path(sys.executable).resolve()) != report['python']['sha256']:
            raise RuntimeError('Python executable changed during proof')
        if head(ROOT, env) != report['git_head'] or head(source, env) != report['git_head']:
            raise RuntimeError('Git head changed during proof')
        report['gate_report_sha256'] = sha(out / 'gate/verification.json')
        report['status'] = 'frozen_proof_pass'
        write(report_path, report)
        print(json.dumps({'status': report['status']}))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write(report_path, report)
        raise


if __name__ == '__main__':
    main()

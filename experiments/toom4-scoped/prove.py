#!/usr/bin/env python3
"""Verify and compile one recorded Toom-4 candidate source snapshot."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/combination-20261108'))
from common import command_runner, file_sha, git, manifest, mapping_sha, pinned_tools, positive, write_json

BASE = '2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report = dict(status='running', benchmark_run=False, base=BASE, commands=[],
                  scope='complete native library; remaining acceptance gates pending')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', RAYON_NUM_THREADS='2', OMP_NUM_THREADS='2')
    run = command_runner(out, report, env)
    write_json(out / 'verification.json', report)
    try:
        cpus = sorted(os.sched_getaffinity(0))
        if len(cpus) < 2:
            raise RuntimeError('two available CPUs are required')
        os.sched_setaffinity(0, cpus[-2:])
        report['cpu_affinity'] = sorted(os.sched_getaffinity(0))
        head = git('rev-parse', 'HEAD').decode().strip()
        try:
            git('merge-base', '--is-ancestor', BASE, head)
        except subprocess.CalledProcessError as error:
            raise RuntimeError('source is not based on the expected Git base: ' + head) from error
        report['git_head'] = head
        report['git_status'] = git('status', '--porcelain', '--untracked-files=all').decode().splitlines()
        source_hashes = manifest(ROOT)
        report['native_sha256'] = source_hashes
        report['native_manifest_sha256'] = mapping_sha(source_hashes)
        report['gate_sha256'] = file_sha(Path(__file__).resolve())
        report['gate_helper_sha256'] = {str(p.relative_to(ROOT)): file_sha(p) for p in (
            ROOT / 'experiments/combination-20261108/common.py',
            ROOT / 'experiments/packed-convolution/layout_verify.py')}
        snapshot = out / 'snapshot'
        shutil.copytree(ROOT / 'native', snapshot / 'native')
        if manifest(snapshot) != source_hashes:
            raise RuntimeError('snapshot differs from source')
        forbidden = re.compile(r'\b(?:assume|admit|axiom)\s*\(|verifier::(?:external_body|external_fn_specification|external|trusted|verify\s*=\s*false)')
        for path in (snapshot / 'native').rglob('*.rs'):
            if forbidden.search(path.read_text(encoding='utf-8')):
                raise RuntimeError('proof escape: ' + str(path.relative_to(snapshot)))
        verifier, pin, report['tools'] = pinned_tools(args.deps_root.resolve(), snapshot / 'native', run, env)
        rustc = Path(subprocess.check_output(['rustup', 'which', '--toolchain', pin['rust_toolchain'], 'rustc'],
                                             env=env, text=True).strip()).resolve()
        report['tools']['rustc_path'] = str(rustc)
        report['tools']['rustc_sha256'] = file_sha(rustc)
        rustc_version = run([rustc, '-vV'], 'rustc-version')
        report['tools']['rustc_version'] = (rustc_version.stdout + rustc_version.stderr).decode()
        linked = run(['ldd', rustc], 'rustc-linked')
        libraries = [Path(p).resolve() for p in re.findall(r'=>\s+(\S+)\s+\(', (linked.stdout + linked.stderr).decode())]
        report['tools']['rustc_linked_sha256'] = {str(p): file_sha(p) for p in libraries}
        result = run([verifier, 'native/lib.rs', '--crate-name', 'verigmp', '--crate-type', 'lib',
                      '--num-threads', '2', '--no-cheating', '--compile', '-O',
                      '--export', out / 'verigmp.vir', '-o', out / 'libverigmp.rlib'],
                     'library', snapshot, timeout=1800)
        report['verified_items'] = positive(result.returncode, (result.stdout + result.stderr).decode())
        if manifest(ROOT) != source_hashes or manifest(snapshot) != source_hashes:
            raise RuntimeError('source changed during verification')
        if file_sha(rustc) != report['tools']['rustc_sha256']:
            raise RuntimeError('rustc changed during verification')
        if any(file_sha(p) != digest for p, digest in report['tools']['rustc_linked_sha256'].items()):
            raise RuntimeError('rustc runtime library changed during verification')
        for name, digest in report['tools']['sha256'].items():
            if file_sha(verifier.parent / name) != digest:
                raise RuntimeError('verifier tool changed during verification: ' + name)
        report['exports_sha256'] = {name: file_sha(out / name) for name in ('libverigmp.rlib', 'verigmp.vir')}
        report['status'] = 'full_library_pass'
        write_json(out / 'verification.json', report)
        print(json.dumps({k: report[k] for k in ('status', 'verified_items', 'native_manifest_sha256')}, indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(out / 'verification.json', report)
        raise


if __name__ == '__main__':
    main()

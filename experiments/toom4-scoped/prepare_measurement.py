#!/usr/bin/env python3
"""Build and functionally check the comparator; never runs timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/combination-20261108'))
from common import file_sha, manifest, write_json
from measure_window import expected_shapes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof, out = args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report = {'status': 'running', 'benchmark_run': False, 'commands': []}
    target = out / 'preparation.json'
    write_json(target, report)
    try:
        proof_file = proof / 'verification.json'
        data = json.loads(proof_file.read_text())
        report['proof_report_sha256'] = file_sha(proof_file)
        if data['status'] != 'full_library_pass' or manifest(ROOT) != data['native_sha256']:
            raise RuntimeError('workspace does not match complete proof')
        if manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('proof snapshot differs')
        for name, digest in data['exports_sha256'].items():
            if file_sha(proof / name) != digest:
                raise RuntimeError('proof export changed: ' + name)
        verifier = Path(data['commands'][0]['argv'][0])
        rustc = Path(data['tools']['rustc_path'])
        if file_sha(rustc) != data['tools']['rustc_sha256']:
            raise RuntimeError('compiler differs from proof')
        for name, digest in data['tools']['sha256'].items():
            if file_sha(verifier.parent / name) != digest:
                raise RuntimeError('verifier dependency changed: ' + name)
        files = [Path(__file__).resolve(), ROOT / 'experiments/toom4-scoped/measure.rs',
                 ROOT / 'experiments/toom4-scoped/measurement-protocol.json',
                 ROOT / 'experiments/toom4-scoped/measure_window.py',
                 ROOT / 'experiments/combination-20261108/common.py',
                 *[ROOT / 'experiments/packed-convolution' / name for name in
                   ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')]]
        report['source_sha256'] = {str(path.relative_to(ROOT)): file_sha(path) for path in files}
        env = dict(os.environ, **data['tools']['environment'], PYTHONDONTWRITEBYTECODE='1',
                   RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1')

        def run(name, argv):
            result = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env, capture_output=True, timeout=300)
            (out / (name + '.stdout.log')).write_bytes(result.stdout)
            (out / (name + '.stderr.log')).write_bytes(result.stderr)
            report['commands'].append({'name': name, 'argv': list(map(str, argv)), 'returncode': result.returncode})
            if result.returncode:
                raise RuntimeError(name + ' failed')
            return result.stdout.decode()

        binary = out / 'measure'
        run('build', [rustc, '--edition=2021', ROOT / 'experiments/toom4-scoped/measure.rs', '-O',
                      '-C', 'codegen-units=1', '--extern', 'verigmp=' + str(proof / 'libverigmp.rlib'),
                      '-L', 'dependency=' + str(verifier.parent), '-o', binary])
        abi = out / 'gmp-abi'
        cxx = Path(shutil.which('c++')).resolve()
        run('gmp-abi-build', [cxx, '-std=c++17', ROOT / 'native/controls/gmp_abi.cpp', '-lgmp', '-o', abi])
        report['gmp_abi'] = run('gmp-abi', [abi]).strip()
        report['self_test'] = run('self-test', [binary, '--self-test']).strip()
        shape_lines = run('shapes', [binary, '--list']).splitlines()
        shapes = [tuple(map(int, line.split(','))) for line in shape_lines]
        if len(shapes) != len(set(shapes)) or set(shapes) != expected_shapes():
            raise RuntimeError('invalid shape list')
        report['shapes'] = shapes
        linked = run('linked', ['ldd', binary])
        paths = [Path(p).resolve() for p in re.findall(r'=>\s+(\S+)\s+\(', linked)]
        paths += [Path(p).resolve() for p in re.findall(r'(?m)^\s*(/\S+)\s+\(', linked)]
        if len([p for p in paths if p.name.startswith('libgmp')]) != 1:
            raise RuntimeError('GMP linkage ambiguous')
        report['identity_sha256'] = {str(p): file_sha(p) for p in sorted(set(paths + [binary, abi, rustc, cxx]))}
        report['native_manifest_sha256'] = data['native_manifest_sha256']
        report['proof_exports_sha256'] = data['exports_sha256']
        if manifest(ROOT) != data['native_sha256'] or manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('native source changed during preparation')
        if file_sha(proof_file) != report['proof_report_sha256']:
            raise RuntimeError('proof report changed during preparation')
        if any(file_sha(ROOT / name) != digest for name, digest in report['source_sha256'].items()):
            raise RuntimeError('measurement source changed during preparation')
        if any(file_sha(path) != digest for path, digest in report['identity_sha256'].items()):
            raise RuntimeError('binary, compiler or runtime changed during preparation')
        if any(file_sha(proof / name) != digest for name, digest in data['exports_sha256'].items()):
            raise RuntimeError('proof export changed during preparation')
        report['status'] = 'prepared_no_timing'
        write_json(target, report)
        print(json.dumps({'status': report['status'], 'shapes': len(shapes), 'self_test': report['self_test']}, indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(target, report)
        raise


if __name__ == '__main__':
    main()

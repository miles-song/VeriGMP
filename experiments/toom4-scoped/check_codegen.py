#!/usr/bin/env python3
"""Inspect optimized code generated from the proved source snapshot."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/combination-20261108'))
sys.path.insert(0, str(ROOT / 'scripts'))
from common import file_sha, manifest, positive, write_json
from verify_toom import reachable_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof, out = args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report = dict(status='running', benchmark_run=False,
                  scope='source-identical standalone codegen harnesses; not the exported library binary')
    write_json(out / 'codegen.json', report)
    try:
        cpus = sorted(os.sched_getaffinity(0))
        if len(cpus) < 2:
            raise RuntimeError('two available CPUs are required')
        os.sched_setaffinity(0, cpus[-2:])
        report['cpu_affinity'] = sorted(os.sched_getaffinity(0))
        proof_path = proof / 'verification.json'
        data = json.loads(proof_path.read_text())
        report['proof_report_sha256'] = file_sha(proof_path)
        if data['status'] != 'full_library_pass' or manifest(ROOT) != data['native_sha256']:
            raise RuntimeError('current source lacks a matching complete proof')
        if manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('proof snapshot differs')
        verifier = Path(data['commands'][0]['argv'][0])
        for name, digest in data['tools']['sha256'].items():
            if file_sha(verifier.parent / name) != digest:
                raise RuntimeError('verifier differs: ' + name)
        if file_sha(Path(data['tools']['rustc_path'])) != data['tools']['rustc_sha256']:
            raise RuntimeError('rustc differs from proof')
        env = dict(os.environ, **data['tools']['environment'], PYTHONDONTWRITEBYTECODE='1',
                   RAYON_NUM_THREADS='2', OMP_NUM_THREADS='2')
        driver = ROOT / 'experiments/toom4-entry/overlay/candidate/native/toom4_codegen.rs'
        sources = [Path(__file__).resolve(), driver, ROOT / 'scripts/verify_toom.py',
                   ROOT / 'scripts/verify_multiply.py', ROOT / 'scripts/verify_limbs.py',
                   ROOT / 'experiments/combination-20261108/common.py',
                   *[ROOT / 'experiments/packed-convolution' / name for name in
                     ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')]]
        report['test_source_sha256'] = {str(p.relative_to(ROOT)): file_sha(p) for p in sources}
        report['variants'] = {}
        for label in ['candidate', 'baseline']:
            work = out / label
            shutil.copytree(proof / 'snapshot', work)
            if manifest(work) != data['native_sha256']:
                raise RuntimeError('codegen source copy differs: ' + label)
            text = driver.read_text(encoding='utf-8')
            if label == 'baseline':
                if text.count('toom4_candidate::mul_mod') != 1 or text.count('toom4_candidate::square_mod') != 1:
                    raise RuntimeError('baseline driver anchors differ')
                text = text.replace('toom4_candidate::mul_mod', 'arithmetic::mul_mod')
                text = text.replace('toom4_candidate::square_mod', 'arithmetic::square_mod')
            path = work / 'native/toom4_codegen.rs'
            path.write_text(text, encoding='utf-8')
            assembly = out / (label + '.s')
            command = [str(verifier), str(path), '--crate-name', 'scoped_codegen_' + label,
                       '--num-threads', '2', '--no-cheating', '--compile', '-O', '--emit=asm', '-o', str(assembly)]
            result = subprocess.run(command, cwd=work, env=env, capture_output=True, timeout=900)
            (out / (label + '.stdout.log')).write_bytes(result.stdout)
            (out / (label + '.stderr.log')).write_bytes(result.stderr)
            count = positive(result.returncode, (result.stdout + result.stderr).decode())
            inspected = reachable_code(assembly.read_text())
            inspected['scope'] = 'Standalone ' + label + ' product and square entry points'
            names = inspected['reachable_functions']
            if label == 'candidate' and not all(any(required in name for name in names)
                                                 for required in ['toom4_multiply', 'toom4_square']):
                raise RuntimeError('candidate Toom-4 kernels are not reachable')
            if label == 'baseline' and any('toom4_' in name for name in names):
                raise RuntimeError('production baseline unexpectedly reaches Toom-4')
            report['variants'][label] = dict(argv=command, verified_items=count, driver_sha256=file_sha(path),
                                              assembly_sha256=file_sha(assembly), inspection=inspected)
            if {key: value for key, value in manifest(work).items() if key != 'native/toom4_codegen.rs'} != data['native_sha256']:
                raise RuntimeError('source changed during codegen: ' + label)
            write_json(out / 'codegen.json', report)
        if manifest(ROOT) != data['native_sha256'] or manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('source changed during codegen')
        if file_sha(proof_path) != report['proof_report_sha256']:
            raise RuntimeError('proof report changed during codegen')
        if any(file_sha(ROOT / name) != digest for name, digest in report['test_source_sha256'].items()):
            raise RuntimeError('codegen test source changed')
        if any(file_sha(verifier.parent / name) != digest for name, digest in data['tools']['sha256'].items()):
            raise RuntimeError('verifier changed during codegen')
        report['status'] = 'codegen_pass'
        write_json(out / 'codegen.json', report)
        print(json.dumps(dict(status=report['status'], variants=list(report['variants'])), indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(out / 'codegen.json', report)
        raise


if __name__ == '__main__':
    main()

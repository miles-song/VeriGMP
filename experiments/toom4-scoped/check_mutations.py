#!/usr/bin/env python3
"""Reject semantic mutations against an already proved native snapshot."""
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
sys.path.insert(0, str(ROOT / 'experiments/packed-convolution'))
from common import file_sha, manifest, write_json
from verus_logs import self_check, strict_semantic_rejection


def semantic_rejection(text, returncode, module):
    notes = re.findall(r'(?m)^note: verifying module .*$', text)
    expected = 'note: verifying module ' + module
    function_note = re.compile(
        rf'note: verifying module {re.escape(module)}, function '
        rf'verigmp_mutant::{re.escape(module)}::[A-Za-z_][A-Za-z_0-9]*'
    )
    if (not notes or len(set(notes)) != len(notes)
            or any(note != expected and not function_note.fullmatch(note) for note in notes)):
        return False
    normalized = re.sub(r'(?m)^note: verifying module .*$', '', text)
    return strict_semantic_rejection(normalized + '\n' + expected + '\n', returncode, module)


def check_classifier():
    summary = ('verification results:: 0 verified, 1 errors '
               '(partial verification with `--verify-*`)\n')
    diagnostic = 'error: precondition not satisfied\nerror: aborting due to 1 previous error\n'
    note = 'note: verifying module toom4_multiply'
    function = note + ', function verigmp_mutant::toom4_multiply::full'
    regular = summary + note + '\n' + diagnostic
    single = summary + function + '\n' + diagnostic
    both = summary + note + '\n' + function + '\n' + diagnostic
    assert semantic_rejection(regular, 1, 'toom4_multiply')
    assert semantic_rejection(single, 1, 'toom4_multiply')
    assert semantic_rejection(both, 1, 'toom4_multiply')
    assert not semantic_rejection(single, 0, 'toom4_multiply')
    assert not semantic_rejection(single, 1, 'other_module')
    assert not semantic_rejection(single.replace('verigmp_mutant::', 'other_crate::'), 1, 'toom4_multiply')
    assert not semantic_rejection(single.replace('::toom4_multiply::', '::other_module::'), 1, 'toom4_multiply')
    assert semantic_rejection(single + note + '\n', 1, 'toom4_multiply')
    assert not semantic_rejection(both + function + '\n', 1, 'toom4_multiply')
    assert not semantic_rejection(both + 'note: verifying module wrong_module\n', 1, 'toom4_multiply')
    assert not semantic_rejection(single.replace('full', 'full::nested'), 1, 'toom4_multiply')
    assert not semantic_rejection(single + 'error: unexpected token\n', 1, 'toom4_multiply')
    assert not semantic_rejection(single + 'error: verification timed out\n', 1, 'toom4_multiply')
    assert not semantic_rejection(single + 'error[E0308]: mismatched types\n', 1, 'toom4_multiply')
    return {'status': 'pass', 'fixtures': 14,
            'requires_only_unique_exact_module_or_qualified_function_notes': True,
            'retains_existing_strict_semantic_diagnostics': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof, out = args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report = dict(status='running', benchmark_run=False, mutations=[],
                  scope='semantic mutations after complete positive library verification')
    write_json(out / 'mutations.json', report)
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
        mutation_file = ROOT / 'experiments/toom4-entry/mutations.json'
        inputs = [Path(__file__).resolve(), mutation_file, ROOT / 'experiments/combination-20261108/common.py',
                  *[ROOT / 'experiments/packed-convolution' / name for name in
                    ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')]]
        report['test_source_sha256'] = {str(p.relative_to(ROOT)): file_sha(p) for p in inputs}
        mutations = json.loads(mutation_file.read_text())
        mutations += [
            ['toom4_candidate.rs', 'wrong_mid_product_operand',
             'toom_low::modular(dst,a,b,scratch,top,192,128,2);',
             'toom_low::modular(dst,a,a,scratch,top,192,128,2);', 'toom4_candidate'],
            ['toom4_candidate.rs', 'omit_large_square_normalization',
             'toom4_square_low::low(dst,a,scratch,256,64,1);\n    pow2::normalize_top(dst,top);',
             'toom4_square_low::low(dst,a,scratch,256,64,1);', 'toom4_candidate'],
        ]
        report['classifier'] = {'shared': self_check(), 'single_function': check_classifier()}
        work = out / 'working-copy'
        shutil.copytree(proof / 'snapshot', work)
        for file, name, before, after, module in mutations:
            if manifest(work) != data['native_sha256']:
                raise RuntimeError('mutant source was not restored: ' + name)
            source = work / 'native/verified' / file
            original = source.read_bytes()
            text = original.decode().replace('\r\n', '\n')
            if text.count(before) != 1:
                raise RuntimeError('ambiguous mutation anchor: ' + name)
            try:
                source.write_text(text.replace(before, after), encoding='utf-8')
                command = [str(verifier), 'native/lib.rs', '--crate-name', 'verigmp_mutant', '--crate-type', 'lib',
                           '--verify-module', module, '--multiple-errors', '0', '--num-threads', '2', '--no-cheating']
                result = subprocess.run(command, cwd=work, env=env, capture_output=True, timeout=900)
                log = result.stdout + result.stderr
                (out / (name + '.log')).write_bytes(log)
                rejected = semantic_rejection(log.decode(), result.returncode, module)
                report['mutations'].append(dict(name=name, module=module, returncode=result.returncode,
                                                semantically_rejected=rejected, log_sha256=file_sha(out / (name + '.log')),
                                                mutant_sha256=file_sha(source), argv=command))
                write_json(out / 'mutations.json', report)
                if not rejected:
                    raise RuntimeError('mutation was not semantically rejected: ' + name)
            finally:
                source.write_bytes(original)
        if manifest(work) != data['native_sha256'] or manifest(ROOT) != data['native_sha256']:
            raise RuntimeError('source changed during mutation checks')
        if file_sha(proof_path) != report['proof_report_sha256']:
            raise RuntimeError('proof report changed during mutation checks')
        if any(file_sha(ROOT / name) != digest for name, digest in report['test_source_sha256'].items()):
            raise RuntimeError('mutation test source changed')
        if any(file_sha(verifier.parent / name) != digest for name, digest in data['tools']['sha256'].items()):
            raise RuntimeError('verifier changed during mutation checks')
        report['status'] = 'mutations_pass'
        write_json(out / 'mutations.json', report)
        print(json.dumps(dict(status=report['status'], rejected=len(report['mutations'])), indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(out / 'mutations.json', report)
        raise


if __name__ == '__main__':
    main()

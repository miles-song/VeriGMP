#!/usr/bin/env python3
"""Check the proved candidate library against independent integer oracles."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FEATURE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'experiments/combination-20261108'))
sys.path.insert(0, str(ROOT / 'scripts'))
from common import file_sha, manifest, positive, write_json
from verify_toom import cases as existing_cases


def sha(data):
    return hashlib.sha256(data).hexdigest()


def boundary_cases():
    rng = random.Random(20261109)
    mask = (1 << 64) - 1
    rows = []
    for n in [1, 2, 8, 9, 23, 24, 25, 63, 64, 65, 127, 128, 129,
              191, 192, 193, 255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 1280, 1536, 1792,
              2047, 2048, 2049, 2560, 3072, 3584, 4095, 4096, 4097]:
        vectors = [([0] * n, [mask] * n), ([mask] * n, [mask] * n),
                   ([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(64) for _ in range(n)])]
        for index, (a, b) in enumerate(vectors):
            x = sum(word << (64 * i) for i, word in enumerate(a))
            y = sum(word << (64 * i) for i, word in enumerate(b))
            tops = range(1, 65) if index == 2 and n in [1023, 1024, 1025, 2047, 2048, 2049] else [1, 2, 31, 32, 63, 64]
            for top in tops:
                modulus = 1 << (64 * (n - 1) + top)
                for op, result in [('candidate4', x * y), ('candidate4same', x * x),
                                   ('candidate4square', x * x), ('forced4', x * y),
                                   ('forced4same', x * x), ('forced4square', x * x)]:
                    command = ' '.join(map(str, [op, top, 256, 128, 2, *a, *b]))
                    value = result % modulus
                    expected = ' '.join(str((value >> (64 * i)) & mask) for i in range(n))
                    rows.append((command, expected))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof, out = args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report = dict(status='running', benchmark_run=False, scope='independent integer and boundary tests', commands=[])
    write_json(out / 'oracle.json', report)
    try:
        cpus = sorted(os.sched_getaffinity(0))
        if len(cpus) < 2:
            raise RuntimeError('two available CPUs are required')
        os.sched_setaffinity(0, cpus[-2:])
        report['cpu_affinity'] = sorted(os.sched_getaffinity(0))
        proof_report_path = proof / 'verification.json'
        data = json.loads(proof_report_path.read_text())
        if data['status'] != 'full_library_pass':
            raise RuntimeError('full library proof is not a pass')
        report['proof_report_sha256'] = file_sha(proof_report_path)
        if manifest(ROOT) != data['native_sha256'] or manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('candidate source differs from the proof snapshot')
        for name, digest in data['exports_sha256'].items():
            if file_sha(proof / name) != digest:
                raise RuntimeError('proof export differs: ' + name)
        env = dict(os.environ, **data['tools']['environment'], PYTHONDONTWRITEBYTECODE='1',
                   RAYON_NUM_THREADS='2', OMP_NUM_THREADS='2')
        verifier = Path(data['commands'][0]['argv'][0])
        for name, digest in data['tools']['sha256'].items():
            if file_sha(verifier.parent / name) != digest:
                raise RuntimeError('verifier differs: ' + name)
        if file_sha(Path(data['tools']['rustc_path'])) != data['tools']['rustc_sha256']:
            raise RuntimeError('rustc differs from proof')
        sources = [Path(__file__).resolve(), FEATURE / 'runner.rs', ROOT / 'scripts/verify_toom.py',
                   ROOT / 'scripts/verify_multiply.py', ROOT / 'scripts/verify_limbs.py',
                   ROOT / 'experiments/toom4-entry/oracle.py', ROOT / 'experiments/combination-20261108/common.py',
                   *[ROOT / 'experiments/packed-convolution' / name for name in
                     ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')]]
        report['source_sha256'] = {str(p.relative_to(ROOT)): file_sha(p) for p in sources}
        binary = out / 'oracle-runner'
        command = [str(verifier), str(FEATURE / 'runner.rs'), '--crate-name', 'toom4_scoped_oracle',
                   '--num-threads', '2', '--no-cheating', '--import', 'verigmp=' + str(proof / 'verigmp.vir'),
                   '--extern', 'verigmp=' + str(proof / 'libverigmp.rlib'), '--compile', '-O', '-o', str(binary)]
        built = subprocess.run(command, env=env, cwd=ROOT, capture_output=True, timeout=900)
        (out / 'runner-build.stdout.log').write_bytes(built.stdout)
        (out / 'runner-build.stderr.log').write_bytes(built.stderr)
        report['commands'].append(dict(argv=command, returncode=built.returncode))
        report['verified_callers'] = positive(built.returncode, (built.stdout + built.stderr).decode())
        report['binary_sha256'] = file_sha(binary)
        spec = importlib.util.spec_from_file_location('historical_toom4_oracle', ROOT / 'experiments/toom4-entry/oracle.py')
        old_oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old_oracle)
        legacy, direct, boundary = existing_cases(), old_oracle.cases(), boundary_cases()
        rows = legacy + direct + boundary
        input_bytes = ('\n'.join(row[0] for row in rows) + '\n').encode()
        expected_bytes = ('\n'.join(row[1] for row in rows) + '\n').encode()
        result = subprocess.run([binary], env=env, input=input_bytes, capture_output=True, timeout=900)
        raw = {'input': input_bytes, 'expected': expected_bytes, 'actual': result.stdout, 'stderr': result.stderr}
        report['raw_observations'] = {}
        for name, payload in raw.items():
            path = out / (name + '.txt.gz')
            with path.open('wb') as stream:
                with gzip.GzipFile(filename='', mode='wb', fileobj=stream, compresslevel=1, mtime=0) as compressed:
                    compressed.write(payload)
            report['raw_observations'][name] = dict(file=path.name, sha256=file_sha(path), bytes=len(payload))
        report['oracle'] = dict(existing=len(legacy), forced_toom4=len(direct), dispatch_boundary=len(boundary),
                                input_sha256=sha(input_bytes), expected_sha256=sha(expected_bytes),
                                actual_sha256=sha(result.stdout), stderr_sha256=sha(result.stderr),
                                returncode=result.returncode, boundary_seed=20261109)
        if result.returncode or result.stdout != expected_bytes:
            (out / 'oracle.stderr.log').write_bytes(result.stderr)
            actual_lines, expected_lines = result.stdout.splitlines(), expected_bytes.splitlines()
            for i, (actual, expected) in enumerate(zip(actual_lines, expected_lines)):
                if actual != expected:
                    report['first_mismatch'] = dict(index=i, command_sha256=sha(rows[i][0].encode()),
                                                    actual_sha256=sha(actual), expected_sha256=sha(expected))
                    break
            raise RuntimeError('independent integer oracle mismatch')
        invalid = ['full4 64 23 24 0 1 1', 'squarefull4 64 23 24 0 1 1',
                   'candidate4 0 256 128 2 1 1', 'candidate4square 65 256 128 2 1 1',
                   'forced4 0 256 128 2 1 1', 'forced4square 65 256 128 2 1 1',
                   'shortscratch4 64 24 24 0 1 1', 'weighted4 8 8 0 0 1 1 1 2 3 4',
                   'signed4 2 1 1 1 2 3 4', 'full4 64 24 24 0 1 1 1']
        for i, command in enumerate(invalid):
            result = subprocess.run([binary], env=env, input=(command + '\n').encode(), capture_output=True, timeout=30)
            if result.returncode == 0 or result.stdout.strip():
                raise RuntimeError('invalid command accepted: ' + str(i))
        report['invalid_commands_rejected'] = len(invalid)
        if manifest(ROOT) != data['native_sha256'] or manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('source changed during oracle')
        if file_sha(proof_report_path) != report['proof_report_sha256'] or file_sha(binary) != report['binary_sha256']:
            raise RuntimeError('proof report or runner changed during oracle')
        if any(file_sha(ROOT / name) != digest for name, digest in report['source_sha256'].items()):
            raise RuntimeError('test source changed during oracle')
        if any(file_sha(proof / name) != digest for name, digest in data['exports_sha256'].items()):
            raise RuntimeError('proof export changed during oracle')
        if any(file_sha(verifier.parent / name) != digest for name, digest in data['tools']['sha256'].items()):
            raise RuntimeError('verifier changed during oracle')
        report['status'] = 'oracle_pass'
        write_json(out / 'oracle.json', report)
        print(json.dumps({k: report[k] for k in ('status', 'verified_callers', 'oracle', 'invalid_commands_rejected')}, indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(out / 'oracle.json', report)
        raise


if __name__ == '__main__':
    main()

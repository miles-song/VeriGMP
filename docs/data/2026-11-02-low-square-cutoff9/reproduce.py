#!/usr/bin/env python3
"""Rebuild and measure the frozen public low-square experiment in a new directory."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

DATA = Path(__file__).resolve().parent
PROJECT = DATA.parents[2]
BASELINE = 'c083839dc07f9b0cffea1a52cd6810d817105355'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(directory, normalized=False):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            content = path.read_bytes()
            if normalized:
                content = content.replace(b'\r\n', b'\n')
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(content).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='A new experiment directory; existing paths are refused')
    parser.add_argument('--cpu', type=int, default=0)
    parser.add_argument('--prepare-only', action='store_true', help='Check and assemble frozen sources without compiling or measuring')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit('Refusing to overwrite an existing experiment directory')
    metadata = json.loads((DATA / 'metadata.json').read_text())
    if metadata['baseline_commit'] != BASELINE:
        raise SystemExit('Unexpected baseline identity')
    if any(digest(DATA / p) != h for p, h in metadata['artifact_sha256'].items()):
        raise SystemExit('Frozen evidence or reproduction input changed')
    present = subprocess.run(['git', 'cat-file', '-e', BASELINE + '^{commit}'], cwd=PROJECT, capture_output=True)
    if present.returncode:
        subprocess.run(['git', 'fetch', 'origin', BASELINE], cwd=PROJECT, check=True)
    archive = subprocess.check_output(['git', 'archive', '--format=tar', BASELINE, 'native', 'scripts'], cwd=PROJECT)
    output.mkdir(parents=True)
    baseline = output / 'baseline'
    baseline.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as sources:
        for member in sources:
            target = (baseline / member.name).resolve()
            if not target.is_relative_to(baseline) or not (member.isdir() or member.isfile()):
                raise RuntimeError('Unexpected baseline archive member')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with sources.extractfile(member) as source:
                    target.write_bytes(source.read())
    candidate = output / 'candidate'
    shutil.copytree(baseline, candidate)
    for relative in metadata['candidate_core_sha256_lf']:
        shutil.copy2(DATA / 'candidate' / relative, candidate / relative)
    for name in ['baseline', 'candidate']:
        if source_hashes(output / name, normalized=True) != metadata['source_sha256_lf'][name]:
            raise RuntimeError('Reconstructed source identity differs: ' + name)
    scripts = ['check.py', 'measure.py', 'measure_verified.py', 'summarize.py', 'compare.rs', 'compare_dense.rs']
    for name in scripts:
        shutil.copy2(DATA / name, output / name)
    origin = {'canonical_commit': BASELINE, 'candidate_cutoff': 9,
              'reproduced_from_metadata_sha256': digest(DATA / 'metadata.json'),
              'source_bytes': {name: source_hashes(output / name) for name in ['baseline', 'candidate']}}
    (output / 'origin.json').write_text(json.dumps(origin, indent=2) + '\n')
    preparation = {'status': 'sources_prepared', 'output': str(output),
                   'source_identity_matches_frozen_experiment': True,
                   'verification_run': False, 'benchmark_run': False}
    (output / 'preparation.json').write_text(json.dumps(preparation, indent=2) + '\n')
    print(json.dumps(preparation, indent=2), flush=True)
    if args.prepare_only:
        return
    if not hasattr(os, 'sched_setaffinity') or args.cpu not in os.sched_getaffinity(0):
        raise RuntimeError('Select an available CPU on the pinned Linux x86_64 platform')
    env = dict(os.environ)
    if (PROJECT / 'deps/cargo/bin/rustup').is_file():
        env.setdefault('CARGO_HOME', str(PROJECT / 'deps/cargo'))
        env.setdefault('RUSTUP_HOME', str(PROJECT / 'deps/rustup'))
    if 'CARGO_HOME' in env:
        env['PATH'] = str(Path(env['CARGO_HOME']) / 'bin') + os.pathsep + env['PATH']
    verifier = Path(env.get('VERUS_BIN', PROJECT / 'deps/verus/verus-x86-linux/verus')).resolve()
    if not verifier.is_file():
        raise RuntimeError('Run python3 scripts/setup_verus.py first, or supply VERUS_BIN for the pinned verifier')
    env['VERUS_BIN'] = str(verifier)
    os.sched_setaffinity(0, {args.cpu})
    abi = output / 'gmp-abi'
    built = subprocess.run(['c++', '-std=c++17', baseline / 'native/controls/gmp_abi.cpp', '-lgmp', '-o', abi],
                           cwd=output, env=env, text=True, capture_output=True)
    (output / 'gmp-abi-build.log').write_text(built.stdout + built.stderr)
    if built.returncode:
        raise RuntimeError('The installed GMP header does not satisfy the benchmark ABI')
    checked = subprocess.run([abi], cwd=output, env=env, text=True, capture_output=True)
    (output / 'gmp-abi.log').write_text(checked.stdout + checked.stderr)
    if checked.returncode:
        raise RuntimeError('The installed GMP runtime does not satisfy the benchmark ABI')
    subprocess.run([sys.executable, output / 'check.py'], cwd=output, env=env, check=True)
    for tag in ['default1', 'dense1', 'default2', 'dense2']:
        command = [sys.executable, output / 'measure_verified.py', '--tag', tag, '--cpu', str(args.cpu)]
        if tag.startswith('dense'):
            command.append('--dense')
        subprocess.run(command, cwd=output, env=env, check=True)
    subprocess.run([sys.executable, output / 'summarize.py'], cwd=output, env=env, check=True)


if __name__ == '__main__':
    main()

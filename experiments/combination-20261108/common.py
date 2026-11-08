#!/usr/bin/env python3
"""Small source/command helpers shared by this fixed four-cell experiment."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
FEATURE = Path(__file__).resolve().parent
BASE = '515f1efa0d79bcb73272df9f54917f156decf1e1'
DOUBLE = 'f46b835cb8f812293924418abc42a39978d78694'
CHECKS = 'b31fbce898054f6db668277f8a4da88f94c95aa2'
FIXTURE = '9c1d6f001520c382e117f3d86e488c71834e1bc7'
DOUBLE_FILES = ('native/specs/square.rs', 'native/verified/square_low.rs')
CHECK_FILES = ('native/verified/fast_multiply.rs',)
LABELS = ('baseline', 'double', 'checks', 'both')
sys.path.insert(0, str(ROOT / 'experiments/packed-convolution'))
from layout_verify import git_adapter, positive


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def git(*args):
    return subprocess.check_output(git_adapter() + list(args), timeout=60)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def mapping_sha(mapping):
    return sha(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode())


def manifest(folder):
    return {p.relative_to(folder).as_posix(): file_sha(p)
            for p in sorted((folder / 'native').rglob('*')) if p.is_file()}


def checked_prepared(path):
    folder = path.resolve()
    data = json.loads((folder / 'prepared.json').read_text())
    if data['status'] != 'pass' or data['base'] != BASE:
        raise RuntimeError('invalid prepared source')
    for label in LABELS:
        actual = manifest(folder / label)
        if actual != data['cells'][label]['native_sha256']:
            raise RuntimeError('prepared native drift: ' + label)
        if mapping_sha(actual) != data['cells'][label]['native_manifest_sha256']:
            raise RuntimeError('prepared manifest identity drift')
    for name, digest in data['inputs_sha256'].items():
        if file_sha(ROOT / name) != digest:
            raise RuntimeError('fixed experiment input drift: ' + name)
    return folder, data


def command_runner(out, report, env):
    def run(argv, name, cwd=None, timeout=900, require=True):
        row = dict(name=name, argv=list(map(str, argv)), cwd=str(cwd or out),
                   start_utc=datetime.now(timezone.utc).isoformat())
        report['commands'].append(row)
        write_json(out / 'verification.json', report)
        try:
            result = subprocess.run(row['argv'], cwd=cwd or out, env=env,
                                    capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            for stream in ('stdout', 'stderr'):
                raw = getattr(error, stream) or b''
                (out / (name + '.' + stream + '.log')).write_bytes(raw)
                row[stream + '_sha256'] = sha(raw)
            row.update(timed_out=True, stop_utc=datetime.now(timezone.utc).isoformat())
            write_json(out / 'verification.json', report)
            raise
        for stream in ('stdout', 'stderr'):
            raw = getattr(result, stream)
            (out / (name + '.' + stream + '.log')).write_bytes(raw)
            row[stream + '_sha256'] = sha(raw)
        row.update(returncode=result.returncode,
                   stop_utc=datetime.now(timezone.utc).isoformat())
        write_json(out / 'verification.json', report)
        if require and result.returncode:
            raise RuntimeError('command failed: ' + name)
        return result
    return run


def pinned_tools(deps, native, run, env):
    import zipfile
    pin = json.loads((native / 'toolchain.json').read_text())
    verifier = deps / 'verus/verus-x86-linux/verus'
    archive = deps / 'verus-download' / pin['archive']
    if file_sha(archive) != pin['sha256']:
        raise RuntimeError('wrong pinned archive')
    hashes = {}
    with zipfile.ZipFile(archive) as bundle:
        for name in ('verus', 'rust_verify', 'z3', 'vstd.vir', 'libvstd.rlib',
                     'libverus_builtin.rlib', 'libverus_builtin_macros.so',
                     'libverus_state_machines_macros.so'):
            digest = sha(bundle.read('verus-x86-linux/' + name))
            if file_sha(verifier.parent / name) != digest:
                raise RuntimeError('wrong pinned tool: ' + name)
            hashes[name] = digest
    selected = dict(CARGO_HOME=str(deps / 'cargo'), RUSTUP_HOME=str(deps / 'rustup'),
                    RUSTUP_TOOLCHAIN=pin['rust_toolchain'],
                    PATH=str(deps / 'cargo/bin') + os.pathsep + env['PATH'])
    env.update(selected)
    result = run([verifier, '--version'], 'verus-version')
    version = (result.stdout + result.stderr).decode()
    if pin['verus_version'] not in version or pin['rust_toolchain'] not in version:
        raise RuntimeError('wrong verifier version')
    return verifier, pin, dict(archive_sha256=pin['sha256'], sha256=hashes,
                               verus=version, environment=selected)

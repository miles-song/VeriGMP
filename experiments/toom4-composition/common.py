"""Identity and strict verification helpers shared by the isolated experiment."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def checked(command, log, cwd, input=None, timeout=600):
    result = subprocess.run(list(map(str, command)), cwd=cwd, input=input,
        text=True, capture_output=True, timeout=timeout)
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('Command failed; inspect ' + str(log))
    return result


def verified(command, log, cwd):
    result = checked(command, log, cwd)
    match = re.search(r'verification results:: (\d+) verified, 0 errors', result.stdout + result.stderr)
    if not match or 'partial verification' in result.stdout + result.stderr:
        raise RuntimeError('Not a complete positive verification: ' + str(log))
    return int(match[1])


def strict_mutant(result):
    text = result.stdout + result.stderr
    return bool(result.returncode and re.search(r'verification results:: \d+ verified, [1-9]\d* errors', text)
        and re.search(r'requires not satisfied|precondition not satisfied|invariant not satisfied|postcondition not satisfied|assertion failed', text)
        and not re.search(r'error\[E\d+\]|solver returned unknown|resource limit|timed out|timeout|unexpected token|could not compile|failed to load|panicked at|segmentation fault|internal compiler error', text, re.I))


def bind_tools(stage, out):
    verifier = Path(os.environ['VERUS_BIN']).resolve()
    pin = json.loads((stage / 'baseline/native/toolchain.json').read_text())
    version = checked([verifier, '--version'], out / 'verus.log', stage).stdout
    if pin['verus_version'] not in version or pin['rust_toolchain'] not in version:
        raise RuntimeError('Pinned verifier version mismatch')
    rustc = Path(checked(['rustup', 'which', '--toolchain', pin['rust_toolchain'], 'rustc'],
        out / 'rustc-path.log', stage).stdout.strip()).resolve()
    rust_version = checked([rustc, '-vV'], out / 'rustc.log', stage).stdout
    linkage = checked(['ldd', rustc], out / 'rustc-linked.log', stage).stdout
    files = [verifier.parent / name for name in ['verus', 'rust_verify', 'z3', 'vstd.vir',
        'libvstd.rlib', 'libverus_builtin.rlib', 'libverus_builtin_macros.so', 'libverus_state_machines_macros.so']]
    files += [rustc, Path(shutil.which('rustup')).resolve(), Path(shutil.which('c++')).resolve(), Path(sys.executable).resolve()]
    files += [Path(p).resolve() for p in re.findall(r'=> (\S+) \(', linkage)]
    return verifier, {'version': version, 'rustc': rust_version,
        'sha256': {str(p): sha(p) for p in sorted(set(files))}}


def check_hashes(mapping, root=None):
    for relative, expected in mapping.items():
        path = (root / relative) if root else Path(relative)
        if sha(path) != expected:
            raise RuntimeError('Identity changed: ' + str(path))


def check_prepared(stage):
    prepared = json.loads((stage / 'preparation.json').read_text())
    check_hashes({str(stage / name / relative): h
        for name, files in prepared['variants'].items() for relative, h in files.items()})
    if sha(stage / 'policy.json') != prepared['policy_sha256']:
        raise RuntimeError('Changed preregistered policy')
    return prepared


def default_cases(policy):
    import random
    rng = random.Random(20261103)
    shapes = sorted(set(tuple(x) for x in policy['exploration']['shapes']) |
        {(n, 63) for n in [1,2,3,7,8,9,23,24,25,63,64,65,127,128,129,191,192,193,255,256,257,511,512,513]})
    rows = []
    for n, _ in shapes:
        maximum = (1 << (64 * n)) - 1
        patterns = ([0, 1, maximum, maximum // 3, 1 << (64 * (n - 1)), rng.getrandbits(64 * n)]
            if n < 512 else [maximum, rng.getrandbits(64 * n)])
        tops = range(1, 65) if n in [1,2,9,64,256,1023,1024,1025] else [1,32,63,64]
        for i, a in enumerate(patterns):
            b = patterns[(i + 2) % len(patterns)]
            wa = [(a >> (64 * j)) & ((1 << 64) - 1) for j in range(n)]
            wb = [(b >> (64 * j)) & ((1 << 64) - 1) for j in range(n)]
            for top in tops:
                for operation, answer in [('mul', a*b), ('same', a*a), ('square', a*a)]:
                    answer %= 1 << (64 * (n - 1) + top)
                    command = ' '.join(map(str, [operation, top, n, *wa, *wb]))
                    expected = ' '.join(str((answer >> (64 * j)) & ((1 << 64) - 1)) for j in range(n))
                    rows.append((command, expected))
    return rows

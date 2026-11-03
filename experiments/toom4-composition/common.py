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
import unicodedata


_STRICT_SUMMARY = re.compile(
    r'^verification results:: (?:0|[1-9][0-9]*) verified, [1-9][0-9]* errors'
    r'(?: \(partial verification with `--verify-\*`\))?$')
_STRICT_SUMMARY_MENTION = re.compile(r'\bverification\s+results?\b', re.I)
_STRICT_SEMANTIC_HEADINGS = frozenset({
    'error: requires not satisfied',
    'error: precondition not satisfied',
    'error: postcondition not satisfied',
    'error: invariant not satisfied before loop',
    'error: invariant not satisfied at end of loop body',
    'error: assertion failed',
})
_STRICT_ABORT = re.compile(
    r'^error: aborting due to (?:1 previous error|(?:[2-9]|[1-9][0-9]+) previous errors)$')
_STRICT_CONTROL = re.compile(
    r'out of memory|\boom\b|resource limit|solver returned unknown|\bunknown\b|'
    r'partial verification|timed? out|\btimeout\b|unexpected token|could not compile|'
    r'failed to (?:load|execute)|panicked at|\bpanic\b|segmentation fault|'
    r'internal compiler error|compiler (?:error|panic|crash)|rustc(?::? error)|'
    r'failed to compile|\bfatal\b|access violation|unhandled exception|'
    r'killed by signal|\bsignal\b|\bsig(?:kill|term|abrt|segv|bus|fpe|ill|[0-9]+)\b|'
    r'memory allocation of [0-9]+ bytes failed|cannot allocate memory|'
    r'allocation fail(?:ed|ure)|bad_alloc|outofmemory|\brlimit\b|'
    r'abnormal (?:exit|termination)|\bprocess failed\b', re.I)
_STRICT_SEMANTIC_PHRASES = (
    'requires not satisfied', 'precondition not satisfied',
    'postcondition not satisfied', 'invariant not satisfied', 'assertion failed')
_STRICT_ASSERTION_SOURCE = re.compile(r'^ {2,}\|.*\^.* assertion failed$')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def checked(command, log, cwd, input=None, timeout=600):
    try:
        result = subprocess.run(list(map(str, command)), cwd=cwd, input=input,
            text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        def partial(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
        log.write_text(partial(error.stdout) + partial(error.stderr) + '\nCommand timed out; not a verification result.\n')
        raise
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
    if type(result.returncode) is not int or result.returncode != 1:
        return False

    streams = []
    for stream in (result.stdout, result.stderr):
        if not isinstance(stream, str):
            return False
        if any(unicodedata.category(char) == 'Cc' and char not in '\r\n'
                for char in stream):
            return False
        normalized = stream.replace('\r\n', '\n')
        if '\r' in normalized:
            return False
        streams.append(normalized.split('\n'))

    summaries = 0
    semantic = 0
    aborts = 0
    for lines in streams:
        for line in lines:
            if not line:
                continue
            if _STRICT_SUMMARY.fullmatch(line):
                summaries += 1
                continue
            if _STRICT_SUMMARY_MENTION.search(line):
                return False
            if 'error:' in line.casefold() or line.lstrip().casefold().startswith('error'):
                if line in _STRICT_SEMANTIC_HEADINGS:
                    semantic += 1
                elif _STRICT_ABORT.fullmatch(line):
                    aborts += 1
                else:
                    return False
                continue
            if _STRICT_CONTROL.search(line):
                return False
            lower = line.casefold()
            if any(phrase in lower for phrase in _STRICT_SEMANTIC_PHRASES):
                if not _STRICT_ASSERTION_SOURCE.fullmatch(line):
                    return False

    return summaries == 1 and semantic > 0 and aborts <= 1


def bind_tools(stage, out):
    verifier = Path(os.environ['VERUS_BIN']).resolve()
    pin = json.loads((stage / 'baseline/native/toolchain.json').read_text())
    version = checked([verifier, '--version'], out / 'verus.log', stage).stdout
    if pin['verus_version'] not in version or pin['rust_toolchain'] not in version:
        raise RuntimeError('Pinned verifier version mismatch')
    rustc = Path(checked(['rustup', 'which', '--toolchain', pin['rust_toolchain'], 'rustc'],
        out / 'rustc-path.log', stage).stdout.strip()).resolve()
    rust_version = checked([rustc, '-vV'], out / 'rustc.log', stage).stdout
    files = [verifier.parent / name for name in ['verus', 'rust_verify', 'z3', 'vstd.vir',
        'libvstd.rlib', 'libverus_builtin.rlib', 'libverus_builtin_macros.so', 'libverus_state_machines_macros.so']]
    executables = {'rustc': rustc, 'verus': verifier,
        'rust_verify': verifier.parent / 'rust_verify', 'z3': verifier.parent / 'z3',
        'python': Path(sys.executable).resolve()}
    executables.update({name: Path(shutil.which(name)).resolve()
        for name in ['rustup', 'c++', 'objdump', 'readelf']})
    files += list(executables.values())
    for name, executable in executables.items():
        linked = subprocess.run(['ldd', str(executable)], cwd=stage,
            text=True, capture_output=True, timeout=60)
        linkage = linked.stdout + linked.stderr
        (out / (name + '-linked.log')).write_text(linkage)
        if linked.returncode and not re.search(r'not a dynamic executable|statically linked', linkage):
            raise RuntimeError('Cannot inventory tool runtime: ' + name)
        files += [Path(p).resolve() for p in re.findall(r'=> (\S+) \(', linkage)]
        files += [Path(p).resolve() for p in re.findall(r'(?m)^\s*(/\S+) \(', linkage)]
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
    check_hashes(prepared['infrastructure_sha256'], stage)
    check_hashes(prepared.get('correctness_inputs_sha256', {}), stage)
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
            b = patterns[(i + (2 if len(patterns) > 2 else 1)) % len(patterns)]
            wa = [(a >> (64 * j)) & ((1 << 64) - 1) for j in range(n)]
            wb = [(b >> (64 * j)) & ((1 << 64) - 1) for j in range(n)]
            for top in tops:
                for operation, answer in [('mul', a*b), ('same', a*a), ('square', a*a)]:
                    answer %= 1 << (64 * (n - 1) + top)
                    command = ' '.join(map(str, [operation, top, n, *wa, *wb]))
                    expected = ' '.join(str((answer >> (64 * j)) & ((1 << 64) - 1)) for j in range(n))
                    rows.append((command, expected))
    return rows

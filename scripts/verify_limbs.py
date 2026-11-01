"""Independent integer checks and code-generation/throughput evidence for arithmetic.

Called by verify.py with its immutable source snapshot. Timing is
observational; the deterministic code-shape check is the proof-overhead gate.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
import time


def cases():
    rng = random.Random(20261101)
    maximum = (1 << 64) - 1
    inputs = []
    for n in (0, 1, 2, 3, 4, 7, 8, 16, 31, 32, 64, 127, 256, 1024, 4096):
        zero = [0] * n
        full = [maximum] * n
        one = ([1] + [0] * (n - 1)) if n else []
        inputs.extend([(zero, zero), (full, one), (full, full), (one, full), (full, zero)])
        for _ in range(80 if n <= 256 else 8):
            inputs.append(([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(64) for _ in range(n)]))
    # All carry-chain stopping positions, not just all-zero/all-one operands.
    for n in range(1, 33):
        for stop in range(n):
            inputs.append(([maximum] * stop + [7] + [maximum] * (n - stop - 1), [1] + [0] * (n - 1)))
    rows = []
    for a, b in inputs:
        n = len(a)
        lhs = int.from_bytes(b''.join(x.to_bytes(8, 'little') for x in a), 'little')
        rhs = int.from_bytes(b''.join(x.to_bytes(8, 'little') for x in b), 'little')
        total = lhs + rhs
        limbs = [(total >> (64 * i)) & maximum for i in range(n)]
        expected = ' '.join(map(str, [total >> (64 * n), *limbs]))
        rows.append((' '.join(map(str, a + b)), expected))
    return rows


def normalized_function(assembly, name):
    match = re.search(rf'(?m)^{re.escape(name)}:\n(.*?)^\s*\.size\s+{re.escape(name)},', assembly, re.S)
    if not match:
        raise RuntimeError(f'Cannot locate assembly function {name}')
    body = match[1]
    labels = {}
    for label in re.findall(r'(?m)^(\.LBB\w+):', body):
        labels[label] = f'BLOCK_{len(labels)}'
    lines = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('.') and not line.startswith('.LBB'):
            continue
        for original in sorted(labels, key=len, reverse=True):
            line = re.sub(re.escape(original) + r'\b', labels[original], line)
        # On this fixed toolchain, the source Location is passed in rdx to
        # core::panicking::panic. Do not normalize any other static constants.
        if re.match(r'leaq\s+\.Lanon\.[0-9a-f]+\.\d+\(%rip\), %rdx$', line):
            suffix = body[body.index(raw):]
            if not re.search(r'callq\s+\*\w*core\w*panicking\w*5panic@GOTPCREL', suffix):
                raise RuntimeError('Static constant is not recognized as panic location metadata')
            line = re.sub(r'\.Lanon\.[0-9a-f]+\.\d+(?=\(%rip\))', 'PANIC_LOCATION', line)
        lines.append(line)
    return lines


def check_limbs(snapshot, verifier, env, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {'status': 'running', 'scope': 'Radix representation and equal-length in-place addition',
              'complete_library_refined': False, 'complete_integer_api': False}

    def run(command, log, timeout=180, **kwargs):
        started = time.perf_counter()
        result = subprocess.run([str(x) for x in command], cwd=snapshot, env=env,
                                capture_output=True, text=True, timeout=timeout, **kwargs)
        text = result.stdout + result.stderr
        (output / log).write_text(text, encoding='utf-8')
        return result, text, time.perf_counter() - started

    def verified_compile(source, binary, log, *flags):
        result, text, seconds = run([verifier, snapshot / source, '--compile', '-O', *flags, '-o', binary], log)
        match = re.search(r'verification results:: (\d+) verified, 0 errors', text)
        if result.returncode or not match:
            raise RuntimeError(f'Verus failed: {source}, see {log}')
        return {'verification_items_including_imports': int(match[1]), 'seconds': seconds}

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    try:
        binary = snapshot / 'limbs-native'
        report['proof'] = verified_compile('native/limbs_runner.rs', binary, 'proof.log')
        binary_hash = digest(binary)
        rows = cases()
        result, _, _ = run([binary], 'execution.log', input='\n'.join(row[0] for row in rows) + '\n')
        if result.returncode or result.stdout.splitlines() != [row[1] for row in rows]:
            raise RuntimeError('Independent big-integer oracle mismatch')
        if digest(binary) != binary_hash:
            raise RuntimeError('Limb test binary changed during execution')
        report.update(integer_cases=len(rows), max_tested_limbs=4096, binary_sha256=binary_hash)

        source = snapshot / 'native/verified/limbs.rs'
        original = source.read_bytes()
        mutations = []
        try:
            for name, before, after in (
                ('drop_carry', 'carry = next;', 'carry = 0;'),
                ('skip_low_limb', 'let mut i: usize = 0;', 'let mut i: usize = 1;'),
                ('overwrite_output', 'dst[i] = low;', 'dst[i] = 0;'),
            ):
                text = original.decode('utf-8')
                if text.count(before) != 1:
                    raise RuntimeError(f'Mutation anchor missing: {name}')
                source.write_text(text.replace(before, after), encoding='utf-8')
                result, log, _ = run([verifier, snapshot / 'native/limbs_runner.rs'], name + '.log')
                detected = (result.returncode != 0
                            and re.search(r'verification results:: \d+ verified, [1-9]\d* errors', log)
                            and any(s in log for s in ('invariant not satisfied', 'assertion failed', 'postcondition not satisfied', 'requires not satisfied'))
                            and not any(s in log.lower() for s in ('timed out', 'resource limit', 'unexpected token')))
                mutations.append({'name': name, 'rejected_by_proof': bool(detected)})
                if not detected:
                    raise RuntimeError(f'Mutation not rejected semantically: {name}')
        finally:
            source.write_bytes(original)
        report['mutations'] = mutations

        assembly_path = snapshot / 'limbs-codegen.s'
        verified_compile('native/limbs_codegen.rs', assembly_path, 'codegen.log', '--emit=asm')
        assembly = assembly_path.read_text()
        actual = normalized_function(assembly, 'verified_add_assign')
        control = normalized_function(assembly, 'ordinary_add_assign')
        if actual != control:
            raise RuntimeError('Code-shape difference: inspect assembly before accepting performance')
        if any(token in '\n'.join(actual) for token in ('__rust_alloc', '__rust_realloc', 'malloc', 'memcpy', 'memmove')):
            raise RuntimeError('Unexpected allocation/copy call in addition kernel')
        (output / 'codegen-comparison.json').write_text(json.dumps({'verified': actual, 'ordinary': control}, indent=2) + '\n')
        (output / 'limbs-codegen.s').write_text(assembly)
        report['codegen'] = {'normalized_instructions_equal': True,
                             'normalizations': ['local block label names', 'panic source-location metadata', 'non-instruction assembly directives'],
                             'no_allocator_or_copy_calls_in_kernel': True,
                             'assembly_sha256': digest(assembly_path)}

        bench = snapshot / 'limbs-bench'
        verified_compile('native/limbs_bench.rs', bench, 'bench-build.log')
        bench_hash = digest(bench)
        cpu = min(os.sched_getaffinity(0))
        result, _, _ = run([bench, '16438731'], 'benchmark.csv', timeout=180,
                           preexec_fn=lambda: os.sched_setaffinity(0, {cpu}))
        if result.returncode or digest(bench) != bench_hash:
            raise RuntimeError('Benchmark failure or binary identity changed')
        samples = list(csv.DictReader(io.StringIO(result.stdout)))
        expected_lengths = [1, 4, 16, 64, 256, 1024, 4096, 16384]
        if len(samples) != 56 or sorted({int(s['limbs']) for s in samples}) != expected_lengths:
            raise RuntimeError('Incomplete benchmark output')
        summaries = []
        for n in expected_lengths:
            group = [s for s in samples if int(s['limbs']) == n]
            if len(group) != 7:
                raise RuntimeError('Missing repeated measurements')
            v = [int(s['verified_ns']) / (int(s['iterations']) * n) for s in group]
            o = [int(s['ordinary_ns']) / (int(s['iterations']) * n) for s in group]
            summaries.append({'limbs': n, 'verified_ns_per_limb_median': statistics.median(v),
                              'ordinary_ns_per_limb_median': statistics.median(o),
                              'paired_ratio_median': statistics.median(a / b for a, b in zip(v, o))})
        model = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                      if line.startswith('model name')), 'unknown')
        report['benchmark'] = {'compiler_flags': ['-O'], 'platform': platform.platform(), 'cpu_model': model,
                               'pinned_cpu': cpu, 'runtime_seed': 16438731, 'repetitions': 7,
                               'binary_sha256': bench_hash, 'timing_is_observational': True,
                               'includes': 'In-process calls, carry checksum and black_box; allocation and I/O outside timing',
                               'comparison': 'Same-algorithm ordinary Rust, not a best-available arithmetic library',
                               'summary': summaries}
        report['cost_scope'] = {'proved_loop_visits': 'Exactly n for n limbs, tracked only in erased ghost state',
                                'source_structure': 'One limb addition and store per visit, no allocation or recursive execution',
                                'derived_word_cost': 'O(n) time, O(1) auxiliary words excluding caller-owned input/output',
                                'composed_cost_proved': False}
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report

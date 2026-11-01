"""Check positive arbitrary-bit precision against independent Python integers."""
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

from verify_limbs import normalized_function


def cases():
    rng = random.Random(20261102)
    word_mask = (1 << 64) - 1
    rows = []
    def add(command, expected):
        rows.append((command, expected))
    precisions = list(range(1, 514)) + list(range(word_mask - 128, word_mask + 1))
    precisions += [rng.randrange(1, word_mask + 1) for _ in range(1000)]
    for p in precisions:
        n, offset = divmod(p - 1, 64)
        add(f'layout {p}', f'{n + 1} {offset + 1}')
    for top in range(1, 65):
        values = [0, 1, word_mask, word_mask - 1, (1 << top) - 1, (1 << top) & word_mask]
        values += [rng.getrandbits(64) for _ in range(64)]
        for word in values:
            add(f'mask {top} {word}', str(word % (1 << top)))
    def integer(words):
        return int.from_bytes(b''.join(w.to_bytes(8, 'little') for w in words), 'little')
    def words(value, n):
        return [(value >> (64 * i)) & word_mask for i in range(n)]
    def formatted(values):
        return ' '.join(map(str, values))
    for n in (1, 2, 3, 4, 8, 16, 33, 64, 257, 1024, 4096):
        tops = range(1, 65) if n <= 64 else (1, 31, 63, 64)
        for top in tops:
            modulus = 1 << (64 * (n - 1) + top)
            pairs = [([0] * n, [0] * n), ([word_mask] * n, [1] + [0] * (n - 1)),
                     ([word_mask] * n, [word_mask] * n),
                     ([0] * n, [1] + [0] * (n - 1)),
                     ([0] * (n - 1) + [1], [1] + [0] * (n - 1)),
                     (words(modulus - 1, n), words(1, n))]
            pairs += [([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(64) for _ in range(n)]) for _ in range(4)]
            for a, b in pairs:
                residue = words(integer(a) % modulus, n)
                expected = words((integer(a) + integer(b)) % modulus, n)
                add(f'norm {top} {formatted(a)}', formatted(residue))
                add(f'add {top} {formatted(a + b)}', formatted(expected))
                add(f'sub {top} {formatted(a + b)}', formatted(words((integer(a)-integer(b))%modulus,n)))
                if top==64:
                    difference=integer(a)-integer(b)
                    add(f'subraw 64 {formatted(a+b)}',formatted([*words(difference,n),int(difference<0)]))
                # Idempotence uses the independently computed canonical representative.
                add(f'norm {top} {formatted(residue)}', formatted(residue))
    add('subraw 64','0')
    return rows


def check_pow2(snapshot, verifier, env, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {'status': 'running', 'scope': 'Precision layout, word mask, normalization and in-place modular addition/subtraction',
              'complete_library_refined': False, 'complete_integer_api': False}
    def run(command, log, timeout=180, **kwargs):
        result = subprocess.run([str(x) for x in command], cwd=snapshot, env=env, capture_output=True,
                                text=True, timeout=timeout, **kwargs)
        text = result.stdout + result.stderr
        if log is not None:
            (output / log).write_text(text, encoding='utf-8')
        return result, text
    def compile(source, target, log, *flags):
        result, text = run([verifier, snapshot / source, '--compile', '-O', *flags, '-o', target], log)
        match = re.search(r'verification results:: (\d+) verified, 0 errors', text)
        if result.returncode or not match:
            raise RuntimeError(f'Verus verification/compilation failed: {source}')
        return int(match[1])
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        binary = snapshot / 'pow2-native'
        report['verification_items_including_imports'] = compile('native/pow2_runner.rs', binary, 'proof.log')
        binary_hash = digest(binary)
        rows = cases()
        input_text = '\n'.join(c for c, _ in rows) + '\n'
        result, _ = run([binary], None, input=input_text)
        if result.returncode or result.stdout.splitlines() != [expected for _, expected in rows]:
            raise RuntimeError('Independent modulo-power-of-two oracle mismatch')
        if digest(binary) != binary_hash:
            raise RuntimeError('Execution binary changed')
        report['oracle'] = {'cases': len(rows), 'seed': 20261102, 'top_bits': [1, 64], 'max_limbs': 4096,
                            'layout_max_bits': (1 << 64) - 1, 'binary_sha256': binary_hash,
                            'input_sha256': hashlib.sha256(input_text.encode()).hexdigest(),
                            'output_sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}
        # Invalid domains must reject instead of producing a mathematical answer.
        invalid = ['layout 0', 'mask 0 1', 'mask 65 1', 'norm 1', 'add 1', 'add 0 1 2', 'add 65 1 2',
                   'sub 1','sub 0 1 2','sub 65 1 2','sub 64 1 2 3']
        for i, command in enumerate(invalid):
            result, _ = run([binary], f'invalid-{i}.log', input=command + '\n')
            if result.returncode == 0 or result.stdout.strip():
                raise RuntimeError(f'Invalid domain accepted: {command}')
        report['invalid_domains_rejected'] = len(invalid)

        source = snapshot / 'native/verified/pow2.rs'
        original = source.read_bytes()
        report['mutations'] = []
        try:
            for name, before, after in (
                ('wrong_layout_rounding', 'let remaining = bits - 1;', 'let remaining = bits;'),
                ('wrong_mask_bit', 'let mask = (1u64 << bits) - 1;', 'let mask = (1u64 << bits) - 2;'),
                ('discard_full_word', '        word\n    } else {', '        0\n    } else {'),
                ('skip_normalization', '    normalize_top(dst, top);', '    // normalization deliberately removed'),
                ('subtract_as_add', 'let _borrow=limbs::sub_assign(dst,rhs);', 'let _borrow=limbs::add_assign(dst,rhs);'),
                ('skip_sub_normalization', '    normalize_top(dst,top);', '    // normalization deliberately removed'),
            ):
                text = original.decode('utf-8')
                if text.count(before) != 1:
                    raise RuntimeError(f'Mutation anchor mismatch: {name}')
                source.write_text(text.replace(before, after), encoding='utf-8')
                result, log = run([verifier, snapshot / 'native/pow2_runner.rs'], name + '.log')
                detected = (result.returncode != 0
                            and re.search(r'verification results:: \d+ verified, [1-9]\d* errors', log)
                            and any(s in log for s in ('invariant not satisfied', 'assertion failed', 'postcondition not satisfied', 'requires not satisfied'))
                            and not any(s in log.lower() for s in ('timed out', 'resource limit', 'unexpected token')))
                report['mutations'].append({'name': name, 'rejected_by_proof': bool(detected)})
                if not detected:
                    raise RuntimeError(f'Mutation not rejected semantically: {name}')
        finally:
            source.write_bytes(original)

        source=snapshot/'native/verified/limbs.rs';original=source.read_bytes()
        try:
            before='borrow=next;i+=1;proof{visits=visits+1;}'
            text=original.decode();assert text.count(before)==1
            source.write_text(text.replace(before,'borrow=0;i+=1;proof{visits=visits+1;}'))
            result,log=run([verifier,snapshot/'native/pow2_runner.rs'],'drop_sub_borrow.log')
            detected=bool(result.returncode and re.search(r'verification results:: \d+ verified, [1-9]\d* errors',log)
                and any(s in log for s in ('invariant not satisfied','assertion failed','postcondition not satisfied'))
                and not any(s in log.lower() for s in ('timed out','resource limit','unexpected token')))
            report['mutations'].append({'name':'drop_sub_borrow','rejected_by_proof':detected})
            if not detected:raise RuntimeError('Borrow mutant not rejected semantically')
        finally:source.write_bytes(original)

        assembly_path = snapshot / 'pow2-codegen.s'
        compile('native/pow2_codegen.rs', assembly_path, 'codegen.log', '--emit=asm')
        assembly = assembly_path.read_text()
        comparisons = {}
        for name in ('layout', 'mask', 'normalize', 'add_mod', 'sub_mod'):
            verified = normalized_function(assembly, 'verified_' + name)
            ordinary = normalized_function(assembly, 'ordinary_' + name)
            if verified != ordinary:
                raise RuntimeError(f'Code-shape difference in {name}; inspect before accepting performance')
            if any(token in '\n'.join(verified) for token in ('__rust_alloc', '__rust_realloc', 'malloc', 'memcpy', 'memmove')):
                raise RuntimeError(f'Unexpected allocation or copy in {name}')
            if any(re.match(r'(i?div)[bwlq]?\s', line) or re.search(r'__(u?div|u?mod)ti3', line) for line in verified):
                raise RuntimeError(f'Unexpected general division in {name}')
            comparisons[name] = {'verified': verified, 'ordinary': ordinary}
        (output / 'codegen-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
        (output / 'pow2-codegen.s').write_text(assembly)
        report['codegen'] = {'normalized_equal': list(comparisons), 'no_allocator_or_copy_calls': True,
                             'no_general_integer_division': True,
                             'normalization': 'Block labels, panic location metadata and non-instruction directives only',
                             'assembly_sha256': digest(assembly_path)}

        bench = snapshot / 'pow2-bench'
        compile('native/pow2_bench.rs', bench, 'bench-build.log')
        bench_hash = digest(bench)
        cpu = min(os.sched_getaffinity(0))
        result, _ = run([bench, '16438731'], 'benchmark.csv', preexec_fn=lambda: os.sched_setaffinity(0, {cpu}))
        if result.returncode or digest(bench) != bench_hash:
            raise RuntimeError('Benchmark failure or binary identity changed')
        samples = list(csv.DictReader(io.StringIO(result.stdout)))
        expected_shapes = [(1,1),(1,63),(1,64),(2,1),(2,63),(2,64),(16,7),(256,31),(1024,63),(4096,1),(4096,64)]
        if len(samples) != 154 or {s['operation'] for s in samples}!={'add','sub'} or sorted({(int(s['limbs']),int(s['top'])) for s in samples}) != expected_shapes:
            raise RuntimeError('Incomplete benchmark shapes')
        summaries = []
        for operation,n,top in [(op,n,top) for op in ('add','sub') for n,top in expected_shapes]:
            group = [s for s in samples if (s['operation'],int(s['limbs']),int(s['top'])) == (operation,n,top)]
            if len(group) != 7:
                raise RuntimeError('Missing benchmark repetitions')
            v = [int(s['verified_ns']) / (int(s['iterations']) * n) for s in group]
            o = [int(s['ordinary_ns']) / (int(s['iterations']) * n) for s in group]
            summaries.append({'operation':operation,'limbs': n, 'top': top, 'precision_bits': 64*(n-1)+top,
                              'verified_ns_per_limb_median': statistics.median(v),
                              'ordinary_ns_per_limb_median': statistics.median(o),
                              'paired_ratio_median': statistics.median(a/b for a,b in zip(v,o))})
        model = next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                      if line.startswith('model name')), 'unknown')
        report['benchmark'] = {'compiler_flags': ['-O'], 'platform': platform.platform(), 'cpu_model': model,
                               'pinned_cpu': cpu, 'runtime_seed': 16438731, 'repetitions': 7,
                               'binary_sha256': bench_hash, 'timing_is_observational': True,
                               'includes': 'In-process calls and black_box; allocation/initialization/I/O excluded',
                               'comparison': 'Same-algorithm ordinary Rust, not best-available arithmetic', 'summary': summaries}
        report['cost_scope'] = {'layout_mask_normalize': 'Constant word operations; normalize writes only the top word',
                                'modular_addition': 'One existing n-visit addition loop plus constant-time normalization',
                                'modular_subtraction': 'One n-visit borrow loop plus constant-time normalization; Euclidean residue for negative differences',
                                'extra_space': 'O(1) words excluding caller storage', 'composed_cost_proved': False}
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report

#!/usr/bin/env python3
"""Run the predeclared timing protocol only in an explicitly scheduled window."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/combination-20261108'))
from common import file_sha, manifest, write_json

HEADER = ['run', 'operation', 'limbs', 'top', 'repetition', 'position', 'mode', 'iterations', 'ns']
ORDERS = ([2, 0, 1, 1, 0, 2, 2, 0, 3, 3, 0, 2],
          [2, 1, 0, 0, 1, 2, 2, 3, 0, 0, 3, 2])
REGISTERED = {(1, 1), (1, 64), (2, 1), *((n, 63) for n in
              (23, 24, 25, 63, 64, 65, 127, 128, 129, 191, 192, 193,
               255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 2048, 4096))}
EXTRA = (511, 512, 513, 1023, 1024, 1025, 1280, 1536, 1792, 2047, 2048,
         2049, 2560, 3072, 3584, 4095, 4096, 4097)
TIME_SPREAD = 1.10
RATIO_SPREAD = 1.05


def benchmark_environment():
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'TZ': 'UTC',
            'RAYON_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}


def no_system_preload():
    preload = Path('/etc/ld.so.preload')
    if preload.exists() and preload.read_bytes().strip():
        raise RuntimeError('nonempty system loader preload is forbidden')


def linked_paths(binary, env):
    no_system_preload()
    result = subprocess.run(['/usr/bin/ldd', str(binary)], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=30, check=True)
    if 'not found' in result.stdout:
        raise RuntimeError('a linked library was not found')
    paths = set()
    for line in result.stdout.splitlines():
        if 'linux-vdso' in line:
            continue
        match = re.match(r'^\s*(?:\S+\s+=>\s+)?(/\S+)\s+\(', line)
        if not match:
            raise RuntimeError('unrecognized ldd output: ' + line)
        paths.add(Path(match.group(1)).resolve(strict=True))
    if not paths:
        raise RuntimeError('no dynamic dependencies resolved')
    return {str(path): file_sha(path) for path in sorted(paths)}, result.stdout


def runtime_identity(binary, env):
    linked, output = linked_paths(binary, env)
    names = [Path(path).name for path in linked]
    for prefix in ('libgmp', 'libc.so', 'ld-linux'):
        if sum(name.startswith(prefix) for name in names) != 1:
            raise RuntimeError('expected exactly one runtime ' + prefix)
    linked[str(binary.resolve(strict=True))] = file_sha(binary)
    return linked, output


def proc_identity(pid, expected, env, verify_hash, initial=None):
    no_system_preload()
    raw_environment = (Path('/proc') / str(pid) / 'environ').read_bytes().split(b'\0')
    pairs = [entry.split(b'=', 1) for entry in raw_environment if entry]
    if any(len(pair) != 2 for pair in pairs):
        raise RuntimeError('malformed process environment')
    decoded = [(key.decode(), value.decode()) for key, value in pairs]
    if len(decoded) != len(dict(decoded)) or dict(decoded) != env:
        raise RuntimeError('process environment differs from fixed environment')
    raw = (Path('/proc') / str(pid) / 'maps').read_text()
    identities = {}
    for line in raw.splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) < 5:
            raise RuntimeError('malformed process map')
        if int(parts[4]) == 0:
            continue
        if len(parts) != 6 or not parts[5].startswith('/') or parts[5].endswith(' (deleted)'):
            raise RuntimeError('unidentifiable process mapping')
        path = Path(parts[5]).resolve(strict=True)
        stat = path.stat()
        major, minor = (int(value, 16) for value in parts[3].split(':'))
        if (os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino) != (major, minor, int(parts[4])):
            raise RuntimeError('mapped file device or inode changed: ' + str(path))
        key = str(path)
        meta = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
        if key in identities and identities[key] != meta:
            raise RuntimeError('mapping metadata changed: ' + key)
        identities[key] = meta
    if set(identities) != set(expected):
        raise RuntimeError(f'loaded paths differ: actual={sorted(identities)} expected={sorted(expected)}')
    if initial is not None and identities != initial:
        raise RuntimeError('loaded file metadata changed')
    if verify_hash:
        for name, digest in expected.items():
            if file_sha(name) != digest:
                raise RuntimeError('loaded file hash changed: ' + name)
            stat = Path(name).stat()
            if [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns] != identities[name]:
                raise RuntimeError('loaded file changed while hashing: ' + name)
    return raw, identities


def wait_marker(process, stderr_path, phase, timeout=30):
    marker = 'VERIGMP_CONTROL_' + phase
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if marker in stderr_path.read_text():
            return
        if process.poll() is not None:
            raise RuntimeError('process exited before ' + marker)
        time.sleep(0.05)
    raise RuntimeError('process timed out before ' + marker)


def release(process):
    process.stdin.write(b'G')
    process.stdin.flush()


def loader_probe(binary, env, expected, out):
    stderr_path = out / 'loader-probe.stderr.log'
    process = None
    try:
        with stderr_path.open('wb') as stderr:
            process = subprocess.Popen([str(binary), '--check-loader'], cwd=ROOT, env=env,
                                       stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                       stderr=stderr, start_new_session=True)
            wait_marker(process, stderr_path, 'READY')
            raw, first = proc_identity(process.pid, expected, env, True)
            (out / 'loader-probe-ready.maps').write_text(raw)
            incorrect = dict(expected)
            incorrect[next(iter(incorrect))] = '0' * 64
            missing_path = dict(expected)
            del missing_path[next(iter(missing_path))]
            incorrect_meta = {name: list(values) for name, values in first.items()}
            incorrect_meta[next(iter(incorrect_meta))][1] += 1
            for label, paths, environment, metadata in (
                    ('hash', incorrect, env, None),
                    ('paths', missing_path, env, None),
                    ('environment', expected, dict(env, LD_PRELOAD='/invalid'), None),
                    ('metadata', expected, env, incorrect_meta)):
                try:
                    proc_identity(process.pid, paths, environment, True, metadata)
                except RuntimeError:
                    pass
                else:
                    raise RuntimeError('invalid runtime ' + label + ' was accepted')
            release(process)
            wait_marker(process, stderr_path, 'DONE')
            raw, _ = proc_identity(process.pid, expected, env, True, first)
            (out / 'loader-probe-done.maps').write_text(raw)
            release(process)
            if process.wait(timeout=10):
                raise RuntimeError('loader probe failed')
            process = None
        return first
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def expected_shapes():
    return REGISTERED | {(n, top) for n in EXTRA for top in (1, 31, 63, 64)}


def require_spread(values, limit, label):
    if not values or min(values) <= 0 or max(values) / min(values) > limit:
        raise RuntimeError(f'{label} exceeded spread {limit}')


def parse_run(text, run, shapes):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != HEADER:
        raise RuntimeError('unexpected CSV columns')
    groups = {}
    for line in reader:
        if None in line or any(value is None for value in line.values()):
            raise RuntimeError('malformed CSV row')
        row = {key: int(value) for key, value in line.items()}
        key = (row['operation'], row['limbs'], row['top'], row['repetition'])
        if row['run'] != run or row['iterations'] < 1 or row['ns'] < 10_000_000:
            raise RuntimeError('invalid run, iterations, or batch duration')
        groups.setdefault(key, []).append(row)
    expected = {(op, n, top, rep) for n, top in shapes for op in range(2) for rep in range(7)}
    if set(groups) != expected:
        raise RuntimeError('missing or unexpected operation, shape, or repetition')
    result = {}
    for n, top in shapes:
        for op in range(2):
            blocks = [[], []]
            counts = set()
            for rep in range(7):
                rows = groups[(op, n, top, rep)]
                order = ORDERS[(rep + run) % 2]
                if (len(rows) != 12 or [r['position'] for r in rows] != list(range(12)) or
                        [r['mode'] for r in rows] != order or
                        len({r['iterations'] for r in rows}) != 1):
                    raise RuntimeError('invalid sample order, count, or calibration')
                counts.add(rows[0]['iterations'])
                for block in range(2):
                    sample = rows[6 * block:6 * block + 6]
                    a = [r['ns'] / r['iterations'] for r in sample if r['mode'] == 0]
                    other = [r['ns'] / r['iterations'] for r in sample if r['mode'] == (1 if block == 0 else 3)]
                    g = [r['ns'] / r['iterations'] for r in sample if r['mode'] == 2]
                    for name, values in (('A', a), ('B/C', other), ('G', g)):
                        require_spread(values, TIME_SPREAD, f'paired {name} batches')
                    av, bv, gv = statistics.mean(a), statistics.mean(other), statistics.mean(g)
                    blocks[block].append(dict(a=av, other_time=bv, g=gv,
                                              other=bv / av, a_over_g=av / gv,
                                              other_over_g=bv / gv, a_drift=a[1] / a[0],
                                              g_drift=g[1] / g[0], order=(rep + run) % 2))
            if len(counts) != 1:
                raise RuntimeError('calibration changed across repetitions')
            block_results = []
            for samples in blocks:
                metrics = ('a', 'other_time', 'g', 'other', 'a_over_g', 'other_over_g', 'a_drift', 'g_drift')
                item = {key: statistics.median(x[key] for x in samples) for key in metrics}
                item['by_order'] = {}
                for order in range(2):
                    selected = [x for x in samples if x['order'] == order]
                    for key in ('a', 'other_time', 'g', 'other'):
                        require_spread([x[key] for x in selected], TIME_SPREAD,
                                       f'within-order {key} operation={op}, n={n}, top={top}')
                    item['by_order'][str(order)] = {key: statistics.median(x[key] for x in selected)
                                                   for key in ('a', 'other_time', 'g', 'other')}
                for key in ('a', 'other_time', 'g', 'other'):
                    require_spread([item['by_order'][str(order)][key] for order in range(2)],
                                   RATIO_SPREAD if key == 'other' else TIME_SPREAD,
                                   f'between-order {key} operation={op}, n={n}, top={top}')
                block_results.append(item)
            result[(op, n, top)] = block_results
    return result


def compare_runs(first, second):
    if set(first) != set(second):
        raise RuntimeError('run shapes differ')
    results = []
    for (op, n, top) in sorted(first):
        blocks = []
        for block in range(2):
            first_block, second_block = first[(op, n, top)][block], second[(op, n, top)][block]
            for key in ('a', 'other_time', 'g', 'other'):
                require_spread([first_block[key], second_block[key]],
                               RATIO_SPREAD if key == 'other' else TIME_SPREAD,
                               f'between-run {key} operation={op}, n={n}, top={top}')
            for order in ('0', '1'):
                require_spread([first_block['by_order'][order]['other'],
                                second_block['by_order'][order]['other']], RATIO_SPREAD,
                               f'between-run order={order} ratio operation={op}, n={n}, top={top}')
            blocks.append(dict(run_0=first_block, run_1=second_block,
                               a_cross_run=second_block['a'] / first_block['a']))
        enabled = n >= (2048 if op == 0 else 1024)
        ratios = [first[(op, n, top)][0]['other'], second[(op, n, top)][0]['other']]
        screen = all(r <= 0.98 for r in ratios) if enabled else (
            all(r <= 1.03 for r in ratios) if (n, top) in REGISTERED else None)
        results.append(dict(operation=op, limbs=n, top=top, candidate_enabled=enabled,
                            registered=(n, top) in REGISTERED, candidate_screen_pass=screen,
                            candidate_block=blocks[0], forced_exploratory_block=blocks[1]))
    return results


def self_test():
    shapes = [(1, 64)]
    def fixture(run, override=None):
        output = io.StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(HEADER)
        for op in range(2):
            for rep in range(7):
                for pos, mode in enumerate(ORDERS[(rep + run) % 2]):
                    duration = override(op, rep, pos, mode) if override else 20_000_000
                    writer.writerow([run, op, 1, 64, rep, pos, mode, 1, duration])
        return output.getvalue()
    first, second = fixture(0), fixture(1)
    assert len(compare_runs(parse_run(first, 0, shapes), parse_run(second, 1, shapes))) == 2
    for broken in [first.rsplit('\n', 2)[0] + '\n', first.replace(',20000000', ',1', 1),
                   first.replace(',0,2,1,20000000', ',0,1,1,20000000', 1)]:
        try:
            parse_run(broken, 0, shapes)
        except RuntimeError:
            pass
        else:
            raise RuntimeError('invalid synthetic sample was accepted')
    def reject_fixture(override):
        try:
            parse_run(fixture(0, override), 0, shapes)
        except RuntimeError:
            return
        raise RuntimeError('noisy synthetic sample was accepted')
    for target in (1, 3):
        # A/G remain 20 ms; a 10 ms and 29 ms pair averages to the misleading 0.975 ratio.
        reject_fixture(lambda op, rep, pos, mode: (10_000_000 if pos in (2, 8) else 29_000_000)
                       if op == 0 and rep == 0 and mode == target else 20_000_000)
        reject_fixture(lambda op, rep, pos, mode: 23_000_000
                       if op == 0 and rep % 2 == 1 and mode == target else 20_000_000)
        reject_fixture(lambda op, rep, pos, mode: 16_000_000
                       if op == 0 and rep == 2 and mode == target else 20_000_000)
        altered = fixture(1, lambda op, rep, pos, mode: 22_000_000
                          if op == 0 and mode == target else 20_000_000)
        try:
            compare_runs(parse_run(first, 0, shapes), parse_run(altered, 1, shapes))
        except RuntimeError:
            pass
        else:
            raise RuntimeError('cross-run ratio mismatch was accepted')
    env = benchmark_environment()
    if any(key.startswith(('LD_', 'MALLOC_', 'GLIBC_')) for key in env):
        raise RuntimeError('loader or allocator overrides present in fixed environment')
    hz = os.sysconf('SC_CLK_TCK')
    previous = dict(time_before=10, time_after=10, busy_before=0, busy_after=0, processes={})
    allowed = dict(time_before=11, time_after=11, busy_before=0, busy_after=0, processes={})
    monitor(previous, allowed, None, None, io.StringIO())
    process_ticks = math.floor(0.10 * hz) + 1
    aggregate_ticks = max(math.floor(0.15 * hz), math.floor(0.10 * hz) + 1)
    for rejected in [dict(time_before=11, time_after=11, busy_before=process_ticks,
                          busy_after=process_ticks, processes={(999999, 1): (process_ticks, 'R', 1)}),
                     dict(time_before=11, time_after=11, busy_before=aggregate_ticks,
                          busy_after=aggregate_ticks, processes={}),
                     dict(time_before=11, time_after=11, busy_before=0,
                          busy_after=aggregate_ticks, processes={})]:
        try:
            monitor(previous, rejected, None, None, io.StringIO())
        except RuntimeError:
            pass
        else:
            raise RuntimeError('excess synthetic CPU load was accepted')
    print('parser and rejection self-test passed; no timing')


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def cpu_identity(cpu):
    for block in Path('/proc/cpuinfo').read_text().split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
        fields = {key.strip(): value.strip() for key, value in fields.items()}
        if fields.get('processor') == str(cpu):
            return {key: fields[key] for key in ('processor', 'model name', 'physical id', 'core id', 'microcode')
                    if key in fields}
    raise RuntimeError('requested CPU missing from /proc/cpuinfo')


def snapshot():
    def aggregate_busy():
        values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
        return sum(values[i] for i in (0, 1, 2, 5, 6, 7))

    time_before = time.monotonic()
    busy_before = aggregate_busy()
    processes = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            text = path.read_text()
            tail = text.rsplit(') ', 1)[1].split()
            processes[(int(path.parent.name), int(tail[19]))] = (int(tail[11]) + int(tail[12]), tail[0], int(tail[17]))
        except (FileNotFoundError, ProcessLookupError):
            continue
    busy_after = aggregate_busy()
    time_after = time.monotonic()
    return dict(time_before=time_before, time_after=time_after,
                busy_before=busy_before, busy_after=busy_after, processes=processes)


def monitor(previous, current, benchmark_pid, expected_cpu, stream):
    elapsed = current['time_after'] - previous['time_before']
    if not 0.8 <= elapsed <= 3:
        raise RuntimeError('CPU monitoring interval outside 0.8..3 seconds')
    hz = os.sysconf('SC_CLK_TCK')
    if (previous['busy_after'] < previous['busy_before'] or
            current['busy_after'] < current['busy_before'] or
            current['busy_before'] < previous['busy_after']):
        raise RuntimeError('aggregate CPU counter decreased')
    tick_delta = {}
    for key, (ticks, state, threads) in current['processes'].items():
        old = previous['processes'].get(key, (0, state, threads))[0]
        delta = ticks - old
        if delta < 0:
            raise RuntimeError('process CPU counter decreased')
        if delta:
            tick_delta[key[0]] = tick_delta.get(key[0], 0) + delta
    excluded = tick_delta.get(os.getpid(), 0) + tick_delta.get(benchmark_pid, 0)
    busy = max(0, current['busy_after'] - previous['busy_before'] - excluded)
    others = {str(pid): ticks for pid, ticks in tick_delta.items() if pid not in (os.getpid(), benchmark_pid)}
    benchmark = [(state, threads) for (pid, _), (_, state, threads) in current['processes'].items()
                 if pid == benchmark_pid]
    affinity = None
    if benchmark and benchmark[0][0] != 'Z':
        affinity = sorted(os.sched_getaffinity(benchmark_pid))
    entry = dict(monotonic=current['time_after'], elapsed_seconds=elapsed, ticks_per_second=hz,
                 previous_busy_before=previous['busy_before'], current_busy_after=current['busy_after'],
                 guest_non_benchmark_ticks=busy, process_ticks=others,
                 benchmark_ticks=tick_delta.get(benchmark_pid, 0), monitor_ticks=tick_delta.get(os.getpid(), 0),
                 benchmark_threads=benchmark[0][1] if benchmark else None, benchmark_affinity=affinity)
    stream.write(json.dumps(entry, sort_keys=True) + '\n')
    stream.flush()
    if busy > 0.10 * hz * elapsed or any(ticks > 0.10 * hz * elapsed for ticks in others.values()):
        raise RuntimeError('background CPU threshold exceeded')
    if benchmark and benchmark[0][0] != 'Z' and (benchmark[0][1] != 1 or affinity != [expected_cpu]):
        raise RuntimeError('benchmark thread count or CPU affinity changed')


def check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash):
    if file_sha(prep_file) != prep_hash or file_sha(proof / 'verification.json') != proof_hash:
        raise RuntimeError('preparation or proof report changed')
    if prep['status'] != 'prepared_no_timing' or proof_data['status'] != 'full_library_pass':
        raise RuntimeError('required preparation or proof missing')
    if manifest(ROOT) != proof_data['native_sha256'] or manifest(proof / 'snapshot') != proof_data['native_sha256']:
        raise RuntimeError('native source differs from proof')
    for name, digest in prep['source_sha256'].items():
        if file_sha(ROOT / name) != digest:
            raise RuntimeError('measurement source changed: ' + name)
    for name, digest in prep['evidence_sha256'].items():
        if file_sha(prep_file.parent / name) != digest:
            raise RuntimeError('preparation evidence changed: ' + name)
    for name, digest in prep['identity_sha256'].items():
        if file_sha(Path(name)) != digest:
            raise RuntimeError('compiled binary, tool, or linked library changed: ' + name)
    for name, digest in proof_data['exports_sha256'].items():
        if file_sha(proof / name) != digest:
            raise RuntimeError('proof export changed: ' + name)
    verifier = Path(proof_data['commands'][0]['argv'][0])
    for name, digest in proof_data['tools']['sha256'].items():
        if file_sha(verifier.parent / name) != digest:
            raise RuntimeError('verifier dependency changed: ' + name)


def run_window(args):
    if not args.authorized_window:
        raise RuntimeError('the parent must schedule a quiet timing window before --authorized-window')
    env = benchmark_environment()
    if dict(os.environ) != env:
        raise RuntimeError('launch controller with exactly the predeclared clean environment')
    prepared, proof, out = args.prepared.resolve(), args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    if args.cpu not in os.sched_getaffinity(0):
        raise RuntimeError('requested CPU is outside current affinity')
    out.mkdir(parents=True)
    report_path = out / 'measurement.json'
    report = dict(status='running', benchmark_run=True, cpu=args.cpu, cpu_identity=cpu_identity(args.cpu), boot_id=boot_id(),
                  platform=platform.platform(),
                  original_affinity=sorted(os.sched_getaffinity(0)), runs=[])
    write_json(report_path, report)
    process = None
    try:
        prep_file = prepared / 'preparation.json'
        prep_hash, proof_hash = file_sha(prep_file), file_sha(proof / 'verification.json')
        prep, proof_data = json.loads(prep_file.read_text()), json.loads((proof / 'verification.json').read_text())
        if prep['proof_report_sha256'] != proof_hash:
            raise RuntimeError('preparation refers to a different proof report')
        if prep['benchmark_environment'] != env:
            raise RuntimeError('prepared benchmark environment differs')
        check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
        report.update(preparation_sha256=prep_hash, proof_report_sha256=proof_hash,
                      native_manifest_sha256=prep['native_manifest_sha256'],
                      source_sha256=prep['source_sha256'], identity_sha256=prep['identity_sha256'],
                      gmp_abi=prep['gmp_abi'], shapes=prep['shapes'], environment=env,
                      runtime_sha256=prep['runtime_sha256'])
        binary = prepared / 'measure'
        with (out / 'monitor.jsonl').open('w', encoding='utf-8') as monitor_file:
            for run in range(2):
                if boot_id() != report['boot_id']:
                    raise RuntimeError('boot identity changed')
                check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
                runtime, linked = runtime_identity(binary, env)
                if runtime != prep['runtime_sha256']:
                    raise RuntimeError('runtime dependency resolution changed')
                (out / f'run-{run}.ldd.log').write_text(linked)
                previous = snapshot()
                time.sleep(1)
                current = snapshot()
                monitor(previous, current, None, None, monitor_file)
                stdout_path, stderr_path = out / f'run-{run}.csv', out / f'run-{run}.stderr.log'
                with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
                    process = subprocess.Popen([str(binary), '--run', str(run)], stdout=stdout, stderr=stderr,
                                               stdin=subprocess.PIPE, cwd=ROOT, env=env, start_new_session=True,
                                               preexec_fn=lambda: os.sched_setaffinity(0, {args.cpu}))
                    if os.sched_getaffinity(process.pid) != {args.cpu}:
                        raise RuntimeError('benchmark CPU affinity failed')
                    wait_marker(process, stderr_path, 'READY')
                    raw, mapped = proc_identity(process.pid, runtime, env, True)
                    ready_path = out / f'run-{run}.ready.maps'
                    ready_path.write_text(raw)
                    previous = snapshot()
                    time.sleep(1)
                    current = snapshot()
                    monitor(previous, current, process.pid, args.cpu, monitor_file)
                    start = time.monotonic()
                    release(process)
                    while True:
                        time.sleep(1)
                        previous, current = current, snapshot()
                        monitor(previous, current, process.pid, args.cpu, monitor_file)
                        states = [state for (pid, _), (_, state, _) in current['processes'].items() if pid == process.pid]
                        if not states or states == ['Z'] or time.monotonic() - start > 1800:
                            raise RuntimeError('benchmark process exited or exceeded timeout')
                        raw, _ = proc_identity(process.pid, runtime, env, False, mapped)
                        monitor_file.write(json.dumps(dict(kind='mapping_check', run=run,
                                                           monotonic=time.monotonic(),
                                                           maps_sha256=hashlib.sha256(raw.encode()).hexdigest()),
                                                      sort_keys=True) + '\n')
                        monitor_file.flush()
                        if 'VERIGMP_CONTROL_DONE' in stderr_path.read_text():
                            raw, _ = proc_identity(process.pid, runtime, env, True, mapped)
                            done_path = out / f'run-{run}.done.maps'
                            done_path.write_text(raw)
                            release(process)
                            break
                    code = process.wait(timeout=10)
                    process = None
                    if code:
                        raise RuntimeError(f'benchmark run {run} failed with exit code {code}')
                parsed = parse_run(stdout_path.read_text(), run, [tuple(x) for x in prep['shapes']])
                report['runs'].append(dict(run=run, stdout_sha256=file_sha(stdout_path),
                                           stderr_sha256=file_sha(stderr_path), shapes=len(parsed),
                                           ldd_sha256=file_sha(out / f'run-{run}.ldd.log'),
                                           ready_maps_sha256=file_sha(ready_path),
                                           done_maps_sha256=file_sha(done_path), mapped_metadata=mapped))
                check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
                write_json(report_path, report)
        report['monitor_sha256'] = file_sha(out / 'monitor.jsonl')
        first = parse_run((out / 'run-0.csv').read_text(), 0, [tuple(x) for x in prep['shapes']])
        second = parse_run((out / 'run-1.csv').read_text(), 1, [tuple(x) for x in prep['shapes']])
        report['results'] = compare_runs(first, second)
        if boot_id() != report['boot_id']:
            raise RuntimeError('boot identity changed')
        check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
        report['status'] = 'complete_exploratory_screen'
        write_json(report_path, report)
        print(json.dumps({'status': report['status'], 'shapes': len(report['results'])}))
    except BaseException as error:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        report.update(status='invalid_window', failure=repr(error))
        if (out / 'monitor.jsonl').exists():
            report['monitor_sha256'] = file_sha(out / 'monitor.jsonl')
        write_json(report_path, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('self-test')
    run = sub.add_parser('run')
    run.add_argument('--prepared', type=Path, required=True)
    run.add_argument('--proof', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--cpu', type=int, required=True)
    run.add_argument('--authorized-window', action='store_true')
    args = parser.parse_args()
    if args.command == 'self-test':
        self_test()
    else:
        run_window(args)


if __name__ == '__main__':
    main()

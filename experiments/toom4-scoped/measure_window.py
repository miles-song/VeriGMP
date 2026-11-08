#!/usr/bin/env python3
"""Run the predeclared timing protocol only in an explicitly scheduled window."""
import argparse
import csv
import io
import json
import math
import os
from pathlib import Path
import platform
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


def expected_shapes():
    return REGISTERED | {(n, top) for n in EXTRA for top in (1, 31, 63, 64)}


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
                    av, bv, gv = statistics.mean(a), statistics.mean(other), statistics.mean(g)
                    blocks[block].append(dict(a=av, other=bv / av, a_over_g=av / gv,
                                              other_over_g=bv / gv, a_drift=a[1] / a[0],
                                              g_drift=g[1] / g[0]))
            if len(counts) != 1:
                raise RuntimeError('calibration changed across repetitions')
            block_results = []
            for samples in blocks:
                item = {key: statistics.median(x[key] for x in samples) for key in samples[0]}
                if not (0.90 <= item['a_drift'] <= 1.10 and 0.90 <= item['g_drift'] <= 1.10):
                    raise RuntimeError(f'within-run drift exceeded for operation={op}, n={n}, top={top}')
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
            a0, a1 = first[(op, n, top)][block]['a'], second[(op, n, top)][block]['a']
            cross_run = a1 / a0
            if not 0.90 <= cross_run <= 1.10:
                raise RuntimeError(f'between-run drift exceeded for operation={op}, n={n}, top={top}')
            blocks.append(dict(run_0=first[(op, n, top)][block],
                               run_1=second[(op, n, top)][block], a_cross_run=cross_run))
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
    def fixture(run):
        output = io.StringIO()
        writer = csv.writer(output, lineterminator='\n')
        writer.writerow(HEADER)
        for op in range(2):
            for rep in range(7):
                for pos, mode in enumerate(ORDERS[(rep + run) % 2]):
                    writer.writerow([run, op, 1, 64, rep, pos, mode, 1, 20_000_000])
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
    hz = os.sysconf('SC_CLK_TCK')
    previous = dict(time=10, busy=0, processes={})
    allowed = dict(time=11, busy=0, processes={})
    monitor(previous, allowed, None, None, io.StringIO())
    process_ticks = math.floor(0.10 * hz) + 1
    aggregate_ticks = math.floor(0.20 * hz) + 1
    for rejected in [dict(time=11, busy=process_ticks, processes={(999999, 1): (process_ticks, 'R', 1)}),
                     dict(time=11, busy=aggregate_ticks, processes={})]:
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
    values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    busy = sum(values[i] for i in (0, 1, 2, 5, 6, 7))
    processes = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            text = path.read_text()
            tail = text.rsplit(') ', 1)[1].split()
            processes[(int(path.parent.name), int(tail[19]))] = (int(tail[11]) + int(tail[12]), tail[0], int(tail[17]))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return dict(time=time.monotonic(), busy=busy, processes=processes)


def monitor(previous, current, benchmark_pid, expected_cpu, stream):
    elapsed = current['time'] - previous['time']
    if not 0.8 <= elapsed <= 3:
        raise RuntimeError('CPU monitoring interval outside 0.8..3 seconds')
    hz = os.sysconf('SC_CLK_TCK')
    if current['busy'] < previous['busy']:
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
    busy = max(0, current['busy'] - previous['busy'] - excluded)
    others = {str(pid): ticks for pid, ticks in tick_delta.items() if pid not in (os.getpid(), benchmark_pid)}
    benchmark = [(state, threads) for (pid, _), (_, state, threads) in current['processes'].items()
                 if pid == benchmark_pid]
    affinity = None
    if benchmark and benchmark[0][0] != 'Z':
        affinity = sorted(os.sched_getaffinity(benchmark_pid))
    entry = dict(monotonic=current['time'], elapsed_seconds=elapsed, ticks_per_second=hz,
                 guest_non_benchmark_ticks=busy, process_ticks=others,
                 benchmark_ticks=tick_delta.get(benchmark_pid, 0), monitor_ticks=tick_delta.get(os.getpid(), 0),
                 benchmark_threads=benchmark[0][1] if benchmark else None, benchmark_affinity=affinity)
    stream.write(json.dumps(entry, sort_keys=True) + '\n')
    stream.flush()
    if busy > 0.20 * hz * elapsed or any(ticks > 0.10 * hz * elapsed for ticks in others.values()):
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
        check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
        report.update(preparation_sha256=prep_hash, proof_report_sha256=proof_hash,
                      native_manifest_sha256=prep['native_manifest_sha256'],
                      source_sha256=prep['source_sha256'], identity_sha256=prep['identity_sha256'],
                      gmp_abi=prep['gmp_abi'], shapes=prep['shapes'])
        env = dict(os.environ, RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1')
        binary = prepared / 'measure'
        with (out / 'monitor.jsonl').open('w', encoding='utf-8') as monitor_file:
            for run in range(2):
                if boot_id() != report['boot_id']:
                    raise RuntimeError('boot identity changed')
                check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
                previous = snapshot()
                time.sleep(1)
                current = snapshot()
                monitor(previous, current, None, None, monitor_file)
                stdout_path, stderr_path = out / f'run-{run}.csv', out / f'run-{run}.stderr.log'
                with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
                    process = subprocess.Popen([str(binary), '--run', str(run)], stdout=stdout, stderr=stderr,
                                               cwd=ROOT, env=env, start_new_session=True,
                                               preexec_fn=lambda: os.sched_setaffinity(0, {args.cpu}))
                    if os.sched_getaffinity(process.pid) != {args.cpu}:
                        raise RuntimeError('benchmark CPU affinity failed')
                    start = time.monotonic()
                    while True:
                        time.sleep(1)
                        previous, current = current, snapshot()
                        monitor(previous, current, process.pid, args.cpu, monitor_file)
                        states = [state for (pid, _), (_, state, _) in current['processes'].items() if pid == process.pid]
                        if states == ['Z']:
                            break
                        if not states or time.monotonic() - start > 1800:
                            raise RuntimeError('benchmark process vanished or exceeded timeout')
                    code = process.wait(timeout=10)
                    process = None
                    if code:
                        raise RuntimeError(f'benchmark run {run} failed with exit code {code}')
                parsed = parse_run(stdout_path.read_text(), run, [tuple(x) for x in prep['shapes']])
                report['runs'].append(dict(run=run, stdout_sha256=file_sha(stdout_path),
                                           stderr_sha256=file_sha(stderr_path), shapes=len(parsed)))
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

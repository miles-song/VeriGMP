#!/usr/bin/env python3
"""Run the separately preregistered 24-shape screen in a scheduled window."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

import measure_window as core

ROOT = core.ROOT
WINDOW_SECONDS = 420
PROCESS_SECONDS = 180
LIMBS = (1, 256, 511, 512, 513, 1023, 1024, 1025, 1536, 2047, 2048, 2049,
         3072, 4095, 4096, 4097)


def expected_shapes():
    return ({(n, 63) for n in LIMBS} |
            {(n, top) for n in (1024, 2048) for top in (1, 31, 64)} |
            {(4096, top) for top in (1, 64)})


def deadline_signal(signum, _frame):
    raise TimeoutError('window deadline or external termination signal ' + str(signum))


def spawn(argv, cpu, active, **kwargs):
    signals = {signal.SIGALRM, signal.SIGTERM}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)

    def child_setup():
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        os.sched_setaffinity(0, {cpu})

    try:
        active[0] = subprocess.Popen(argv, start_new_session=True, preexec_fn=child_setup, **kwargs)
        return active[0]
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def kill_and_wait(process):
    result = {'pid': process.pid, 'signal': 'SIGKILL'}
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        result['group_already_gone'] = True
    try:
        result['returncode'] = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        result['wait_timeout'] = True
    return result


def self_test():
    core.self_test()
    previous_alarm = signal.signal(signal.SIGALRM, deadline_signal)
    previous_term = signal.signal(signal.SIGTERM, deadline_signal)
    active = [None]
    killed = None
    try:
        signal.setitimer(signal.ITIMER_REAL, 0.2)
        try:
            process = spawn(['/usr/bin/sleep', '30'], min(os.sched_getaffinity(0)), active,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait()
        except TimeoutError:
            if active[0] is not None:
                killed = kill_and_wait(active[0])
                active[0] = None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if active[0] is not None:
            kill_and_wait(active[0])
        signal.signal(signal.SIGALRM, previous_alarm)
        signal.signal(signal.SIGTERM, previous_term)
    if killed is None or killed.get('returncode') != -signal.SIGKILL:
        raise RuntimeError('deadline did not kill and reap the synthetic process group')
    if len(expected_shapes()) != 24:
        raise RuntimeError('screen shape count differs from preregistration')
    print('screen deadline and process-group cleanup self-test passed; no timing')


def run_screen(args):
    previous_alarm = signal.signal(signal.SIGALRM, deadline_signal)
    previous_term = signal.signal(signal.SIGTERM, deadline_signal)
    signal.setitimer(signal.ITIMER_REAL, WINDOW_SECONDS)
    active = [None]
    report_path = None
    report = None
    out = args.output.resolve()
    try:
        if not args.authorized_window:
            raise RuntimeError('the parent must schedule a quiet timing window')
        env = core.benchmark_environment()
        if dict(os.environ) != env:
            raise RuntimeError('launch controller with exactly the predeclared clean environment')
        prepared, proof = args.prepared.resolve(), args.proof.resolve()
        if out.exists() or out.is_relative_to(ROOT):
            raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
        if args.cpu not in os.sched_getaffinity(0):
            raise RuntimeError('requested CPU is outside current affinity')
        out.mkdir(parents=True)
        report_path = out / 'measurement.json'
        report = dict(status='running', benchmark_run=True, scope='24-shape exploratory screen',
                      window_timeout_seconds=WINDOW_SECONDS, process_timeout_seconds=PROCESS_SECONDS,
                      cpu=args.cpu, cpu_identity=core.cpu_identity(args.cpu), boot_id=core.boot_id(),
                      platform=platform.platform(), original_affinity=sorted(os.sched_getaffinity(0)), runs=[])
        core.write_json(report_path, report)
        prep_file = prepared / 'preparation.json'
        prep_hash, proof_hash = core.file_sha(prep_file), core.file_sha(proof / 'verification.json')
        prep, proof_data = json.loads(prep_file.read_text()), json.loads((proof / 'verification.json').read_text())
        if prep['proof_report_sha256'] != proof_hash or prep['benchmark_environment'] != env:
            raise RuntimeError('preparation proof or environment differs')
        if len(prep['shapes']) != 24 or {tuple(shape) for shape in prep['shapes']} != expected_shapes():
            raise RuntimeError('prepared shapes differ from the preregistered screen')
        core.check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
        report.update(preparation_sha256=prep_hash, proof_report_sha256=proof_hash,
                      native_manifest_sha256=prep['native_manifest_sha256'], source_sha256=prep['source_sha256'],
                      identity_sha256=prep['identity_sha256'], gmp_abi=prep['gmp_abi'], shapes=prep['shapes'],
                      environment=env, runtime_sha256=prep['runtime_sha256'])
        binary = prepared / 'measure'
        with (out / 'monitor.jsonl').open('w', encoding='utf-8') as monitor_file:
            for run in range(2):
                if core.boot_id() != report['boot_id']:
                    raise RuntimeError('boot identity changed')
                core.check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
                runtime, linked = core.runtime_identity(binary, env)
                if runtime != prep['runtime_sha256']:
                    raise RuntimeError('runtime dependency resolution changed')
                (out / f'run-{run}.ldd.log').write_text(linked)
                previous = core.snapshot()
                time.sleep(1)
                current = core.snapshot()
                core.monitor(previous, current, None, None, monitor_file)
                stdout_path, stderr_path = out / f'run-{run}.csv', out / f'run-{run}.stderr.log'
                with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
                    process = spawn([str(binary), '--run', str(run)], args.cpu, active, stdout=stdout, stderr=stderr,
                                    stdin=subprocess.PIPE, cwd=ROOT, env=env)
                    if os.sched_getaffinity(process.pid) != {args.cpu}:
                        raise RuntimeError('benchmark CPU affinity failed')
                    core.wait_marker(process, stderr_path, 'READY')
                    raw, mapped = core.proc_identity(process.pid, runtime, env, True)
                    ready_path = out / f'run-{run}.ready.maps'
                    ready_path.write_text(raw)
                    previous = core.snapshot()
                    time.sleep(1)
                    current = core.snapshot()
                    core.monitor(previous, current, process.pid, args.cpu, monitor_file)
                    start = time.monotonic()
                    core.release(process)
                    while True:
                        time.sleep(1)
                        previous, current = current, core.snapshot()
                        core.monitor(previous, current, process.pid, args.cpu, monitor_file)
                        states = [state for (pid, _), (_, state, _) in current['processes'].items() if pid == process.pid]
                        if not states or states == ['Z'] or time.monotonic() - start > PROCESS_SECONDS:
                            raise RuntimeError('benchmark process exited or exceeded 180-second timeout')
                        raw, _ = core.proc_identity(process.pid, runtime, env, False, mapped)
                        monitor_file.write(json.dumps(dict(kind='mapping_check', run=run, monotonic=time.monotonic(),
                                                           maps_sha256=hashlib.sha256(raw.encode()).hexdigest()),
                                                      sort_keys=True) + '\n')
                        monitor_file.flush()
                        if 'VERIGMP_CONTROL_DONE' in stderr_path.read_text():
                            raw, _ = core.proc_identity(process.pid, runtime, env, True, mapped)
                            done_path = out / f'run-{run}.done.maps'
                            done_path.write_text(raw)
                            core.release(process)
                            break
                    code = process.wait(timeout=10)
                    active[0] = None
                    if code:
                        raise RuntimeError(f'benchmark run {run} failed with exit code {code}')
                parsed = core.parse_run(stdout_path.read_text(), run, [tuple(x) for x in prep['shapes']])
                report['runs'].append(dict(run=run, stdout_sha256=core.file_sha(stdout_path),
                                           stderr_sha256=core.file_sha(stderr_path), shapes=len(parsed),
                                           ldd_sha256=core.file_sha(out / f'run-{run}.ldd.log'),
                                           ready_maps_sha256=core.file_sha(ready_path),
                                           done_maps_sha256=core.file_sha(done_path), mapped_metadata=mapped))
                core.check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
                core.write_json(report_path, report)
        report['monitor_sha256'] = core.file_sha(out / 'monitor.jsonl')
        first = core.parse_run((out / 'run-0.csv').read_text(), 0, [tuple(x) for x in prep['shapes']])
        second = core.parse_run((out / 'run-1.csv').read_text(), 1, [tuple(x) for x in prep['shapes']])
        report['results'] = core.compare_runs(first, second)
        if core.boot_id() != report['boot_id']:
            raise RuntimeError('boot identity changed')
        core.check_identity(prep, prep_file, prep_hash, proof, proof_data, proof_hash)
        report['status'] = 'complete_exploratory_screen'
        core.write_json(report_path, report)
        print(json.dumps({'status': report['status'], 'operation_shapes': len(report['results'])}))
    except BaseException as error:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGTERM})
        signal.setitimer(signal.ITIMER_REAL, 0)
        if active[0] is not None:
            cleanup = kill_and_wait(active[0])
            if report is not None:
                report['cleanup'] = cleanup
        if report is not None and report_path is not None:
            report.update(status='invalid_window', failure=repr(error))
            if (out / 'monitor.jsonl').exists():
                report['monitor_sha256'] = core.file_sha(out / 'monitor.jsonl')
            core.write_json(report_path, report)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_alarm)
        signal.signal(signal.SIGTERM, previous_term)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM, signal.SIGTERM})


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
        run_screen(args)


if __name__ == '__main__':
    main()

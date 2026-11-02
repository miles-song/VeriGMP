"""Measure one immutable declared run; retain failures and every raw sample."""
from pathlib import Path
import argparse
import csv
import io
import json
import math
import os
import platform
import statistics
import subprocess
import time
from common import check_hashes, check_prepared, now, sha, write


def process_sample():
    result = {}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            text = (directory / 'stat').read_text()
            fields = text[text.rindex(')') + 2:].split()
            result[int(directory.name)] = {'name': text[text.index('(')+1:text.rindex(')')],
                'ticks': int(fields[11]) + int(fields[12]), 'last_cpu': int(fields[36])}
        except (OSError, ValueError, IndexError):
            pass
    return result


def deltas(a, b, seconds, excluded):
    return [{'pid': pid, 'name': row['name'], 'last_cpu': row['last_cpu'],
        'cpu_percent': 100*(row['ticks']-a[pid]['ticks'])/os.sysconf('SC_CLK_TCK')/seconds}
        for pid, row in b.items() if pid in a and pid not in excluded and row['ticks'] > a[pid]['ticks']]


def host_probe(stage, directory, name):
    result = subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile',
        '-NonInteractive', '-Command', (stage / 'host_probe.ps1').read_text()], capture_output=True, timeout=30)
    (directory / (name + '.stdout')).write_bytes(result.stdout)
    (directory / (name + '.stderr')).write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError('Windows quiet probe failed')
    report = json.loads(result.stdout.decode('utf-8-sig'))
    if report['Status'] != 'pass':
        raise RuntimeError('Windows quiet probe did not pass')
    return report


def measure(stage, phase, tag, authorization):
    if not authorization.strip():
        raise RuntimeError('Root-coordinated quiet window reference required')
    directory = stage / (phase + '-' + tag)
    directory.mkdir()
    report = {'status': 'running', 'phase': phase, 'tag': tag, 'started_utc': now(),
        'quiet_window_authorization': authorization, 'benchmark_started': False,
        'platform': platform.platform(), 'cpu': 0, 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'cpu_model': next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))}
    write(directory / 'measurement.json', report)
    try:
        check_prepared(stage)
        built = stage / (phase + '-build')
        binding = json.loads((built / 'binding.json').read_text())
        if binding['status'] != 'pass':
            raise RuntimeError('Benchmark build not accepted')
        identities = dict(binding['paired_library_sha256'] | binding['runtime_sha256'] | binding['toolchain']['sha256'])
        identities[str(built / 'compare.rs')] = binding['source_sha256']
        identities[str(built / 'compare')] = binding['binary_sha256']
        identities[str(stage / 'policy.json')] = binding['policy_sha256']
        identities[str(stage / 'build-evidence/build.json')] = binding['build_gate_sha256']
        identities[str(stage / 'preparation.json')] = binding['source_manifest_sha256']
        identities.update({str(p): sha(p) for p in stage.iterdir() if p.is_file()})
        identities[str(built / 'binding.json')] = sha(built / 'binding.json')
        if phase == 'confirmation':
            gate = json.loads((stage / 'acceptance/verification.json').read_text())
            if gate['status'] != 'pass':
                raise RuntimeError('Full selected-source gate has not passed')
            identities[str(stage / 'acceptance/verification.json')] = sha(stage / 'acceptance/verification.json')
        check_hashes(identities)
        report['identities_before_after'] = identities
        time.sleep(5)
        report['windows_before'] = host_probe(stage, directory, 'host-before')
        a = process_sample()
        started = time.monotonic()
        time.sleep(1)
        b = process_sample()
        report['wsl_before'] = deltas(a, b, time.monotonic()-started, {os.getpid()})
        if any(row['CPUPercent'] > 10 for row in report['windows_before']['Rows']):
            raise RuntimeError('Windows host busy; benchmark not started')
        if any(row['cpu_percent'] > 10 for row in report['wsl_before']):
            raise RuntimeError('WSL host busy; benchmark not started')
        report['benchmark_started'] = True
        report['measurement_started_utc'] = now()
        write(directory / 'measurement.json', report)
        a = process_sample()
        started = time.monotonic()
        with (directory / 'benchmark.csv').open('w') as raw, (directory / 'calibration.csv').open('w') as calibration:
            child = subprocess.Popen([built / 'compare'], cwd=stage, stdout=raw, stderr=calibration,
                text=True, preexec_fn=lambda: os.sched_setaffinity(0, {0}))
            code = child.wait(timeout=600)
        report['wsl_during'] = deltas(a, process_sample(), time.monotonic()-started, {os.getpid(), child.pid})
        report['measurement_finished_utc'] = now()
        report['windows_after'] = host_probe(stage, directory, 'host-after')
        if code:
            raise RuntimeError('Benchmark runtime failure; retain all observations')
        if any(row['cpu_percent'] > 10 for row in report['wsl_during']):
            raise RuntimeError('Other WSL work during timing; results retained as contaminated')
        rows = list(csv.DictReader((directory / 'benchmark.csv').open()))
        groups = {}
        for row in rows:
            groups.setdefault(tuple(int(row[k]) for k in ['operation','limbs','top','mode']), []).append(row)
        expected = {(op,n,top,mode) for op in [0,1] for n,top in binding['shapes'] for mode in range(len(binding['modes']))}
        if set(groups) != expected:
            raise RuntimeError('Incomplete registered matrix')
        medians = {}
        for key, records in groups.items():
            if len(records) != 7 or {int(r['repetition']) for r in records} != set(range(7)):
                raise RuntimeError('Incomplete repetitions')
            if any(int(r['iterations']) <= 0 or int(r['ns']) < 10_000_000 for r in records):
                raise RuntimeError('Recorded batch duration below registered minimum')
            medians[key] = statistics.median(int(r['ns'])/int(r['iterations']) for r in records)
        for op in [0,1]:
            for n, top in binding['shapes']:
                actual = [int(r['mode']) for r in rows if int(r['operation']) == op and int(r['limbs']) == n and int(r['top']) == top]
                if actual != [(j+rep)%len(binding['modes']) for rep in range(7) for j in range(len(binding['modes']))]:
                    raise RuntimeError('Mode order differs from registered rotation')
        report['medians'] = [{'operation': op, 'limbs': n, 'top': top, 'mode': binding['modes'][mode],
            'ns': value, 'over_baseline': value/medians[op,n,top,0],
            'over_gmp': value/medians[op,n,top,len(binding['modes'])-1]}
            for (op,n,top,mode), value in sorted(medians.items())]
        report['raw_sha256'] = sha(directory / 'benchmark.csv')
        report['calibration_sha256'] = sha(directory / 'calibration.csv')
        report['samples'] = len(rows)
        report['minimum_batch_ns'] = min(int(r['ns']) for r in rows)
        check_hashes(identities)
        check_prepared(stage)
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != report['boot_id']:
            raise RuntimeError('Boot identity changed')
        report.update(status='pass', finished_utc=now(), source_tool_artifact_checks_before_after=True)
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}', finished_utc=now())
    write(directory / 'measurement.json', report)
    print(json.dumps({k: report[k] for k in ['status','error','samples','minimum_batch_ns'] if k in report}, indent=2))
    return report['status'] == 'pass'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['exploration','confirmation'])
    parser.add_argument('--tag', required=True)
    parser.add_argument('--quiet-window', required=True)
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if not __import__('re').fullmatch('[a-z0-9_-]+', args.tag):
        raise ValueError('Invalid measurement tag')
    raise SystemExit(not measure(args.stage.resolve(), args.phase, args.tag, args.quiet_window))

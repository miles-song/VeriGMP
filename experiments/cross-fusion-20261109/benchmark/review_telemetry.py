#!/usr/bin/env python3
"""Bind and assess retained Windows/WSL telemetry for one benchmark session."""
import argparse
import datetime
import json
from pathlib import Path
import re

from measure import sha


def timestamp(value):
    result = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp lacks timezone')
    return result.timestamp()


def memory_pressure(row, kind):
    if kind == 'host':
        memory = row['memory']
        return float(memory['load_percent']) >= 90
    match = re.search(r'(?m)^some\s+avg10=([0-9.]+)', row['memory_pressure'])
    if not match:
        raise ValueError('WSL memory PSI is unavailable')
    return float(match.group(1)) >= 5


def busy_ticks(row):
    fields = row['proc_stat'].splitlines()[0].split()
    if fields[0] != 'cpu' or len(fields) < 9:
        raise ValueError('WSL aggregate CPU counters are unavailable')
    values = list(map(int, fields[1:]))
    return sum(values[index] for index in (0, 1, 2, 5, 6, 7))


def evaluate_series(rows, kind, start, end, allowed, lifetimes=()):
    failures, unknown, intervals = [], [], []
    if len(rows) < 2:
        return dict(failures=['fewer than two ' + kind + ' samples'], unknown=[], intervals=[])
    if timestamp(rows[0]['utc_start']) > start or timestamp(rows[-1]['utc_start']) < end:
        failures.append(kind + ' telemetry does not cover the complete session')
    monotonic = 'monotonic_ms' if kind == 'host' else 'monotonic_ns'
    scale = 1000 if kind == 'host' else 1_000_000_000
    clock_key = 'start_100ns' if kind == 'host' else 'start_ticks'
    cpu_key = 'cpu_100ns' if kind == 'host' else 'cpu_ticks'
    max_gap = 0.0
    cpu_streak = memory_streak = unexplained_streak = 0.0
    vm_identity = None
    for a, b in zip(rows, rows[1:]):
        t0, t1 = timestamp(a['utc_start']), timestamp(b['utc_start'])
        elapsed = (b[monotonic] - a[monotonic]) / scale
        wall = t1 - t0
        max_gap = max(max_gap, elapsed, wall)
        if elapsed <= 0 or elapsed > 2 or wall <= 0 or wall > 2 or abs(elapsed - wall) > 0.2:
            failures.append(kind + ' telemetry gap or clock inconsistency')
        for sample in (a, b):
            duration = timestamp(sample['utc_end']) - timestamp(sample['utc_start'])
            if duration < 0 or duration > 2:
                failures.append(kind + ' sample collection exceeded two seconds')
            if not sample['processes']:
                unknown.append(kind + ' process snapshot is empty')
            if kind == 'wsl' and sample['errors']:
                unknown.append('WSL process snapshots have read errors')
            if kind == 'wsl':
                for vanished in sample['vanished']:
                    moment = timestamp(vanished['utc'])
                    matches = [life for life in lifetimes if life['pid'] == vanished['pid']
                               and life['start'] <= moment <= life['end']]
                    if len(matches) != 1:
                        unknown.append('a vanished WSL process cannot be attributed to a unique benchmark child')
        if t1 < start or t0 > end or elapsed <= 0:
            continue
        before = {(p['pid'], p[clock_key]): p for p in a['processes']}
        after = {(p['pid'], p[clock_key]): p for p in b['processes']}
        if len(before) != len(a['processes']) or len(after) != len(b['processes']):
            unknown.append(kind + ' process identities are not unique')
        if kind == 'host':
            for processes in (a['processes'], b['processes']):
                vm = [p for p in processes if p['name'].casefold() in ('vmmem', 'vmmemwsl')]
                if len(vm) != 1:
                    unknown.append('WSL host aggregate identity is ambiguous')
                else:
                    identity = (vm[0]['pid'], vm[0][clock_key])
                    if vm_identity is not None and vm_identity != identity:
                        unknown.append('WSL host aggregate identity changed')
                    vm_identity = identity
        cpu_unit = 10_000_000 if kind == 'host' else b['ticks_per_second']
        if kind == 'wsl' and (a['ticks_per_second'] != cpu_unit or cpu_unit <= 0):
            unknown.append('WSL clock tick frequency changed')
        competitors = []
        observed_cpu = 0.0
        vm_cpu = 0.0
        for identity, process in after.items():
            delta = process[cpu_key] - before.get(identity, {}).get(cpu_key, 0)
            if delta < 0:
                unknown.append(kind + ' process CPU counter decreased')
                continue
            seconds = delta / cpu_unit
            observed_cpu += seconds
            if kind == 'host' and identity[0] == 0:
                continue
            if kind == 'host' and identity == vm_identity:
                vm_cpu += seconds
                continue
            if kind == 'wsl' and identity in allowed:
                continue
            if seconds:
                competitors.append(dict(pid=identity[0], start=identity[1],
                                        name=process['name'], cpu_seconds=seconds))
        total = sum(process['cpu_seconds'] for process in competitors)
        rate = total / elapsed
        cpu_streak = cpu_streak + elapsed if rate > 0.2 else 0
        if cpu_streak >= 5:
            failures.append(kind + ' competing processes exceeded 0.2 CPUs for at least five seconds')
        busy = unexplained = None
        if kind == 'wsl':
            try:
                busy = (busy_ticks(b) - busy_ticks(a)) / cpu_unit
                if busy < 0:
                    raise ValueError('WSL aggregate CPU counter decreased')
                overlapping = sum(life['cpu_seconds'] for life in lifetimes
                                  if life['start'] <= t1 and life['end'] >= t0)
                # A whole child CPU time may overlap only partially; subtracting it all
                # deliberately makes this a lower bound on unaccounted CPU.
                unexplained = max(0.0, busy - observed_cpu - overlapping - 0.1)
                unexplained_streak = unexplained_streak + elapsed if unexplained / elapsed > 0.2 else 0
                if unexplained_streak >= 5:
                    failures.append('WSL unexplained CPU exceeded 0.2 CPUs for at least five seconds')
            except (KeyError, ValueError, IndexError, TypeError):
                unknown.append('WSL aggregate CPU counters are unavailable')
        try:
            memory_high = memory_pressure(a, kind) and memory_pressure(b, kind)
            memory_streak = memory_streak + elapsed if memory_high else 0
            if memory_streak >= 5:
                failures.append(kind + ' memory pressure exceeded the preregistered limit for five seconds')
        except (KeyError, ValueError, TypeError):
            unknown.append(kind + ' memory pressure data are unavailable')
        intervals.append(dict(start=a['utc_start'], end=b['utc_start'], seconds=elapsed,
                              competing_cpu_seconds=total, competing_cpus=rate,
                              wsl_host_aggregate_cpu_seconds=vm_cpu,
                              wsl_busy_cpu_seconds=busy, wsl_unexplained_cpu_lower_bound=unexplained,
                              competitors=sorted(competitors, key=lambda p: -p['cpu_seconds'])))
    return dict(failures=sorted(set(failures)), unknown=sorted(set(unknown)),
                max_gap_seconds=max_gap, intervals=intervals)


def read_rows(path):
    with path.open(encoding='utf-8-sig') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    build = json.loads(args.build.read_text())
    paths = dict(report=args.report.resolve(), build=args.build.resolve(),
                 raw=Path(report['raw']).resolve(), host=Path(report['host_telemetry']).resolve(),
                 wsl=Path(report['wsl_telemetry']).resolve())
    before = {name: sha(path) for name, path in paths.items()}
    receipt = dict(status='inconclusive', paths={k: str(v) for k, v in paths.items()},
                   report_sha256=before['report'], raw_sha256=before['raw'],
                   build_sha256=before['build'], host_sha256=before['host'], wsl_sha256=before['wsl'],
                   review_script=str(Path(__file__).resolve()), review_script_sha256=sha(__file__),
                   limitations=['Host actual frequency and temperature are unavailable; throttling is unknown.',
                                'Guest /proc process snapshots do not cover other WSL distributions or VMs.',
                                'Processes that both start and exit between snapshots may be missed.',
                                'The WSL host aggregate is retained but cannot identify processes in other guests.',
                                'An independent reviewer must inspect the WSL inventories and the full logs.'])
    try:
        if before['raw'] != report['raw_sha256'] or before['build'] != report['build_sha256']:
            raise ValueError('session raw or build identity changed')
        if build['harness_files'].get(str(Path(__file__).resolve())) != sha(__file__):
            raise ValueError('review script is not part of the fixed harness')
        raw = read_rows(paths['raw'])
        outcomes = [r for r in raw if r.get('record') == 'outcome']
        if any(r.get('process_identity', {}).get('start_ticks') is None for r in outcomes):
            raise ValueError('a benchmark process identity is incomplete')
        allowed = {(r['process_identity']['pid'], r['process_identity']['start_ticks']) for r in outcomes}
        lifetimes = [dict(pid=r['process_identity']['pid'], start_ticks=r['process_identity']['start_ticks'],
                          start=timestamp(r['started_utc']), end=timestamp(r['ended_utc']),
                          cpu_seconds=r['child_cpu_seconds']) for r in outcomes]
        start, end = timestamp(report['session_start_utc']), timestamp(report['session_end_utc'])
        if end < start:
            raise ValueError('invalid session time range')
        host, wsl = read_rows(paths['host']), read_rows(paths['wsl'])
        inventories = [row for row in host if row.get('record') == 'wsl_inventory']
        if (len(inventories) != 2 or [r['phase'] for r in inventories] != ['before', 'after']
                or host[0] != inventories[0] or host[-1] != inventories[-1]
                or any(r['exit_code'] != 0 or r['power_exit_code'] != 0 or not r['output'].strip()
                       or not r['power_plan'].strip() for r in inventories)):
            raise ValueError('WSL inventory or power plan before/after is missing or incomplete')
        if not wsl or wsl[-1].get('record') != 'monitor_end':
            raise ValueError('WSL monitor has not recorded a clean stop')
        if timestamp(inventories[0]['utc']) > start or timestamp(inventories[-1]['utc']) < end:
            raise ValueError('WSL inventory does not bracket the session')
        host_samples = [row for row in host if row.get('record') == 'sample']
        wsl_samples = [row for row in wsl if row.get('record') == 'sample']
        receipt['wsl_inventory'] = inventories
        receipt['host'] = evaluate_series(host_samples, 'host', start, end, set())
        receipt['wsl'] = evaluate_series(wsl_samples, 'wsl', start, end, allowed, lifetimes)
        failures = receipt['host']['failures'] + receipt['wsl']['failures']
        unknown = receipt['host']['unknown'] + receipt['wsl']['unknown']
        if inventories[0]['output'] != inventories[-1]['output']:
            failures.append('WSL distribution inventory changed during the session')
        if inventories[0]['power_plan'] != inventories[-1]['power_plan']:
            failures.append('host power plan changed during the session')
        if {name: sha(path) for name, path in paths.items()} != before:
            failures.append('session or telemetry bytes changed during review')
        if failures:
            receipt['status'] = 'environment_violation'
            receipt['reason'] = '; '.join(sorted(set(failures)))
        elif unknown:
            receipt['status'] = 'inconclusive'
            receipt['reason'] = '; '.join(sorted(set(unknown)))
        else:
            receipt['status'] = 'pass_pending_independent_review'
            receipt['reason'] = 'automated telemetry thresholds passed; independent review remains required'
    except (KeyError, IndexError, TypeError, ValueError, OSError, json.JSONDecodeError) as error:
        receipt['status'] = 'inconclusive'
        receipt['reason'] = str(error)
    with args.output.open('x') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(status=receipt['status'], reason=receipt['reason'],
                          receipt=str(args.output.resolve()), sha256=sha(args.output)), sort_keys=True))


if __name__ == '__main__':
    main()

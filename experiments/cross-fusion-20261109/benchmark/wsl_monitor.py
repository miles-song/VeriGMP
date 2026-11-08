#!/usr/bin/env python3
"""Capture timestamped WSL-wide process CPU snapshots until a stop marker exists."""
import argparse
import datetime
import json
import os
from pathlib import Path
import time


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def process_snapshot():
    processes = []
    vanished = []
    errors = []
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            value = (directory / 'stat').read_text()
            name, rest = value.split('(', 1)[1].rsplit(')', 1)
            fields = rest.split()
            processes.append(dict(pid=int(directory.name), name=name, ppid=int(fields[1]),
                                  cpu_ticks=int(fields[11]) + int(fields[12]),
                                  start_ticks=int(fields[19])))
        except (FileNotFoundError, ProcessLookupError):
            vanished.append(dict(pid=int(directory.name), utc=utc()))
        except (OSError, ValueError, IndexError) as error:
            errors.append(dict(pid=int(directory.name), error=type(error).__name__))
    return processes, vanished, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stop-file', type=Path, required=True)
    args = parser.parse_args()
    if args.stop_file.exists():
        raise RuntimeError('stop marker already exists')
    ticks = int(os.sysconf('SC_CLK_TCK'))
    deadline = time.monotonic()
    with args.output.open('x') as stream:
        while True:
            start = utc()
            monotonic_ns = time.monotonic_ns()
            processes, vanished, errors = process_snapshot()
            proc_stat = Path('/proc/stat').read_text()
            cpu_pressure = Path('/proc/pressure/cpu').read_text()
            memory_pressure = Path('/proc/pressure/memory').read_text()
            meminfo = Path('/proc/meminfo').read_text()
            monitor = next(row for row in processes if row['pid'] == os.getpid())
            row = dict(record='sample', utc_start=start, utc_end=utc(), monotonic_ns=monotonic_ns,
                       ticks_per_second=ticks, processes=processes, vanished=vanished,
                       monitor=dict(pid=monitor['pid'], start_ticks=monitor['start_ticks']),
                       errors=errors, proc_stat=proc_stat, cpu_pressure=cpu_pressure,
                       memory_pressure=memory_pressure, meminfo=meminfo)
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush()
            if args.stop_file.exists():
                stream.write(json.dumps(dict(record='monitor_end', utc=utc(),
                                             monitor=row['monitor']), sort_keys=True) + '\n')
                stream.flush()
                break
            deadline += 1
            time.sleep(max(0, deadline - time.monotonic()))


if __name__ == '__main__':
    main()

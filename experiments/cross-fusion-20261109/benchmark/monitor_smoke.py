#!/usr/bin/env python3
"""Assess real monitor logs against a synthetic, explicitly non-benchmark session."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

from measure import sha
from review_telemetry import read_rows, timestamp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=Path, required=True)
    parser.add_argument('--wsl', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    host = [r for r in read_rows(args.host) if r.get('record') == 'sample']
    wsl = [r for r in read_rows(args.wsl) if r.get('record') == 'sample']
    start = max(timestamp(host[0]['utc_start']), timestamp(wsl[0]['utc_start'])) + 1
    end = min(timestamp(host[-1]['utc_start']), timestamp(wsl[-1]['utc_start'])) - 1
    if end <= start:
        raise RuntimeError('not enough overlapping monitor samples')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    raw = output / 'synthetic-empty-raw.jsonl'
    raw.touch(exist_ok=False)
    to_iso = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).isoformat()
    report = dict(status='synthetic_monitor_smoke_no_benchmark', raw=str(raw), raw_sha256=sha(raw),
                  build_sha256=sha(args.build), host_telemetry=str(args.host.resolve()),
                  wsl_telemetry=str(args.wsl.resolve()), session_start_utc=to_iso(start), session_end_utc=to_iso(end))
    report_path = output / 'synthetic-report.json'
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    review_path = output / 'review.json'
    command = [sys.executable, str(Path(__file__).with_name('review_telemetry.py')),
               '--report', str(report_path), '--build', str(args.build.resolve()), '--output', str(review_path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    summary = dict(purpose='non-benchmark monitor smoke', command=command,
                   exit_code=result.returncode, stdout=result.stdout.strip(), stderr=result.stderr,
                   host_sha256=sha(args.host), wsl_sha256=sha(args.wsl),
                   synthetic_report_sha256=sha(report_path), review_sha256=sha(review_path))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()

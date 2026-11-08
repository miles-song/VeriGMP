#!/usr/bin/env python3
"""Prove and compile the source-fixed combined native crate exactly once."""
import argparse
import json
import os
from pathlib import Path
from common import *


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--deps-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepared, data = checked_prepared(args.prepared)
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh external proof output')
    out.mkdir(parents=True)
    report = dict(status='running', benchmark_run=False, commands=[],
                  prepared_sha256=file_sha(prepared / 'prepared.json'),
                  source_head=data['source_head'], cell='both',
                  native_sha256=data['cells']['both']['native_sha256'],
                  native_manifest_sha256=data['cells']['both']['native_manifest_sha256'])
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    run = command_runner(out, report, env)
    try:
        verifier, pin, report['tools'] = pinned_tools(args.deps_root.resolve(), prepared / 'both/native', run, env)
        result = run(['taskset', '-c', '2-15', verifier, 'native/lib.rs', '--crate-name', 'verigmp',
                      '--crate-type', 'lib', '--num-threads', '2', '--no-cheating', '--compile', '-O',
                      '--export', out / 'verigmp.vir', '-o', out / 'libverigmp.rlib'],
                     'library', prepared / 'both')
        report.update(status='full_library_pass',
                      verified_items=positive(result.returncode, (result.stdout + result.stderr).decode()),
                      verification_scope='complete combined native/lib.rs')
        report['exports_sha256'] = {name: file_sha(out / name) for name in ('libverigmp.rlib', 'verigmp.vir')}
        checked_prepared(prepared)
        write_json(out / 'verification.json', report)
        print(json.dumps(dict(status=report['status'], verified_items=report['verified_items'],
                              native_manifest_sha256=report['native_manifest_sha256']), indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(out / 'verification.json', report)
        raise


if __name__ == '__main__':
    main()

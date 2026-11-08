#!/usr/bin/env python3
"""Reconstruct four exact immutable native sources; never executes arithmetic."""
import argparse
import json
from pathlib import Path
import re
from common import *


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh external output')
    if git('status', '--porcelain').strip():
        raise RuntimeError('commit experiment inputs first')
    head = git('rev-parse', 'HEAD').decode().strip()
    names = git('ls-tree', '-r', '--name-only', BASE, 'native').decode().splitlines()
    if len(names) != 57 or len([n for n in names if n.endswith('.rs')]) != 50:
        raise RuntimeError('baseline native inventory drift')
    base = {name: git('show', BASE + ':' + name) for name in names}
    if any((ROOT / name).read_bytes() != data for name, data in base.items()):
        raise RuntimeError('production native must remain exact baseline')
    inputs = [p.relative_to(ROOT).as_posix() for p in sorted(FEATURE.iterdir()) if p.is_file()]
    inputs += ['AGENTS.md', 'experiments/packed-convolution/layout_verify.py',
               'experiments/packed-convolution/verus_logs.py']
    legacy = 'experiments/arithmetic-precondition-checks-20261108/'
    inputs += [legacy + name for name in ('bench.rs', 'runtime.rs', 'oracle.py', 'measure.py')]
    sources = {name: (ROOT / name).read_bytes() for name in sorted(inputs)}
    for name, data in sources.items():
        if git('show', head + ':' + name) != data:
            raise RuntimeError('HEAD bytes differ: ' + name)
    fixture_files = {'low_runtime.rs': 'low_runtime.rs', 'square_oracle.py': 'direct_oracle.py',
                     'codegen.py': 'codegen.py'}
    for local, original in fixture_files.items():
        if (FEATURE / local).read_bytes() != git('show', FIXTURE + ':experiments/double-cross-20261108/' + original):
            raise RuntimeError('historical fixture identity drift: ' + local)
    out.mkdir(parents=True)
    report = dict(status='running', benchmark_run=False, source_head=head, base=BASE,
                  factors=dict(double=DOUBLE, checks=CHECKS), cells={},
                  inputs_sha256={name: sha(data) for name, data in sources.items()})
    for name, data in sources.items():
        target = out / 'inputs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for label in LABELS:
        files = dict(base)
        origins = {name: BASE for name in names}
        if label in ('double', 'both'):
            for name in DOUBLE_FILES:
                files[name] = git('show', DOUBLE + ':' + name)
                origins[name] = DOUBLE
        if label in ('checks', 'both'):
            for name in CHECK_FILES:
                files[name] = git('show', CHECKS + ':' + name)
                origins[name] = CHECKS
        for name, data in files.items():
            target = out / label / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        digests = {name: sha(data) for name, data in files.items()}
        changed = sorted(name for name in names if files[name] != base[name])
        expected = sorted((DOUBLE_FILES if label in ('double', 'both') else ()) +
                          (CHECK_FILES if label in ('checks', 'both') else ()))
        if changed != expected:
            raise RuntimeError('unexpected changed source scope: ' + label)
        for name in changed:
            if re.search(r'\b(?:assume|admit|axiom)\s*\(|external_body|external_fn_specification|'
                         r'verify\s*=\s*false|\bunsafe\b|extern\s+"C"', files[name].decode()):
                raise RuntimeError('proof escape/unsafe in factor source')
        report['cells'][label] = dict(native_sha256=digests, changed_from_baseline=changed,
                                      native_manifest_sha256=mapping_sha(digests), origins=origins)
    # Check the public function contracts by exact prefix, not by a similar model.
    def contract(data, name):
        text = data.decode()
        start = text.index('pub fn ' + name + '(')
        end = text.index('\n{', start)
        return text[start:end]
    for label in LABELS:
        for source, name in (('native/verified/square_low.rs', 'low'),
                             ('native/verified/fast_multiply.rs', 'full')):
            if contract((out / label / source).read_bytes(), name) != contract(base[source], name):
                raise RuntimeError('public contract drift: ' + label + '/' + name)
    report.update(status='pass', public_contracts_byte_identical=True,
                  native_file_count=57, native_rust_file_count=50)
    write_json(out / 'prepared.json', report)
    print(json.dumps(dict(status='pass', source_head=head,
                         cells={k: v['native_manifest_sha256'] for k, v in report['cells'].items()}), indent=2))


if __name__ == '__main__':
    main()

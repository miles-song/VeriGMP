"""Full library proof/compile and default integer oracle for every registered mode."""
from pathlib import Path
import argparse
import json
import re
import subprocess
from common import bind_tools, check_hashes, check_prepared, checked, default_cases, now, sha, verified, write


def build(stage):
    out = stage / 'build-evidence'
    out.mkdir()
    report = {'status': 'running', 'started_utc': now(), 'benchmark_run': False,
        'libraries': {}, 'default_oracles': {}}
    write(out / 'build.json', report)
    try:
        prepared = check_prepared(stage)
        policy = json.loads((stage / 'policy.json').read_text())
        report['source_sha256'] = {name: files for name, files in prepared['variants'].items()}
        report['infrastructure_sha256'] = prepared['infrastructure_sha256']
        report['preparation_sha256'] = sha(stage / 'preparation.json')
        verifier, toolchain = bind_tools(stage, out)
        report['toolchain'] = toolchain
        rows = default_cases(policy)
        data = '\n'.join(x for x, _ in rows) + '\n'
        answers = [y for _, y in rows]
        for name in prepared['variants']:
            directory = out / name
            directory.mkdir()
            root = stage / name
            for file in (root / 'native').rglob('*.rs'):
                if re.search(r'\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)', file.read_text()):
                    raise RuntimeError('Unapproved proof escape: ' + str(file))
            lib, vir = directory / ('lib' + name + '.rlib'), directory / (name + '.vir')
            count = verified([verifier, root / 'native/lib.rs', '--crate-name', name,
                '--crate-type', 'lib', '--export', vir, '--compile', '-O', '-o', lib],
                directory / 'library.log', root)
            if count <= 0:
                raise RuntimeError('No positive library proof items: ' + name)
            report['libraries'][name] = {'verified_items': count, 'rlib': sha(lib), 'vir': sha(vir)}
            runner = directory / 'default-runner'
            verified([verifier, stage / 'default_runner.rs', '--import', 'experiment=' + str(vir),
                '--extern', 'experiment=' + str(lib), '--compile', '-O', '-o', runner],
                directory / 'runner-build.log', root)
            runner_hash = sha(runner)
            result = checked([runner], directory / 'default-oracle.log', root, input=data)
            if result.stdout.splitlines() != answers:
                raise RuntimeError('Default integer oracle mismatch: ' + name)
            if sha(runner) != runner_hash:
                raise RuntimeError('Default runner changed during execution: ' + name)
            report['default_oracles'][name] = {'cases': len(rows), 'runner_sha256': runner_hash,
                'coverage': 'Actual arithmetic entries, top=1..64 on registered boundary/principal sizes, full-u64 edge/random operands, read-only alias, exact 12n/10n scratch and output/scratch canaries'}
            write(out / 'build.json', report)
        check_prepared(stage)
        check_hashes(report['infrastructure_sha256'], stage)
        check_hashes(toolchain['sha256'])
        for name, library in report['libraries'].items():
            check_hashes({str(out / name / ('lib' + name + '.rlib')): library['rlib'],
                str(out / name / (name + '.vir')): library['vir']})
        if sha(stage / 'preparation.json') != report['preparation_sha256']:
            raise RuntimeError('Preparation manifest changed')
        report.update(status='pass', finished_utc=now())
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}', finished_utc=now())
    write(out / 'build.json', report)
    print(json.dumps({key: report[key] for key in ['status', 'error', 'libraries', 'default_oracles'] if key in report}, indent=2))
    return report['status'] == 'pass'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    raise SystemExit(not build(args.stage.resolve()))

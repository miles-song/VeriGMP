"""Hosted correctness/codegen execution; deliberately never execute a timing driver."""
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
import tarfile
import traceback
from common import check_hashes, check_prepared, now, sha, write

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKFLOW = '.github/workflows/toom4-composition-proof.yml'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True).strip()


def command(args, log):
    # Redirect directly so an interrupted job retains partial subprocess output.
    with log.open('w') as stream:
        result = subprocess.run(list(map(str, args)), cwd=REPO, stdout=stream,
            stderr=subprocess.STDOUT, timeout=3 * 60 * 60)
    if result.returncode:
        raise RuntimeError('Command failed; inspect ' + str(log))


def checkout_identity():
    commit = git('rev-parse', 'HEAD')
    if os.environ.get('GITHUB_SHA', commit) != commit:
        raise RuntimeError('Checkout is not the exact triggering commit')
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('CI requires a clean checkout')
    paths = [WORKFLOW, 'native/toolchain.json', 'scripts/setup_verus.py', '.gitattributes']
    directories = ['experiments/toom4-composition'] + [
        'experiments/' + name + '/overlay/candidate' for name in
        ['toom4-entry', 'odd-division', 'toom4-fusion', 'toom4-signed-eval']]
    paths += git('ls-files', '--', *directories).splitlines()
    return {'commit': commit, 'tree': git('rev-parse', 'HEAD^{tree}'),
        'sha256': {p: sha(REPO / p) for p in sorted(set(paths))}}


def archive_inputs(output, checkout, prepared):
    stage = output / 'stage'
    inputs = {name + '/' + p: digest for name, files in prepared['variants'].items()
        for p, digest in files.items()}
    inputs.update(prepared['infrastructure_sha256'])
    inputs['preparation.json'] = sha(stage / 'preparation.json')
    with tarfile.open(output / 'inputs.tar.gz', 'w:gz') as archive:
        for path in sorted(inputs):
            archive.add(stage / path, arcname='stage/' + path, recursive=False)
        for path in checkout['sha256']:
            archive.add(REPO / path, arcname='checkout/' + path, recursive=False)
    check_hashes(inputs, stage)
    check_hashes(checkout['sha256'], REPO)
    return inputs


def prepare(output):
    output.mkdir(parents=True)
    report = {'status': 'preparing', 'started_utc': now(),
        'scope': 'Hosted correctness and linked codegen only; no performance execution or candidate acceptance',
        'timing_executed': False, 'selection_executed': False,
        'semantic_mutants_executed': False, 'promotion_allowed': False}
    write(output / 'ci.json', report)
    try:
        report['checkout'] = checkout_identity()
        command([sys.executable, HERE / 'prepare.py', '--output', output / 'stage'], output / 'prepare.log')
        prepared = check_prepared(output / 'stage')
        report['inputs_sha256'] = archive_inputs(output, report['checkout'], prepared)
        report['input_archive_sha256'] = sha(output / 'inputs.tar.gz')
        report['preparation_sha256'] = sha(output / 'stage/preparation.json')
        report.update(status='prepared_not_executed', prepared_utc=now())
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        write(output / 'ci.json', report)


def validate_results(stage):
    prepared = check_prepared(stage)
    policy = json.loads((stage / 'policy.json').read_text())
    build = json.loads((stage / 'build-evidence/build.json').read_text())
    directory = stage / 'exploration-build'
    binding = json.loads((directory / 'binding.json').read_text())
    audit = json.loads((directory / 'codegen-audit.json').read_text())
    names = policy['modes'][:-1]
    if (build['status'] != 'pass' or build['benchmark_run'] or
            set(build['libraries']) != set(names) or set(build['default_oracles']) != set(names) or
            build['source_sha256'] != prepared['variants'] or
            build['infrastructure_sha256'] != prepared['infrastructure_sha256'] or
            build['preparation_sha256'] != sha(stage / 'preparation.json')):
        raise RuntimeError('Incomplete or stale full-library/default-oracle gate')
    pairs = {}
    for name in names:
        library = build['libraries'][name]
        oracle = build['default_oracles'][name]
        if library['verified_items'] <= 0 or oracle['cases'] <= 0:
            raise RuntimeError('Empty proof or oracle: ' + name)
        pairs[str(stage / 'build-evidence' / name / ('lib' + name + '.rlib'))] = library['rlib']
        pairs[str(stage / 'build-evidence' / name / (name + '.vir'))] = library['vir']
        check_hashes({str(stage / 'build-evidence' / name / 'default-runner'): oracle['runner_sha256']})
    if (binding['status'] != 'pass' or binding['phase'] != 'exploration' or
            binding['modes'] != policy['modes'] or binding['paired_library_sha256'] != pairs or
            binding['source_manifest_sha256'] != sha(stage / 'preparation.json') or
            binding['build_gate_sha256'] != sha(stage / 'build-evidence/build.json') or
            binding['toolchain'] != build['toolchain'] or
            binding['policy_sha256'] != prepared['policy_sha256'] or
            binding['source_sha256'] != sha(directory / 'compare.rs') or
            binding['binary_sha256'] != sha(directory / 'compare') or
            audit['status'] != 'inspection_complete' or audit['phase'] != 'exploration' or
            audit['binary_sha256'] != binding['binary_sha256'] or
            audit['binding_sha256'] != sha(directory / 'binding.json') or
            audit['script_sha256'] != sha(stage / 'audit_codegen.py')):
        raise RuntimeError('Incomplete or stale linked-codegen binding')
    for name in names:
        for entry in ['mul_mod', 'square_mod']:
            if name + '::arithmetic::' + entry not in audit['actual_default_entries']:
                raise RuntimeError('Missing compiled production entry: ' + name + '::' + entry)
    check_hashes(pairs | build['toolchain']['sha256'] | binding['runtime_sha256'])
    check_hashes(audit['artifacts'], directory)
    check_hashes({path: item['sha256'] for path, item in audit['tools'].items()})
    return {str(path.relative_to(stage)): sha(path) for path in
        [stage / 'build-evidence/build.json', directory / 'binding.json', directory / 'codegen-audit.json']}


def run(output):
    report = json.loads((output / 'ci.json').read_text())
    if report['status'] != 'prepared_not_executed':
        raise RuntimeError('Refusing to rerun an existing attempt')
    report.update(status='running', execution_started_utc=now())
    write(output / 'ci.json', report)
    try:
        if platform.system() != 'Linux' or platform.machine() != 'x86_64':
            raise RuntimeError('Hosted execution requires x86_64 Linux')
        if checkout_identity() != report['checkout']:
            raise RuntimeError('Checkout changed since preparation')
        stage = output / 'stage'
        check_hashes(report['inputs_sha256'], stage)
        if sha(output / 'inputs.tar.gz') != report['input_archive_sha256']:
            raise RuntimeError('Input archive changed')
        if (REPO / 'native/toolchain.json').read_bytes() != (stage / 'baseline/native/toolchain.json').read_bytes():
            raise RuntimeError('Bootstrap pin differs from the prepared baseline')
        pin = json.loads((REPO / 'native/toolchain.json').read_text())
        check_hashes({str(REPO / 'deps/verus-download' / pin['archive']): pin['sha256']})
        fields = ['GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_REF', 'GITHUB_EVENT_NAME',
            'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKFLOW_SHA',
            'RUNNER_OS', 'RUNNER_ARCH', 'RUNNER_NAME', 'RUNNER_ENVIRONMENT', 'ImageOS', 'ImageVersion']
        report['runner'] = {'platform': platform.platform(), 'uname': list(platform.uname()),
            'python': sys.version, 'python_executable': str(Path(sys.executable).resolve()),
            'environment': {key: os.environ[key] for key in fields if key in os.environ}}
        command(['uname', '-a'], output / 'uname.log')
        command(['lscpu'], output / 'cpu.log')
        command(['dpkg-query', '-W', 'g++', 'libgmp-dev', 'libgmp10', 'binutils'], output / 'packages.log')
        command([sys.executable, stage / 'build.py'], output / 'build-launch.log')
        command([sys.executable, stage / 'bench_build.py', 'exploration'], output / 'comparison-build-launch.log')
        command([sys.executable, stage / 'audit_codegen.py', 'exploration'], output / 'codegen-launch.log')
        report['result_sha256'] = validate_results(stage)
        check_hashes(report['inputs_sha256'], stage)
        if checkout_identity() != report['checkout']:
            raise RuntimeError('Checkout changed during execution')
        if sha(output / 'inputs.tar.gz') != report['input_archive_sha256']:
            raise RuntimeError('Input archive changed during execution')
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}')
        (output / 'ci-error.log').write_text(traceback.format_exc())
    finally:
        report['finished_utc'] = now()
        write(output / 'ci.json', report)
        write(output / 'artifact-inventory.json', {str(p.relative_to(output)): sha(p)
            for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'artifact-inventory.json'})
    print(json.dumps({'status': report['status'], 'scope': report['scope'],
        'timing_executed': report['timing_executed']}, indent=2))
    return report['status'] == 'pass'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'run'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.phase == 'prepare':
        prepare(args.output.resolve())
    else:
        raise SystemExit(not run(args.output.resolve()))

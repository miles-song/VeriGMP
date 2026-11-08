#!/usr/bin/env python3
"""Build and functionally check the independent screen; never runs timing."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/combination-20261108'))
from common import file_sha, manifest, write_json
from inspect_measurement import inspect
from measure_screen import expected_shapes
from measure_window import benchmark_environment, linked_paths, loader_probe, runtime_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof, out = args.proof.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use a fresh persistent evidence directory outside the checkout')
    out.mkdir(parents=True)
    report = {'status': 'running', 'benchmark_run': False, 'commands': []}
    target = out / 'preparation.json'
    write_json(target, report)
    try:
        proof_file = proof / 'verification.json'
        data = json.loads(proof_file.read_text())
        report['proof_report_sha256'] = file_sha(proof_file)
        if data['status'] != 'full_library_pass' or manifest(ROOT) != data['native_sha256']:
            raise RuntimeError('workspace does not match complete proof')
        if manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('proof snapshot differs')
        for name, digest in data['exports_sha256'].items():
            if file_sha(proof / name) != digest:
                raise RuntimeError('proof export changed: ' + name)
        verifier = Path(data['commands'][0]['argv'][0])
        rustc = Path(data['tools']['rustc_path'])
        if file_sha(rustc) != data['tools']['rustc_sha256']:
            raise RuntimeError('compiler differs from proof')
        for name, digest in data['tools']['sha256'].items():
            if file_sha(verifier.parent / name) != digest:
                raise RuntimeError('verifier dependency changed: ' + name)
        files = [Path(__file__).resolve(), ROOT / 'experiments/toom4-scoped/screen.rs',
                 ROOT / 'experiments/toom4-scoped/screen-protocol.json',
                 ROOT / 'experiments/toom4-scoped/measure_screen.py',
                 ROOT / 'experiments/toom4-scoped/measure_window.py',
                 ROOT / 'experiments/toom4-scoped/inspect_measurement.py',
                 ROOT / 'experiments/combination-20261108/common.py',
                 *[ROOT / 'experiments/packed-convolution' / name for name in
                   ('layout_verify.py', 'layout_mutations.py', 'layout_oracle.py', 'verus_logs.py')]]
        report['source_sha256'] = {str(path.relative_to(ROOT)): file_sha(path) for path in files}
        env = dict(data['tools']['environment'], LANG='C', LC_ALL='C', TZ='UTC',
                   PYTHONDONTWRITEBYTECODE='1', RAYON_NUM_THREADS='1', OMP_NUM_THREADS='1')
        bench_env = benchmark_environment()
        report['build_environment'] = env
        report['benchmark_environment'] = bench_env

        def run(name, argv, selected_env=env):
            result = subprocess.run(list(map(str, argv)), cwd=ROOT, env=selected_env, capture_output=True, timeout=300)
            (out / (name + '.stdout.log')).write_bytes(result.stdout)
            (out / (name + '.stderr.log')).write_bytes(result.stderr)
            report['commands'].append({'name': name, 'argv': list(map(str, argv)), 'returncode': result.returncode})
            if result.returncode:
                raise RuntimeError(name + ' failed')
            return result.stdout.decode()

        rustc_linked, rustc_ldd = linked_paths(rustc, env)
        (out / 'rustc.ldd.log').write_text(rustc_ldd)
        proof_linked = data['tools']['rustc_linked_sha256']
        if {p: digest for p, digest in rustc_linked.items() if not Path(p).name.startswith('ld-linux')} != proof_linked:
            raise RuntimeError('rustc dynamically resolved libraries differ from proof')
        cc = Path('/usr/bin/cc').resolve(strict=True)
        collect2 = Path(run('collect2-path', [cc, '-print-prog-name=collect2']).strip()).resolve(strict=True)
        linker = Path(shutil.which('ld.bfd', path=env['PATH'])).resolve(strict=True)
        gcc_linker = Path(run('gcc-linker-path', [cc, '-print-prog-name=ld']).strip()).resolve(strict=True)
        if linker != gcc_linker:
            raise RuntimeError('GCC and fixed BFD linker resolve differently')
        cxx = Path('/usr/bin/c++').resolve(strict=True)
        tool_paths = [rustc, cc, collect2, linker, cxx, Path('/usr/bin/ldd').resolve()]
        tool_linked = {}
        for tool in (cc, collect2, linker, cxx):
            deps, output = linked_paths(tool, env)
            (out / (tool.name + '.ldd.log')).write_text(output)
            tool_linked.update(deps)
        tool_linked.update(rustc_linked)
        report['tool_linked_sha256'] = tool_linked
        report['linker_paths'] = {'cc': str(cc), 'collect2': str(collect2), 'ld_bfd': str(linker)}
        run('cc-link-plan', [cc, '-###', '-fuse-ld=bfd', '-x', 'c', '/dev/null', '-o', '/dev/null'])

        binary = out / 'measure'
        run('build', [rustc, '--edition=2021', '--crate-name', 'measure',
                      ROOT / 'experiments/toom4-scoped/screen.rs', '-O',
                      '-C', 'codegen-units=1', '-C', 'linker=/usr/bin/cc', '-C', 'link-arg=-fuse-ld=bfd',
                      '--extern', 'verigmp=' + str(proof / 'libverigmp.rlib'),
                      '-L', 'dependency=' + str(verifier.parent), '-o', binary])
        abi = out / 'gmp-abi'
        run('gmp-abi-build', [cxx, '-fuse-ld=bfd', '-std=c++17', ROOT / 'native/controls/gmp_abi.cpp', '-lgmp', '-o', abi])
        report['gmp_abi'] = run('gmp-abi', [abi], bench_env).strip()
        report['self_test'] = run('self-test', [binary, '--self-test'], bench_env).strip()
        report['controller_self_test'] = run('controller-self-test',
                                             ['/usr/bin/python3', '-B',
                                              ROOT / 'experiments/toom4-scoped/measure_screen.py', 'self-test'],
                                             bench_env).strip()
        shape_lines = run('shapes', [binary, '--list'], bench_env).splitlines()
        shapes = [tuple(map(int, line.split(','))) for line in shape_lines]
        if len(shapes) != len(set(shapes)) or set(shapes) != expected_shapes():
            raise RuntimeError('invalid shape list')
        report['shapes'] = shapes
        checks = run('all-inputs-gmp', [binary, '--check-inputs'], bench_env).splitlines()
        if len(checks) != 2 * len(shapes) or set(checks) != {
                f'{op},{n},{top},pass' for n, top in shapes for op in range(2)}:
            raise RuntimeError('actual timing input GMP checks incomplete')
        report['actual_timing_inputs_checked'] = len(checks)
        report['runtime_sha256'], linked = runtime_identity(binary, bench_env)
        (out / 'measure.ldd.log').write_text(linked)
        report['loader_probe_metadata'] = loader_probe(binary, bench_env, report['runtime_sha256'], out)
        report['loader_probe_negative_cases'] = ['hash', 'paths', 'environment', 'metadata']
        for label, artifact in (('binary', binary), ('rlib', proof / 'libverigmp.rlib')):
            run('nm-' + label, ['/usr/bin/nm', '-C', '-S', '--defined-only', artifact], bench_env)
            run('objdump-' + label, ['/usr/bin/objdump', '-d', '-C', artifact], bench_env)
        run('relocations-binary', ['/usr/bin/readelf', '-Wr', binary], bench_env)
        inspection = inspect(*[(out / (name + '.stdout.log')).read_text() for name in
                               ('nm-binary', 'nm-rlib', 'objdump-binary', 'relocations-binary')])
        write_json(out / 'codegen-observation.json', inspection)
        report['codegen_observation_sha256'] = file_sha(out / 'codegen-observation.json')
        report['identity_sha256'] = dict(report['runtime_sha256'], **tool_linked)
        report['identity_sha256'].update({str(p): file_sha(p) for p in [abi, *tool_paths,
                                                                        Path('/usr/bin/nm').resolve(),
                                                                        Path('/usr/bin/objdump').resolve(),
                                                                        Path('/usr/bin/readelf').resolve()]})
        report['native_manifest_sha256'] = data['native_manifest_sha256']
        report['proof_exports_sha256'] = data['exports_sha256']
        if manifest(ROOT) != data['native_sha256'] or manifest(proof / 'snapshot') != data['native_sha256']:
            raise RuntimeError('native source changed during preparation')
        if file_sha(proof_file) != report['proof_report_sha256']:
            raise RuntimeError('proof report changed during preparation')
        if any(file_sha(ROOT / name) != digest for name, digest in report['source_sha256'].items()):
            raise RuntimeError('measurement source changed during preparation')
        if any(file_sha(path) != digest for path, digest in report['identity_sha256'].items()):
            raise RuntimeError('binary, compiler or runtime changed during preparation')
        if runtime_identity(binary, bench_env)[0] != report['runtime_sha256']:
            raise RuntimeError('runtime resolution changed during preparation')
        if linked_paths(rustc, env)[0] != rustc_linked:
            raise RuntimeError('rustc resolution changed during preparation')
        if any(file_sha(proof / name) != digest for name, digest in data['exports_sha256'].items()):
            raise RuntimeError('proof export changed during preparation')
        report['evidence_sha256'] = {path.name: file_sha(path) for path in sorted(out.iterdir())
                                     if path.is_file() and path != target}
        report['status'] = 'prepared_no_timing'
        write_json(target, report)
        print(json.dumps({'status': report['status'], 'shapes': len(shapes), 'self_test': report['self_test']}, indent=2))
    except BaseException as error:
        report.update(status='fail', failure=repr(error))
        write_json(target, report)
        raise


if __name__ == '__main__':
    main()

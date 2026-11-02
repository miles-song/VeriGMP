"""Selected-source correctness, semantic mutants and standalone optimized codegen."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from common import check_hashes, check_prepared, checked, now, sha, strict_mutant, verified, write


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accept(stage, archive):
    out = stage / 'acceptance'
    out.mkdir()
    selection = json.loads((stage / 'selection.json').read_text())
    selected = selection['selected']
    root = stage / selected
    report = {'status': 'running', 'started_utc': now(), 'selected': selected, 'mutations': []}
    write(out / 'verification.json', report)
    try:
        check_prepared(stage)
        build = json.loads((stage / 'build-evidence/build.json').read_text())
        if build['status'] != 'pass':
            raise RuntimeError('Library gate did not pass')
        check_hashes(build['toolchain']['sha256'])
        verifier = Path(__import__('os').environ['VERUS_BIN']).resolve()
        lib = stage / 'build-evidence' / selected / ('lib' + selected + '.rlib')
        vir = stage / 'build-evidence' / selected / (selected + '.vir')
        check_hashes({str(lib): build['libraries'][selected]['rlib'], str(vir): build['libraries'][selected]['vir']})
        report['paired_library'] = build['libraries'][selected]
        report['library_source_sha256'] = json.loads((stage / 'preparation.json').read_text())['variants'][selected]
        report['gate_input_sha256'] = {p.name: sha(p) for p in archive.iterdir() if p.is_file()}
        runner_source = (root / 'native/toom4_runner.rs').read_text()
        runner_source = '\n'.join(line for line in runner_source.splitlines() if not line.startswith('#[path='))
        runner_source = 'extern crate experiment;\nuse experiment::*;\n' + runner_source
        (out / 'runner.rs').write_text(runner_source)
        report['runner_verified_items'] = verified([verifier, out / 'runner.rs', '--import', 'experiment=' + str(vir),
            '--extern', 'experiment=' + str(lib), '--compile', '-O', '-o', out / 'runner'], out / 'runner-build.log', root)
        sys.path.insert(0, str(root / 'scripts'))
        base = load(root / 'scripts/verify_toom.py', 'base_oracle')
        modules = {name: load(archive / (name + '.py'), name) for name in ['oracle', 'odd_oracle', 'fusion_oracle', 'signed_oracle']}
        suites = [('existing', base.cases())] + [(name, module.cases()) for name, module in modules.items()]
        report['oracles'] = {}
        for name, rows in suites:
            data = '\n'.join(command for command, _ in rows) + '\n'
            result = checked([out / 'runner'], out / (name + '-oracle.log'), root, input=data)
            if result.stdout.splitlines() != [answer for _, answer in rows]:
                raise RuntimeError('Independent integer oracle mismatch: ' + name)
            report['oracles'][name] = {'cases': len(rows),
                'input_sha256': hashlib.sha256(data.encode()).hexdigest(),
                'output_sha256': hashlib.sha256(result.stdout.encode()).hexdigest()}
        invalid = ['full4 64 23 24 0 1 1', 'squarefull4 64 23 24 0 1 1',
            'candidate4 0 256 128 2 1 1', 'candidate4square 65 256 128 2 1 1',
            'shortscratch4 64 24 24 0 1 1', 'weighted4 8 8 0 0 1 1 1 2 3 4',
            'signed4 2 1 1 1 2 3 4', 'full4 64 24 24 0 1 1 1']
        invalid += [command for name in ['odd_oracle', 'fusion_oracle', 'signed_oracle'] for command in modules[name].invalid()]
        for index, command in enumerate(invalid):
            result = subprocess.run([out / 'runner'], input=command + '\n', text=True, capture_output=True, cwd=root, timeout=30)
            (out / f'invalid-{index}.log').write_text(result.stdout + result.stderr)
            if not result.returncode or result.stdout.strip():
                raise RuntimeError('Invalid harness command accepted')
        report['invalid_harness_commands_rejected'] = len(invalid)
        report['mutations_not_applicable'] = []
        mutations = json.loads((archive / 'mutations.json').read_text())
        for file, name, before, after, module in mutations:
            source = root / 'native/verified' / file
            original = source.read_bytes()
            text = original.decode().replace('\r\n', '\n')
            if file == 'toom4_interpolate.rs':
                for var, divisor in [('pmh', 3), ('scratch', 9), ('ph', 15)]:
                    old = f'divide_exact({var},{divisor})'
                    if f'divide_exact_odd({var},{divisor})' in text:
                        before = before.replace(old, f'divide_exact_odd({var},{divisor})')
                        after = after.replace('divide_exact(', 'divide_exact_odd(')
            if text.count(before) != 1:
                report['mutations_not_applicable'].append({'name': name, 'reason': 'Archived transformation absent from selected source', 'matches': text.count(before)})
                continue
            try:
                source.write_text(text.replace(before, after))
                result = subprocess.run([verifier, root / 'native/lib.rs', '--crate-type', 'lib',
                    '--verify-module', module, '--multiple-errors', '0'], cwd=root, text=True, capture_output=True, timeout=300)
                (out / (name + '.log')).write_text(result.stdout + result.stderr)
                rejected = strict_mutant(result)
                report['mutations'].append({'name': name, 'module': module, 'semantic_vc_failure': rejected})
                write(out / 'verification.json', report)
                if not rejected:
                    raise RuntimeError('No actual semantic VC failure: ' + name)
            finally:
                source.write_bytes(original)
        asm = out / 'codegen.s'
        report['codegen_verified_items'] = verified([verifier, root / 'native/toom4_codegen.rs', '--compile', '-O',
            '--emit=asm', '-o', asm], out / 'codegen.log', root)
        assembly = asm.read_text()
        report['codegen'] = base.reachable_code(assembly)
        report['odd_codegen'] = load(archive / 'odd_codegen.py', 'odd_codegen').inspect_odd(assembly)
        report['fusion_codegen'] = load(archive / 'fusion_codegen.py', 'fusion_codegen').inspect_fusion(assembly)
        report['signed_codegen'] = load(archive / 'signed_codegen.py', 'signed_codegen').inspect_signed(assembly)
        for required in ['toom4_multiply', 'toom4_square']:
            if not any(required in symbol for symbol in report['codegen']['reachable_functions']):
                raise RuntimeError('Actual default does not reach ' + required)
        check_prepared(stage)
        check_hashes(build['toolchain']['sha256'])
        check_hashes(report['gate_input_sha256'], archive)
        report['artifact_sha256'] = {p.name: sha(p) for p in [out / 'runner', out / 'runner.rs', asm]}
        report.update(status='pass', finished_utc=now(), source_tool_artifact_checks_before_after=True)
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}', finished_utc=now())
    write(out / 'verification.json', report)
    print(json.dumps({key: report[key] for key in ['status', 'error', 'selected', 'oracles'] if key in report}, indent=2))
    return report['status'] == 'pass'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(not accept(args.stage.resolve(), args.archive.resolve()))

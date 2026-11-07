#!/usr/bin/env python3
"""Source-bound focused model proof, release compilation, oracle and mutants."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import time
import zipfile

from mutations import MUTATIONS
from oracle import check as check_oracle

ROOT = Path(__file__).resolve().parents[2]
FEATURE = 'experiments/packed-convolution'
MODEL = 'native/specs/packed_convolution.rs'
SOURCES = ['AGENTS.md', '.gitattributes', 'LICENSE', 'native/toolchain.json',
           'native/proof-status.json', 'native/lib.rs', 'native/specs/radix.rs',
           'native/specs/product.rs', MODEL, 'README.md', 'README.zh-CN.md',
           'docs/packed-convolution.md', *[f'{FEATURE}/{name}' for name in
           ('model.rs', 'codegen.rs', 'oracle.py', 'mutations.py', 'verify.py')]]
POSITIVE = re.compile(r'^verification results:: ([1-9][0-9]*) verified, 0 errors$', re.M)
NEGATIVE = re.compile(r'^verification results:: [0-9]+ verified, [1-9][0-9]* errors$', re.M)
FAULT = re.compile(r'(?i)resource limit|rlimit.*exceeded|timed out|panic|unexpected token|could not compile|solver.*unknown')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_adapter():
    command = ['git', '-C', str(ROOT)]
    pointer = (ROOT / '.git').read_text() if (ROOT / '.git').is_file() else ''
    match = re.fullmatch(r'gitdir: ([A-Za-z]):[/\\](.+)\s*', pointer.strip())
    if platform.system() == 'Linux' and match:
        windows_git = Path('/mnt/c/Program Files/Git/cmd/git.exe')
        mounted_root = re.fullmatch(r'/mnt/([a-z])/(.+)', str(ROOT))
        if windows_git.is_file() and mounted_root:
            windows_root = mounted_root[1].upper() + ':/' + mounted_root[2]
            return [str(windows_git), '-C', windows_root]
        gitdir = Path('/mnt') / match[1].lower() / match[2].replace('\\', '/')
        command += [f'--git-dir={gitdir}', f'--work-tree={ROOT}']
    return command


def git(*args):
    return subprocess.run(git_adapter() + list(args), check=True, capture_output=True, timeout=60).stdout


def identity(sources):
    top = git('rev-parse', '--show-toplevel').decode().strip()
    windows_top = re.fullmatch(r'([A-Za-z]):[/\\](.+)', top)
    if platform.system() == 'Linux' and windows_top:
        top = '/mnt/' + windows_top[1].lower() + '/' + windows_top[2].replace('\\', '/')
    if Path(top).resolve() != ROOT:
        raise RuntimeError('Git identity does not resolve to this actual worktree')
    if git('status', '--porcelain', '--untracked-files=all').strip():
        raise RuntimeError('Commit all feature inputs before acceptance')
    head = git('rev-parse', 'HEAD').decode().strip()
    for name, data in sources.items():
        if git('show', f'{head}:{name}') != data or (ROOT / name).read_bytes() != data:
            raise RuntimeError('HEAD/source mismatch: ' + name)
    return dict(head=head, branch=git('branch', '--show-current').decode().strip(),
                root=str(ROOT), git_command=git_adapter(),
                source_sha256={n: sha(d) for n, d in sources.items()})


def live_group(group):
    members = []
    for stat in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = stat.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == group and fields[0] != 'Z':
                members.append(int(stat.parent.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError('Use a fresh persistent evidence directory outside the checkout')
    output.mkdir(parents=True)
    report = dict(status='running', scope='universal packed convolution model',
                  runtime_refinement=False, bit_cost_proved=False, peak_space_proved=False,
                  benchmark_run=False, gmp_parity=False, commands=[], mutants=[])

    def save():
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    def run(command, name, cwd, env, timeout=150):
        command = list(map(str, command))
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        expired = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                stdout, stderr = proc.communicate(timeout=5)
        remaining = live_group(proc.pid)
        if remaining:
            os.killpg(proc.pid, signal.SIGKILL)
            for _ in range(20):
                time.sleep(0.1)
                remaining = live_group(proc.pid)
                if not remaining:
                    break
        (output / (name + '.stdout.log')).write_bytes(stdout)
        (output / (name + '.stderr.log')).write_bytes(stderr)
        report['commands'].append(dict(command=command, cwd=str(cwd), returncode=proc.returncode,
            timeout=expired, owned_live_children=remaining, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)))
        save()
        if expired or remaining:
            raise RuntimeError('Timeout or owned child quiescence failure: ' + name)
        return proc.returncode, (stdout + stderr).decode(errors='replace')

    def positive(result):
        code, log = result
        matches = POSITIVE.findall(log)
        if code or len(matches) != 1 or 'error:' in log or FAULT.search(log):
            raise RuntimeError('No complete positive verification summary')
        return int(matches[0])

    save()
    try:
        if platform.system() != 'Linux' or platform.machine() != 'x86_64':
            raise RuntimeError('Pinned model verification requires x86_64 Linux/WSL')
        sources = {name: (ROOT / name).read_bytes() for name in SOURCES}
        source_identity = identity(sources)
        report['source_git'] = source_identity
        forbidden = r'\b(?:assume|admit|axiom)\s*\(|external_body|external_fn_specification|verifier::trusted|verify\s*=\s*false|\bunsafe\b|extern\s+"C"'
        for name in (MODEL, f'{FEATURE}/model.rs'):
            if re.search(forbidden, sources[name].decode()):
                raise RuntimeError('Unapproved proof escape/core FFI: ' + name)
        for name, (before, _) in MUTATIONS.items():
            if sources[MODEL].decode().count(before) != 1:
                raise RuntimeError('Mutation anchor is not unique: ' + name)
        assert '#[path="specs/packed_convolution.rs"] pub mod packed_convolution;' in sources['native/lib.rs'].decode()
        status = json.loads(sources['native/proof-status.json'])
        entry = [m for m in status['modules'] if m['files'] == ['specs/packed_convolution.rs']]
        assert len(entry) == 1 and entry[0]['status'] == 'model_proved'
        assert 'model_proved' in sources['docs/packed-convolution.md'].decode()
        for name in ('README.md', 'README.zh-CN.md'):
            assert 'docs/packed-convolution.md' in sources[name].decode()
        report['documentation_check'] = 'pass'
        snapshot = output / 'source'
        for name, data in sources.items():
            path = snapshot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        pin = json.loads(sources['native/toolchain.json'])
        deps = args.deps_root.resolve()
        archive = deps / 'verus-download' / pin['archive']
        if file_sha(archive) != pin['sha256']:
            raise RuntimeError('Pinned verifier archive SHA-256 mismatch')
        verifier = deps / 'verus/verus-x86-linux/verus'
        tool_names = ['verus', 'rust_verify', 'z3', 'vstd.vir', 'libvstd.rlib',
                      'libverus_builtin.rlib', 'libverus_builtin_macros.so', 'libverus_state_machines_macros.so']
        tools = {}
        with zipfile.ZipFile(archive) as bundle:
            for name in tool_names:
                installed = verifier.parent / name
                actual = file_sha(installed)
                with bundle.open('verus-x86-linux/' + name) as stream:
                    expected = hashlib.file_digest(stream, 'sha256').hexdigest()
                if actual != expected:
                    raise RuntimeError('Installed verifier file differs from pinned archive: ' + name)
                tools[str(installed)] = actual
        env = dict(os.environ, CARGO_HOME=str(deps / 'cargo'), RUSTUP_HOME=str(deps / 'rustup'),
                   RUSTUP_TOOLCHAIN=pin['rust_toolchain'])
        env['PATH'] = str(deps / 'cargo/bin') + os.pathsep + env['PATH']
        code, version = run([verifier, '--version'], 'verus-version', snapshot, env)
        if code or pin['verus_version'] not in version or pin['rust_toolchain'] not in version:
            raise RuntimeError('Verifier/Rust version mismatch')
        rustup = deps / 'cargo/bin/rustup'
        code, rust_version = run([rustup, 'run', pin['rust_toolchain'], 'rustc', '-vV'], 'rustc-version', snapshot, env)
        if code or 'release: 1.99.1' not in rust_version or 'host: x86_64-unknown-linux-gnu' not in rust_version:
            raise RuntimeError('Compiler version mismatch')
        report['toolchain'] = dict(verus_version=version, rustc_version=rust_version,
                                  archive_sha256=file_sha(archive), actual_file_sha256=tools)
        library, metadata = output / 'libpacked_model.rlib', output / 'packed_model.vir'
        command = [verifier, f'{FEATURE}/model.rs', '--crate-type', 'lib', '--crate-name', 'packed_model',
                   '--no-cheating', '--rlimit', '10', '--num-threads', '4']
        report['model_verified_items'] = positive(run(command + ['--compile', '-O', '--export', metadata,
            '-o', library], 'model-proof-release', snapshot, env))
        report['exports_sha256'] = {str(path): file_sha(path) for path in (library, metadata)}
        report['oracle'] = check_oracle(output)
        report['oracle_fixture_verified_items'] = positive(run([verifier, output / 'oracle-fixtures.rs',
            '--crate-type', 'lib', '--import', f'packed_model={metadata}', '--extern', f'packed_model={library}',
            '--no-cheating', '--rlimit', '10', '--num-threads', '4'], 'oracle-model-import', snapshot, env))
        client = output / 'erasure-client.o'
        report['erasure_client_verified_items'] = positive(run([verifier, f'{FEATURE}/codegen.rs',
            '--import', f'packed_model={metadata}', '--extern', f'packed_model={library}',
            '--crate-type', 'lib', '--no-cheating', '--compile', '-O', '--emit=obj',
            '-o', client], 'erasure-client-build', snapshot, env))
        code, symbols = run(['nm', '-S', '--defined-only', client], 'proof-erasure-symbols', snapshot, env)
        if code:
            raise RuntimeError('Could not inspect erasure client')
        bodies = []
        disassemblies = []
        for name in ('packed_model_identity', 'ordinary_identity'):
            match = re.search(r'^([0-9a-f]+) ([0-9a-f]+) [Tt] ' + name + r'$', symbols, re.M)
            if not match:
                raise RuntimeError('Missing erasure client symbol: ' + name)
            code, assembly = run(['objdump', '-d', f'--disassemble={name}', client],
                'erasure-' + name, snapshot, env)
            section_names = re.findall(r'^Disassembly of section ([^:]+):$', assembly, re.M)
            symbol_names = re.findall(r'^\s*[0-9a-f]+ <([^>]+)>:$', assembly, re.M)
            instructions = re.findall(r'^\s*[0-9a-f]+:\s+(?:[0-9a-f]{2}\s+)+(.+)$', assembly, re.M)
            if (code or section_names != [f'.text.{name}'] or symbol_names != [name]
                    or not instructions or any(i.split()[0] not in ('mov', 'ret') for i in instructions)):
                raise RuntimeError('Symbol-targeted disassembly was not exact or retained unexpected work: ' + name)
            bodies.append(instructions)
            disassemblies.append(dict(symbol=name, section=section_names[0], labels=symbol_names,
                                      instructions=len(instructions)))
        if bodies[0] != bodies[1]:
            raise RuntimeError('Proof client differs from the ordinary identity control')
        report['erasure_disassemblies'] = disassemblies
        report['erasure_check'] = 'proof-bearing identity has the same mov/ret body as its ordinary control'
        for name, (before, after) in MUTATIONS.items():
            original = sources[MODEL].decode()
            if original.count(before) != 1:
                raise RuntimeError('Mutation anchor is not unique: ' + name)
            mutated = original.replace(before, after).encode()
            directory = output / 'mutants' / name
            for source in (MODEL, 'native/specs/radix.rs', 'native/specs/product.rs', f'{FEATURE}/model.rs'):
                path = directory / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(mutated if source == MODEL else sources[source])
            code, log = run(command, 'mutant-' + name, directory, env)
            rejected = (code != 0 and bool(NEGATIVE.search(log)) and not FAULT.search(log)
                        and bool(re.search(r'error: (postcondition not satisfied|assertion failed|precondition not satisfied|requires not satisfied)', log)))
            report['mutants'].append(dict(name=name, source_sha256=sha(mutated), rejected_by_logic=rejected))
            save()
            if not rejected:
                raise RuntimeError('Mutation was not rejected by a semantic VC: ' + name)
        if identity(sources) != source_identity or any(file_sha(path) != digest for path, digest in tools.items()):
            raise RuntimeError('Source or verifier changed during acceptance')
        report['artifact_sha256'] = {str(p.relative_to(output)): file_sha(p) for p in output.rglob('*')
                                    if p.is_file() and p.name != 'verification.json'}
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}')
    save()
    print(json.dumps({k: report[k] for k in ('status', 'error', 'model_verified_items', 'oracle', 'mutants') if k in report}, indent=2))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Forced/helper integer oracles and semantic mutants, without candidate selection."""
from pathlib import Path
import argparse
import ctypes
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from common import check_hashes, check_prepared, now, sha, strict_mutant, write

ORACLES = ['oracle', 'odd_oracle', 'fusion_oracle', 'signed_oracle']
WALL_BUDGET_SECONDS = 120 * 60
FUSED_CALL_MUTANTS = {'fusion_wrong_half_constant', 'fusion_wrong_quadratic_constant',
    'fusion_wrong_quartic_constant', 'fusion_wrong_sixth_constant'}
EXISTING_INVALID = ['default 0 192 128 2 1 2', 'default 65 192 128 2 1 2',
    'square 4294967297 192 128 2 1 2', 'full 64 23 24 0 1 2',
    'low 64 24 23 0 1 2', 'low 64 24 24 3 1 2', 'squarek 64 7 24 0 1 2',
    'shortscratch 64 192 128 2 1 2', 'divide 0 1', 'row 1 2 1 1 2 3',
    'squarebase', 'squarebaselow']
TOOM4_INVALID = ['full4 64 23 24 0 1 1', 'squarefull4 64 23 24 0 1 1',
    'candidate4 0 256 128 2 1 1', 'candidate4square 65 256 128 2 1 1',
    'shortscratch4 64 24 24 0 1 1', 'weighted4 8 8 0 0 1 1 1 2 3 4',
    'signed4 2 1 1 1 2 3 4', 'full4 64 24 24 0 1 1 1']
INVALID_SITES = {
    'existing_invalid': ['arithmetic_parameters'] * 7 + ['scratch_capacity', 'divide_domain',
        'row_shape', 'base_square_shape', 'base_square_shape'],
    'toom4_invalid': ['arithmetic_parameters'] * 4 + ['scratch_capacity', 'evaluation_weights',
        'evaluation_weights', 'arithmetic_shape'],
    'odd_oracle_invalid': ['odd_limb_domain'] * 4 + ['odd_limb_shape', 'odd_divisor',
        'exact_divisor', 'exact_multiple', 'exact_multiple', 'exact_multiple',
        'exact_divisor', 'exact_multiple', 'exact_multiple', 'exact_shape'],
    'fusion_oracle_invalid': ['subscaled_shape'] * 3 + ['subscaled_domain'] * 2 + ['subscaled_shape'] * 3,
    'signed_oracle_invalid': ['signed_limb_domain', 'signed_limb_domain', 'signed_limb_shape',
        'evaluation_weights'] + ['evaluation_shape'] * 4,
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def linked_runner(source):
    text = source.decode('utf-8').replace('\r\n', '\n')
    for entry in ['mul_mod', 'square_mod']:
        before = 'toom4_candidate::' + entry + '('
        if text.count(before) != 1:
            raise RuntimeError('Unexpected archived runner entry: ' + before)
        text = text.replace(before, 'arithmetic::' + entry + '(')
    replacements = {
        'let op=fields.next().unwrap();let args:Vec<u64>=fields.map(|s|s.parse().unwrap()).collect();':
            'let op=fields.next().unwrap_or_else(||harness_reject("syntax"));\n'
            '        let args:Vec<u64>=fields.map(|s|s.parse().unwrap_or_else(|_|harness_reject("syntax"))).collect();\n'
            '        harness_validate(op,&args);',
        '"shortscratch4"=>toom4_multiply::full(dst,a,b,&mut work[..12*n-1],threshold),':
            '"shortscratch4"=>{harness_capacity(work[..12*n-1].len(),12*n);'
            'toom4_multiply::full(dst,a,b,&mut work[..12*n-1],threshold);},',
        '"shortscratch"=>arithmetic::mul_mod(dst,a,b,&mut work[..3*n],top),':
            '"shortscratch"=>{harness_capacity(work[..3*n].len(),12*n);'
            'arithmetic::mul_mod(dst,a,b,&mut work[..3*n],top);},',
    }
    for before, after in replacements.items():
        if text.count(before) != 1:
            raise RuntimeError('Unexpected archived harness validation site: ' + before)
        text = text.replace(before, after)
    text = '\n'.join(line for line in text.splitlines() if not line.startswith('#[path='))
    guard = Path(__file__).with_name('correctness_guard.rs').read_text(encoding='utf-8')
    return ('extern crate experiment;\nuse experiment::*;\n' + guard + '\n' + text + '\n').encode('utf-8')


def mutation_registry(root, features, mutations):
    rows = []
    for file, name, before, after, module in mutations:
        reason = None
        if file == 'toom4_candidate.rs':
            file, module = 'arithmetic.rs', 'arithmetic'
            if name == 'omit_small_square_normalization':
                before, after = '    pow2::normalize_top(dst,top);', ''
            elif name != 'wrong_small_product_operand':
                raise RuntimeError('Unregistered candidate adapter: ' + name)
        if name == 'odd_admit_even_divisor':
            reason = ('The pinned general toom_words API calls divide_word, with no archived '
                'API-to-odd-helper branch. Direct odd helpers and interpolation divisor mutants remain covered.')
        if name in FUSED_CALL_MUTANTS and 'fusion' not in features:
            reason = ('Declared unfused interpolation has no fused call at this site; '
                'direct scaled_subtraction helper mutants remain applicable.')
        if file == 'toom4_interpolate.rs' and 'odd' in features:
            for var, divisor in [('pmh', 3), ('scratch', 9), ('ph', 15)]:
                old = f'divide_exact({var},{divisor})'
                if old in before:
                    before = before.replace(old, f'divide_exact_odd({var},{divisor})')
                    after = after.replace('divide_exact(', 'divide_exact_odd(')
        path = root / 'native/verified' / file
        text = path.read_bytes().decode('utf-8').replace('\r\n', '\n')
        expected = 0 if reason else 1
        if text.count(before) != expected or before == after:
            raise RuntimeError(f'Mutant anchor mismatch: {root.name}/{name}: {text.count(before)} != {expected}')
        rows.append({'name': name, 'file': 'native/verified/' + file, 'module': module,
            'applicable': reason is None, 'reason': reason, 'expected_matches': expected,
            'before': before, 'after': after, 'source_sha256': sha(path)})
    return rows


def prepare_inputs(stage, policy, variants, archive):
    """Freeze commands, independent answers and the complete applicability table before execution."""
    out = stage / 'correctness-inputs'
    out.mkdir()
    archived = out / 'archive'
    archived.mkdir()
    archive_hashes = {}
    for name in [*(x + '.py' for x in ORACLES), 'mutations.json', 'overlay/candidate/native/toom4_runner.rs']:
        source = archive / name
        (archived / source.name).write_bytes(source.read_bytes())
        archive_hashes['experiments/toom4-signed-eval/' + name] = sha(source)
    (out / 'runner.rs').write_bytes(linked_runner((archived / 'toom4_runner.rs').read_bytes()))
    scripts = stage / 'entry/scripts'
    previous = {name: sys.modules.get(name) for name in ['verify_limbs', 'verify_multiply']}
    try:
        for name in previous:
            sys.modules[name] = load(scripts / (name + '.py'), 'composition_' + name)
        base = load(scripts / 'verify_toom.py', 'composition_existing_oracle')
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    modules = {name: load(archived / (name + '.py'), 'composition_' + name) for name in ORACLES}
    manifest = {'status': 'frozen_before_execution', 'runner_sha256': sha(out / 'runner.rs'),
        'archive_input_sha256': archive_hashes, 'suites': {}, 'mutation_registry': {}}

    def freeze(name, rows, kind):
        if not rows:
            raise RuntimeError('Empty correctness suite: ' + name)
        commands, answers = out / (name + '.commands'), out / (name + '.answers')
        commands.write_bytes(('\n'.join(command for command, _ in rows) + '\n').encode('utf-8'))
        answers.write_bytes(('\n'.join(answer for _, answer in rows) + '\n').encode('utf-8'))
        manifest['suites'][name] = {'kind': kind, 'cases': len(rows),
            'commands_sha256': sha(commands), 'answers_sha256': sha(answers)}

    def freeze_invalid(name, commands):
        sites = INVALID_SITES[name]
        if len(commands) != len(sites):
            raise RuntimeError('Invalid-command registry changed: ' + name)
        freeze(name, list(zip(commands, sites)), 'invalid')

    freeze('existing', base.cases(), 'integer_oracle')
    freeze_invalid('existing_invalid', EXISTING_INVALID)
    freeze_invalid('toom4_invalid', TOOM4_INVALID)
    for name, module in modules.items():
        freeze(name, module.cases(), 'integer_oracle')
        if hasattr(module, 'invalid'):
            freeze_invalid(name + '_invalid', module.invalid())
    mutations = json.loads((archived / 'mutations.json').read_text(encoding='utf-8'))
    if len(mutations) != 49 or len({row[1] for row in mutations}) != 49:
        raise RuntimeError('Unexpected archived mutation registry')
    for name in policy['modes'][1:-1]:
        manifest['mutation_registry'][name] = mutation_registry(stage / name, policy['features'][name], mutations)
        if any(row['source_sha256'] != variants[name][row['file']] for row in manifest['mutation_registry'][name]):
            raise RuntimeError('Mutation registry differs from prepared source: ' + name)
    write(out / 'manifest.json', manifest)
    return ({p.relative_to(stage).as_posix(): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}, archive_hashes)


class ProcessCleanupError(RuntimeError):
    """The owned tree may still be using its mutation source or raw streams."""


def _linux_proc_snapshot():
    """Return process parent/start-time records and a parent-to-children index."""
    records, children = {}, {}
    if not Path('/proc').is_dir():
        raise OSError('Linux /proc is unavailable for owned-process tracking')
    try:
        entries = Path('/proc').iterdir()
    except OSError:
        raise
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / 'stat').read_bytes().decode('ascii', errors='replace')
            tail = raw[raw.rfind(')') + 2:].split()
            if len(tail) <= 19:
                continue
            pid = int(entry.name)
            ppid, start = int(tail[1]), int(tail[19])
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as error:
            raise OSError(f'Cannot inventory Linux process entry {entry.name}') from error
        records[pid] = (ppid, start)
        children.setdefault(ppid, []).append(pid)
    return records, children


def _linux_direct_children():
    records, _ = _linux_proc_snapshot()
    owner = os.getpid()
    return {pid: start for pid, (ppid, start) in records.items() if ppid == owner}


def _linux_owned_processes(root_pid, root_start, owned, baseline):
    """Discover descendants by parent identity, including adopted session escapes."""
    records, children = _linux_proc_snapshot()
    owner = os.getpid()
    observed = {}
    queue = []

    def add(pid, start):
        if pid == owner or pid in observed:
            return
        observed[pid] = start
        queue.append(pid)

    root = records.get(root_pid)
    if root is not None and (root_start is None or root[1] == root_start):
        add(root_pid, root[1])
    for pid, expected in list(owned.items()):
        current = records.get(pid)
        if current is not None and (expected is None or current[1] == expected):
            add(pid, current[1])
    # A descendant that was reparented after its session leader exited is now
    # our direct child. Baseline children are unrelated processes owned before
    # this capture and must remain outside this tree.
    for pid in children.get(owner, []):
        current = records.get(pid)
        if current is None or (pid in baseline and baseline[pid] == current[1]):
            continue
        add(pid, current[1])
    while queue:
        parent = queue.pop()
        for child in children.get(parent, []):
            current = records.get(child)
            if current is not None:
                add(child, current[1])
    return observed, records


def _linux_kill_pid(pid, expected_start):
    pidfd_open = getattr(os, 'pidfd_open', None)
    pidfd_send_signal = getattr(signal, 'pidfd_send_signal', None)
    if pidfd_open is None or pidfd_send_signal is None:
        raise RuntimeError('pidfd signaling is required for escaped descendant cleanup')
    descriptor = pidfd_open(pid, 0)
    try:
        records, _ = _linux_proc_snapshot()
        current = records.get(pid)
        if current is None or current[1] != expected_start:
            return
        pidfd_send_signal(descriptor, signal.SIGKILL)
    finally:
        os.close(descriptor)


def _linux_terminate_owned_tree(process, baseline):
    """Kill and reap the complete owned descendant tree, including setsid escapes."""
    root_pid = process.pid
    initial, records = _linux_owned_processes(root_pid, None, {root_pid: None}, baseline)
    root_start = initial.get(root_pid)
    owned = {root_pid: root_start}
    owned.update(initial)
    reaped = set()
    failures = []
    root_waited = False
    root_signal_sent = False
    stable_empty = 0
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline:
        observed, records = _linux_owned_processes(root_pid, root_start, owned, baseline)
        owned.update(observed)
        if not root_signal_sent:
            try:
                os.killpg(root_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as error:
                failures.append(f'killpg: {type(error).__name__}: {error}')
            try:
                # kill() is a fallback when the process group disappeared or
                # a test/runtime does not expose a usable process group.
                if process.returncode is None:
                    process.kill()
            except ProcessLookupError:
                pass
            except BaseException as error:
                failures.append(f'kill root: {type(error).__name__}: {error}')
            root_signal_sent = True
        for pid in observed:
            if pid == root_pid:
                continue
            try:
                _linux_kill_pid(pid, observed[pid])
            except ProcessLookupError:
                pass
            except (OSError, RuntimeError) as error:
                failures.append(f'kill {pid}: {type(error).__name__}: {error}')
        if not root_waited:
            try:
                process.wait(timeout=1)
                root_waited = True
            except subprocess.TimeoutExpired:
                pass
            except BaseException as error:
                failures.append(f'wait root: {type(error).__name__}: {error}')
        for pid in list(owned):
            identity = (pid, owned[pid])
            if pid == root_pid or identity in reaped:
                continue
            current = records.get(pid)
            if current is not None and current[1] != owned[pid]:
                continue
            try:
                waited, _ = os.waitpid(pid, os.WNOHANG)
                if waited == pid:
                    reaped.add(identity)
            except ChildProcessError:
                # A disappeared process with no waitable child status is safe
                # only when it is also absent from the current /proc snapshot.
                if pid not in records:
                    reaped.add(identity)
            except OSError as error:
                failures.append(f'reap {pid}: {type(error).__name__}: {error}')
        observed, records = _linux_owned_processes(root_pid, root_start, owned, baseline)
        owned.update(observed)
        active = [pid for pid, start in observed.items()
            if pid != root_pid and (pid, start) not in reaped]
        if root_waited and not active:
            stable_empty += 1
            if stable_empty >= 2:
                break
        else:
            stable_empty = 0
        time.sleep(0.01)

    observed, records = _linux_owned_processes(root_pid, root_start, owned, baseline)
    active = [pid for pid, start in observed.items()
        if pid != root_pid and (pid, start) not in reaped]
    if not root_waited:
        failures.append('root process did not become waitable')
    if active:
        failures.append('owned descendants remain: ' + ','.join(map(str, sorted(active))))
    return not failures, len(reaped), failures


def capture(command, prefix, cwd, stdin=None, timeout=300, env=None, run_id=None, snapshot_sha256=None):
    """Keep separate raw byte streams and process state before interpreting any result."""
    command = list(map(str, command))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    output, errors, status = [Path(str(prefix) + ending) for ending in ['.stdout.log', '.stderr.log', '.status.json']]
    receipt = {'command': command, 'cwd': str(cwd), 'timeout_seconds': timeout,
        'started_utc': now(), 'status': 'running', 'returncode': None, 'timed_out': False,
        'stdin_sha256': sha(stdin) if stdin else None,
        'run_id': run_id, 'snapshot_sha256': snapshot_sha256,
        'process_ownership': 'linux_session_group' if sys.platform == 'linux' else 'direct_process_only',
        'process_tracking': 'linux_owned_descendant_tree' if sys.platform == 'linux' else 'direct_process_only',
        'process_tree_quiescent': False}
    write(status, receipt)
    started = time.monotonic()
    process = None
    subreaper = None
    baseline_children = {}
    quiescent = True
    try:
        with output.open('wb') as stdout, errors.open('wb') as stderr:
            with stdin.open('rb') if stdin else open(os.devnull, 'rb') as input_stream:
                if sys.platform == 'linux':
                    # Process-local adoption lets us reap only this session's orphaned solvers.
                    libc = ctypes.CDLL(None, use_errno=True)
                    subreaper = ctypes.c_int()
                    if libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0) != 0:
                        raise OSError(ctypes.get_errno(), 'PR_GET_CHILD_SUBREAPER')
                    if libc.prctl(36, 1, 0, 0, 0) != 0:
                        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')
                try:
                    if sys.platform == 'linux':
                        baseline_children = _linux_direct_children()
                    process = subprocess.Popen(command, cwd=cwd, stdin=input_stream,
                        stdout=stdout, stderr=stderr, env=env, start_new_session=sys.platform == 'linux')
                    quiescent = False
                    receipt['pid'] = process.pid
                    if sys.platform == 'linux':
                        # Keep the leader unreaped until killpg, preventing process-group ID reuse.
                        deadline = time.monotonic() + timeout
                        while os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                            if time.monotonic() >= deadline:
                                raise subprocess.TimeoutExpired(command, timeout)
                            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
                    else:
                        process.wait(timeout=timeout)
                finally:
                    try:
                        if process is not None:
                            if sys.platform == 'linux':
                                quiescent, reaped, cleanup_errors = _linux_terminate_owned_tree(
                                    process, baseline_children)
                                receipt.update(process_tree_quiescent=quiescent,
                                    descendants_reaped=reaped, cleanup_errors=cleanup_errors)
                            else:
                                if process.poll() is None:
                                    process.kill()
                                process.wait()
                                quiescent = True
                            if sys.platform != 'linux' and process.poll() is None:
                                process.kill()
                            if not quiescent:
                                receipt['cleanup_error'] = 'Owned descendant cleanup could not establish quiescence'
                    finally:
                        if subreaper is not None and libc.prctl(36, subreaper.value, 0, 0, 0) != 0:
                            raise OSError(ctypes.get_errno(), 'restore PR_SET_CHILD_SUBREAPER')
        receipt.update(status='completed', returncode=process.returncode)
    except subprocess.TimeoutExpired:
        receipt.update(status='timeout', timed_out=True)
    except OSError as error:
        receipt.update(status='launch_error' if process is None else 'process_error', error=f'{type(error).__name__}: {error}')
    except BaseException as error:
        receipt.update(status='process_error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        # Files receive raw child writes directly; closing them after reaping drains those writes.
        if quiescent:
            receipt.update(stdout_sha256=sha(output), stderr_sha256=sha(errors))
        else:
            receipt.update(status='process_error', error='Owned process cleanup incomplete; raw hashes not finalized')
        receipt.update(finished_utc=now(), elapsed_seconds=time.monotonic() - started)
        write(status, receipt)
        if not quiescent:
            raise ProcessCleanupError('Owned process cleanup incomplete; inspect ' + str(status))
    if receipt['status'] != 'completed':
        raise RuntimeError('Command ' + receipt['status'] + '; inspect ' + str(status))
    try:
        stdout, stderr = output.read_bytes().decode('utf-8'), errors.read_bytes().decode('utf-8')
    except UnicodeDecodeError as error:
        receipt['decode_error'] = str(error)
        write(status, receipt)
        raise RuntimeError('Non-UTF-8 command output; inspect ' + str(status)) from error
    return subprocess.CompletedProcess(command, receipt['returncode'], stdout, stderr)


def positive_verification(result):
    text = result.stdout + result.stderr
    matches = re.findall(r'verification results:: (\d+) verified, (\d+) errors', text)
    if result.returncode or len(matches) != 1 or int(matches[0][1]) or 'partial verification' in text:
        raise RuntimeError('Not a complete verification/compile result')
    return int(matches[0][0])


def invalid_rejected(result, site):
    return (result.returncode == 2 and result.stdout == ''
        and result.stderr == 'COMPOSITION_HARNESS_REJECTED ' + site + '\n')


def remaining_timeout(deadline, maximum):
    remaining = maximum if deadline is None else min(maximum, deadline - time.monotonic())
    if remaining <= 0:
        raise RuntimeError('Correctness wall budget exhausted; pending checks are incomplete')
    return remaining


def run_oracles(stage, out, runner, manifest, record, save, check_context, deadline=None, completed=None,
        run_id=None, snapshot_sha256=None):
    inputs = stage / 'correctness-inputs'
    record['oracles'] = {}
    for name, suite in manifest['suites'].items():
        commands, answers = inputs / (name + '.commands'), inputs / (name + '.answers')
        expected = {str(commands): suite['commands_sha256'], str(answers): suite['answers_sha256']}
        def check_command():
            check_context()
            check_hashes(expected)
        item = dict(suite, status='running')
        record['oracles'][name] = item
        save()
        try:
            if suite['kind'] == 'integer_oracle':
                check_command()
                try:
                    result = capture([runner], out / name, stage, stdin=commands,
                        timeout=remaining_timeout(deadline, 120), run_id=run_id,
                        snapshot_sha256=snapshot_sha256)
                finally:
                    check_command()
                item['passed'] = (result.returncode == 0 and result.stderr == ''
                    and result.stdout == answers.read_bytes().decode('utf-8'))
            else:
                item['results'] = []
                check_command()
                lines = commands.read_bytes().decode('utf-8').splitlines()
                sites = answers.read_bytes().decode('utf-8').splitlines()
                if len(lines) != suite['cases'] or len(sites) != len(lines):
                    raise RuntimeError('Invalid-command suite count changed: ' + name)
                for index, command in enumerate(lines):
                    prefix = out / (name + '-' + str(index))
                    line = Path(str(prefix) + '.command')
                    raw = (command + '\n').encode('utf-8')
                    line.write_bytes(raw)
                    expected[str(line)] = hashlib.sha256(raw).hexdigest()
                    check_command()
                    try:
                        result = capture([runner], prefix, stage, stdin=line,
                            timeout=remaining_timeout(deadline, 30), run_id=run_id,
                            snapshot_sha256=snapshot_sha256)
                    finally:
                        check_command()
                    rejected = invalid_rejected(result, sites[index])
                    item['results'].append({'index': index, 'expected_site': sites[index], 'rejected': rejected})
                    save()
                    if not rejected:
                        raise RuntimeError(f'Malformed command accepted: {name}/{index}')
                item['passed'] = True
            item['status'] = 'pass' if item['passed'] else 'error'
            if not item['passed']:
                raise RuntimeError('Independent integer oracle mismatch: ' + name)
        except Exception as error:
            item.update(status='error', error=f'{type(error).__name__}: {error}')
            raise
        finally:
            save()
        if completed:
            completed(name)


def library_gate(stage, prepared):
    build = json.loads((stage / 'build-evidence/build.json').read_text())
    if (build['status'] != 'pass' or build['benchmark_run']
            or build['source_sha256'] != prepared['variants']
            or set(build['libraries']) != set(prepared['variants'])
            or set(build['default_oracles']) != set(prepared['variants'])
            or build['infrastructure_sha256'] != prepared['infrastructure_sha256']
            or build['preparation_sha256'] != sha(stage / 'preparation.json')):
        raise RuntimeError('Incomplete or stale full-library/default-oracle gate')
    check_hashes(build['toolchain']['sha256'])
    for name, library in build['libraries'].items():
        if library['verified_items'] <= 0 or build['default_oracles'][name]['cases'] <= 0:
            raise RuntimeError('Empty full-library proof/default oracle: ' + name)
        directory = stage / 'build-evidence' / name
        check_hashes({str(directory / ('lib' + name + '.rlib')): library['rlib'],
            str(directory / (name + '.vir')): library['vir'],
            str(directory / 'default-runner'): build['default_oracles'][name]['runner_sha256']})
    return build


def mutation_bytes(original, before, after):
    """Replace one registered LF/CRLF span, retaining every outside byte."""
    if not before or before == after or '\r' in before + after:
        raise RuntimeError('Invalid registered mutation span')
    before, after = before.encode('utf-8'), after.encode('utf-8')
    matches, seen = [], set()
    for newline in [b'\n', b'\r\n']:
        old = before.replace(b'\n', newline)
        if old in seen:
            continue
        seen.add(old)
        offset = original.find(old)
        if offset < 0:
            continue
        if original.find(old, offset + 1) >= 0:
            raise RuntimeError('Mutant raw anchor mismatch: multiple spans')
        if b'\n' not in before and b'\n' in after:
            lines, crlf = original.count(b'\n'), original.count(b'\r\n')
            if 0 < crlf < lines:
                raise RuntimeError('Ambiguous mutation replacement newline')
            newline = b'\r\n' if crlf else b'\n'
        matches.append((offset, old, after.replace(b'\n', newline)))
    if len(matches) != 1:
        raise RuntimeError('Mutant raw anchor mismatch: expected one span')
    offset, old, new = matches[0]
    return (original[:offset] + new + original[offset + len(old):],
        {'offset': offset, 'before_hex': old.hex(), 'after_hex': new.hex()})


def check_mutation_copy(copy, expected):
    actual = {p.relative_to(copy).as_posix() for p in copy.rglob('*') if p.is_file()}
    if actual != set(expected):
        raise RuntimeError('Mutation copy inventory changed: ' + str(copy))
    check_hashes(expected, copy)


def check_variant_context(stage, name, verifier, out, record, report):
    check_hashes({str(stage / 'preparation.json'): report['preparation_sha256'],
        str(stage / 'build-evidence/build.json'): report['build_gate_sha256'],
        str(stage / 'correctness-inputs/manifest.json'): report['input_manifest_sha256']})
    prepared = check_prepared(stage)
    build = library_gate(stage, prepared)
    if (prepared['variants'] != report['source_sha256'] or build['toolchain'] != report['toolchain']
            or record['paired_library'] != build['libraries'][name]
            or str(verifier) != report['verifier'] or str(verifier) not in build['toolchain']['sha256']):
        raise RuntimeError('Variant source/tool/pair context changed: ' + name)
    if 'runner_sha256' in record:
        check_hashes({str(out / name / 'runner'): record['runner_sha256']})
    if 'runner_source_sha256' in record:
        check_hashes({str(stage / 'correctness-inputs/runner.rs'): record['runner_source_sha256']})
    check_mutation_copy(stage / name / 'native',
        {path[len('native/'):]: digest for path, digest in report['source_sha256'][name].items()
            if path.startswith('native/')})


def compile_runner(stage, name, verifier, out, record, report, deadline):
    directory, libdir = out / name, stage / 'build-evidence' / name
    runner = directory / 'runner'
    try:
        check_variant_context(stage, name, verifier, out, record, report)
        try:
            result = capture([verifier, stage / 'correctness-inputs/runner.rs',
                '--import', 'experiment=' + str(libdir / (name + '.vir')),
                '--extern', 'experiment=' + str(libdir / ('lib' + name + '.rlib')),
                '--compile', '-O', '-o', runner], directory / 'runner-build', stage,
                timeout=remaining_timeout(deadline, 300), run_id=report['run_id'],
                snapshot_sha256=report['snapshot_sha256'])
            record.update(runner_verified_items=positive_verification(result),
                runner_role='Imported test infrastructure; zero proof items are compile-only', runner_sha256=sha(runner))
        finally:
            check_variant_context(stage, name, verifier, out, record, report)
    except Exception as error:
        record.update(status='error', error=f'{type(error).__name__}: {error}')
        raise


def run_mutations(stage, name, registry, verifier, out, record, report, save, deadline):
    copy = out / 'mutation-sources' / name
    shutil.copytree(stage / name / 'native', copy / 'native')
    source_hashes = {path: digest for path, digest in report['source_sha256'][name].items()
        if path.startswith('native/')}
    def check_context(expected):
        check_variant_context(stage, name, verifier, out, record, report)
        check_mutation_copy(copy, expected)
    record['mutations'] = {}
    for row in registry:
        item = {'status': 'pending', 'applicable': row['applicable'], 'reason': row['reason']}
        record['mutations'][row['name']] = item
        save()
        if not row['applicable']:
            item['status'] = 'not_applicable'
            save()
            continue
        check_context(source_hashes)
        source = copy / row['file']
        original = source.read_bytes()
        if hashlib.sha256(original).hexdigest() != row['source_sha256']:
            raise RuntimeError('Mutant source/anchor changed: ' + name + '/' + row['name'])
        mutated, span = mutation_bytes(original, row['before'], row['after'])
        digest = hashlib.sha256(mutated).hexdigest()
        mutated_hashes = dict(source_hashes, **{row['file']: digest})
        remaining_timeout(deadline, 300)
        restore = True
        try:
            source.write_bytes(mutated)
            artifact = out / name / 'mutations' / (row['name'] + '.rs')
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(source.read_bytes())
            item.update(status='running', source_before_sha256=row['source_sha256'],
                mutated_source_sha256=digest, byte_span=span, module=row['module'])
            save()
            check_context(mutated_hashes)
            timeout = remaining_timeout(deadline, 300)
            report['mutation_commands_started'] += 1
            save()
            try:
                try:
                    result = capture([verifier, copy / 'native/lib.rs', '--crate-name', name, '--crate-type', 'lib',
                        '--verify-module', row['module'], '--multiple-errors', '0'], artifact.with_suffix(''), copy,
                timeout=timeout, run_id=report.get('run_id'), snapshot_sha256=report.get('snapshot_sha256'))
                except ProcessCleanupError:
                    restore = False
                    raise
            finally:
                check_context(mutated_hashes)
            item['semantic_vc_failure'] = strict_mutant(result)
            if not item['semantic_vc_failure']:
                raise RuntimeError('No actual semantic VC failure: ' + name + '/' + row['name'])
        except Exception as error:
            item.update(status='error', error=f'{type(error).__name__}: {error}')
            raise
        finally:
            try:
                if not restore:
                    raise ProcessCleanupError('Mutation copy retained because owned process cleanup is incomplete')
                source.write_bytes(original)
                check_mutation_copy(copy, source_hashes)
                item['source_restored_sha256'] = sha(source)
                check_context(source_hashes)
            except Exception as error:
                item.update(status='error', restoration_error=f'{type(error).__name__}: {error}')
                raise
            finally:
                save()
        item['status'] = 'pass'
        report['pending_mutations'].remove(name + '/' + row['name'])
        save()


def correctness(stage, run_id=None, snapshot_sha256=None, execution_started_utc=None):
    out = stage / 'correctness-evidence'
    out.mkdir()
    run_id = run_id or os.environ.get('TOOM4_CI_RUN_ID') or uuid.uuid4().hex
    execution_started = (execution_started_utc or os.environ.get('TOOM4_CI_EXECUTION_STARTED_UTC')
        or now())
    report = {'status': 'running', 'run_id': run_id, 'execution_started_utc': execution_started,
        'started_utc': now(), 'wall_budget_seconds': WALL_BUDGET_SECONDS,
        'timing_executed': False, 'selection_executed': False, 'promotion_allowed': False,
        'mutation_method': 'Full-library typecheck with module verification after complete positive same-source library proof',
        'variants': {}, 'mutation_commands_started': 0, 'pending_oracles': [], 'pending_mutations': []}
    def save():
        write(out / 'correctness.json', report)
    save()
    started = time.monotonic()
    deadline = started + WALL_BUDGET_SECONDS
    prepared = build = None
    try:
        if sys.platform != 'linux':
            raise RuntimeError('Correctness execution requires Linux owned-session process cleanup')
        prepared = check_prepared(stage)
        build = library_gate(stage, prepared)
        inputs = stage / 'correctness-inputs'
        manifest = json.loads((inputs / 'manifest.json').read_text())
        names = list(manifest['mutation_registry'])
        policy = json.loads((stage / 'policy.json').read_text())
        if names != policy['modes'][1:-1]:
            raise RuntimeError('Incomplete correctness variant registry')
        report.update(build_gate_sha256=sha(stage / 'build-evidence/build.json'),
            preparation_sha256=sha(stage / 'preparation.json'), input_manifest_sha256=sha(inputs / 'manifest.json'),
            source_sha256=prepared['variants'], toolchain=build['toolchain'],
            snapshot_sha256=(snapshot_sha256 or os.environ.get('TOOM4_CI_SNAPSHOT_SHA256')
                or sha(stage / 'preparation.json')),
            pending_oracles=[name + '/' + suite for name in names for suite in manifest['suites']],
            pending_mutations=[name + '/' + row['name'] for name in names
                for row in manifest['mutation_registry'][name] if row['applicable']])
        save()
        verifier = Path(os.environ['VERUS_BIN']).resolve()
        if str(verifier) not in build['toolchain']['sha256']:
            raise RuntimeError('Correctness verifier is not bound to the library toolchain')
        report['verifier'] = str(verifier)
        # Every variant's forced/helper suites finish before the mutation phase.
        for name in names:
            directory = out / name
            directory.mkdir()
            library = build['libraries'][name]
            record = {'status': 'running', 'paired_library': library, 'runner_source_sha256': sha(inputs / 'runner.rs')}
            report['variants'][name] = record
            save()
            runner = directory / 'runner'
            compile_runner(stage, name, verifier, out, record, report, deadline)
            def check_context():
                check_variant_context(stage, name, verifier, out, record, report)
            def completed(suite):
                report['pending_oracles'].remove(name + '/' + suite)
                save()
            run_oracles(stage, directory, runner, manifest, record, save, check_context, deadline, completed,
                run_id=run_id, snapshot_sha256=report['snapshot_sha256'])
            check_hashes({str(runner): record['runner_sha256']})
        for name in names:
            run_mutations(stage, name, manifest['mutation_registry'][name], verifier, out,
                report['variants'][name], report, save, deadline)
            report['variants'][name]['status'] = 'pass'
            save()
        check_prepared(stage)
        library_gate(stage, prepared)
        if report['pending_oracles'] or report['pending_mutations']:
            raise RuntimeError('Correctness matrix is incomplete')
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='error', error=f'{type(error).__name__}: {error}')
    finally:
        try:
            if prepared is not None:
                check_prepared(stage)
            if build is not None:
                library_gate(stage, prepared)
            for name, record in report['variants'].items():
                if 'runner_sha256' in record:
                    check_hashes({str(out / name / 'runner'): record['runner_sha256']})
            report['source_tool_pair_identity_before_after'] = True
            remaining_timeout(deadline, 1)
        except Exception as error:
            report.update(status='error', identity_error=f'{type(error).__name__}: {error}')
        report['finished_utc'] = now()
        report['elapsed_seconds'] = time.monotonic() - started
        unsafe = []
        for path in out.rglob('*.status.json'):
            receipt = json.loads(path.read_text())
            if (receipt.get('pid') is not None and receipt.get('process_ownership') == 'linux_session_group'
                    and not receipt.get('process_tree_quiescent')):
                unsafe.append(path.relative_to(out).as_posix())
        if unsafe:
            report.update(status='error', process_cleanup_incomplete=unsafe, artifacts_sha256={})
        else:
            report['artifacts_sha256'] = {p.relative_to(out).as_posix(): sha(p)
                for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'correctness.json'}
        save()
    print(json.dumps({key: report[key] for key in ['status', 'error', 'mutation_commands_started',
        'pending_oracles', 'pending_mutations'] if key in report}, indent=2))
    return report['status'] == 'pass'


def captured_result(prefix, command, cwd, stdin_sha256=None):
    status = json.loads(Path(str(prefix) + '.status.json').read_text())
    if (status['status'] != 'completed' or status['timed_out'] or status.get('decode_error')
            or status['command'] != list(map(str, command)) or status['cwd'] != str(cwd)
            or status['stdin_sha256'] != stdin_sha256 or not 0 < status['timeout_seconds'] <= 300):
        raise RuntimeError('Incomplete or mismatched raw command receipt: ' + str(prefix))
    output, errors = Path(str(prefix) + '.stdout.log'), Path(str(prefix) + '.stderr.log')
    check_hashes({str(output): status['stdout_sha256'], str(errors): status['stderr_sha256']})
    return subprocess.CompletedProcess(command, status['returncode'],
        output.read_bytes().decode('utf-8'), errors.read_bytes().decode('utf-8'))


def _evidence_timestamp(value):
    if not isinstance(value, str):
        raise RuntimeError('Missing correctness evidence timestamp')
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError('Invalid correctness evidence timestamp') from error
    if parsed.tzinfo is None or parsed.utcoffset() != datetime.timedelta(0):
        raise RuntimeError('Correctness evidence timestamps must be UTC')
    return parsed


def validate_correctness(stage, build, expected_run_id=None, minimum_started_utc=None,
        expected_snapshot_sha256=None):
    prepared = check_prepared(stage)
    inputs, out = stage / 'correctness-inputs', stage / 'correctness-evidence'
    manifest = json.loads((inputs / 'manifest.json').read_text())
    report = json.loads((out / 'correctness.json').read_text())
    names = json.loads((stage / 'policy.json').read_text())['modes'][1:-1]
    report_started = _evidence_timestamp(report.get('started_utc'))
    report_finished = _evidence_timestamp(report.get('finished_utc'))
    execution_started = _evidence_timestamp(report.get('execution_started_utc'))
    if (report_started > report_finished or execution_started > report_started
            or not report.get('run_id') or not re.fullmatch(r'[0-9a-f]{32}', report['run_id'])
            or not re.fullmatch(r'[0-9a-f]{64}', report.get('snapshot_sha256', ''))
            or (expected_run_id is not None and report['run_id'] != expected_run_id)
            or (expected_snapshot_sha256 is not None
                and report['snapshot_sha256'] != expected_snapshot_sha256)
            or (minimum_started_utc is not None
                and execution_started < _evidence_timestamp(minimum_started_utc))):
        raise RuntimeError('Correctness report is not bound to this fresh source snapshot')
    if (report['status'] != 'pass' or report['timing_executed'] or report['selection_executed']
            or report['promotion_allowed'] or report['pending_oracles'] or report['pending_mutations']
            or report.get('process_cleanup_incomplete')
            or not report.get('source_tool_pair_identity_before_after')
            or set(report['variants']) != set(names) or list(manifest['mutation_registry']) != names
            or report['build_gate_sha256'] != sha(stage / 'build-evidence/build.json')
            or report['preparation_sha256'] != sha(stage / 'preparation.json')
            or report['input_manifest_sha256'] != sha(inputs / 'manifest.json')
            or report['source_sha256'] != prepared['variants'] or report['toolchain'] != build['toolchain']
            or report['verifier'] not in build['toolchain']['sha256']
            or report['wall_budget_seconds'] != WALL_BUDGET_SECONDS
            or not 0 <= report['elapsed_seconds'] <= WALL_BUDGET_SECONDS
            or report['mutation_commands_started'] != sum(row['applicable']
                for rows in manifest['mutation_registry'].values() for row in rows)):
        raise RuntimeError('Incomplete or stale forced/helper/mutation gate')
    check_hashes(report['artifacts_sha256'], out)
    artifact_paths = {path.relative_to(out).as_posix() for path in out.rglob('*')
        if path.is_file() and path.name != 'correctness.json'}
    if artifact_paths != set(report['artifacts_sha256']):
        raise RuntimeError('Correctness artifact inventory is incomplete')
    receipt_paths = list(out.rglob('*.status.json'))
    if not receipt_paths:
        raise RuntimeError('Correctness gate has no process receipts')
    for path in receipt_paths:
        receipt = json.loads(path.read_text())
        receipt_started = _evidence_timestamp(receipt.get('started_utc'))
        receipt_finished = _evidence_timestamp(receipt.get('finished_utc'))
        if (receipt.get('status') != 'completed' or receipt.get('run_id') != report['run_id']
                or receipt.get('snapshot_sha256') != report['snapshot_sha256']
                or receipt.get('process_ownership') != 'linux_session_group'
                or receipt.get('process_tracking') != 'linux_owned_descendant_tree'
                or receipt.get('process_tree_quiescent') is not True
                or receipt_started < report_started or receipt_finished > report_finished
                or receipt_started > receipt_finished):
            raise RuntimeError('Incomplete or stale process receipt: ' + str(path))
    for name in names:
        directory, libdir = out / name, stage / 'build-evidence' / name
        record = report['variants'][name]
        if (record['status'] != 'pass' or record['paired_library'] != build['libraries'][name]
                or record['runner_source_sha256'] != manifest['runner_sha256']
                or set(record['oracles']) != set(manifest['suites'])
                or set(record['mutations']) != {row['name'] for row in manifest['mutation_registry'][name]}):
            raise RuntimeError('Incomplete variant correctness: ' + name)
        runner = directory / 'runner'
        check_hashes({str(runner): record['runner_sha256']})
        compile_command = [report['verifier'], inputs / 'runner.rs', '--import', 'experiment=' + str(libdir / (name + '.vir')),
            '--extern', 'experiment=' + str(libdir / ('lib' + name + '.rlib')), '--compile', '-O', '-o', runner]
        if positive_verification(captured_result(directory / 'runner-build', compile_command, stage)) != record['runner_verified_items']:
            raise RuntimeError('Harness compile evidence changed: ' + name)
        for suite_name, suite in manifest['suites'].items():
            item = record['oracles'][suite_name]
            if any(item[key] != value for key, value in suite.items()) or item['status'] != 'pass' or not item['passed']:
                raise RuntimeError('Incomplete oracle suite: ' + name + '/' + suite_name)
            answers = (inputs / (suite_name + '.answers')).read_bytes().decode('utf-8')
            if suite['kind'] == 'integer_oracle':
                result = captured_result(directory / suite_name, [runner], stage, suite['commands_sha256'])
                if result.returncode or result.stderr or result.stdout != answers:
                    raise RuntimeError('Raw integer oracle mismatch: ' + name + '/' + suite_name)
            else:
                commands = (inputs / (suite_name + '.commands')).read_bytes().decode('utf-8').splitlines()
                sites = answers.splitlines()
                if len(item['results']) != suite['cases'] or len(commands) != len(sites) or len(sites) != suite['cases']:
                    raise RuntimeError('Incomplete malformed-command coverage: ' + name + '/' + suite_name)
                for index, (command, site) in enumerate(zip(commands, sites)):
                    prefix = directory / (suite_name + '-' + str(index))
                    digest = hashlib.sha256((command + '\n').encode('utf-8')).hexdigest()
                    check_hashes({str(prefix) + '.command': digest})
                    result = captured_result(prefix, [runner], stage, digest)
                    if (not invalid_rejected(result, site) or item['results'][index]
                            != {'index': index, 'expected_site': site, 'rejected': True}):
                        raise RuntimeError('Malformed-command rejection was not from expected harness validation')
        copy = out / 'mutation-sources' / name
        check_mutation_copy(copy, {path: digest for path, digest in prepared['variants'][name].items()
            if path.startswith('native/')})
        for row in manifest['mutation_registry'][name]:
            item = record['mutations'][row['name']]
            if item['applicable'] != row['applicable'] or item['reason'] != row['reason']:
                raise RuntimeError('Mutation applicability changed')
            if not row['applicable']:
                if item['status'] != 'not_applicable':
                    raise RuntimeError('Missing declared inapplicable mutant')
                continue
            original = (stage / name / row['file']).read_bytes()
            mutated, span = mutation_bytes(original, row['before'], row['after'])
            digest = hashlib.sha256(mutated).hexdigest()
            artifact = directory / 'mutations' / (row['name'] + '.rs')
            check_hashes({str(artifact): digest})
            command = [report['verifier'], copy / 'native/lib.rs', '--crate-name', name, '--crate-type', 'lib',
                '--verify-module', row['module'], '--multiple-errors', '0']
            if (item['status'] != 'pass' or not item['semantic_vc_failure']
                    or item['source_before_sha256'] != row['source_sha256']
                    or hashlib.sha256(original).hexdigest() != row['source_sha256']
                    or item.get('byte_span') != span
                    or item['source_restored_sha256'] != row['source_sha256'] or item['mutated_source_sha256'] != digest
                    or not strict_mutant(captured_result(artifact.with_suffix(''), command, copy))):
                raise RuntimeError('Missing actual semantic VC failure: ' + name + '/' + row['name'])
    return sha(out / 'correctness.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--run-id')
    parser.add_argument('--snapshot-sha256')
    parser.add_argument('--execution-started-utc')
    args = parser.parse_args()
    raise SystemExit(not correctness(args.stage.resolve(), args.run_id,
        args.snapshot_sha256, args.execution_started_utc))

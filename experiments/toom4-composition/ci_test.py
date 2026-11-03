"""Portable CI-binding rejection tests with synthetic files; no arithmetic execution."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from ci import checkout_identity, command, validate_results
from common import checked, sha, write


class EvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.stage = Path(self.temporary.name).resolve()
        self.names = ['baseline', 'entry', 'odd', 'fusion', 'signed', 'odd_signed', 'fusion_signed']
        self.directory = self.stage / 'exploration-build'
        self.directory.mkdir()
        self.tool = self.stage / 'synthetic-tool'
        self.tool.write_bytes(b'synthetic tool, not an executable')
        (self.stage / 'policy.json').write_text(json.dumps({'modes': self.names + ['gmp']}))
        (self.stage / 'audit_codegen.py').write_text('# synthetic codegen fixture\n')
        self.prepared = {'variants': {}, 'policy_sha256': sha(self.stage / 'policy.json'),
            'infrastructure_sha256': {'audit_codegen.py': sha(self.stage / 'audit_codegen.py')}}
        self.build = {'status': 'pass', 'benchmark_run': False, 'libraries': {}, 'default_oracles': {},
            'toolchain': {'sha256': {str(self.tool): sha(self.tool)}}}
        self.pairs = {}
        for name in self.names:
            source = self.stage / name / 'native/lib.rs'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'// synthetic source, not verified\n')
            self.prepared['variants'][name] = {'native/lib.rs': sha(source)}
            directory = self.stage / 'build-evidence' / name
            directory.mkdir(parents=True)
            lib, vir, runner = directory / ('lib' + name + '.rlib'), directory / (name + '.vir'), directory / 'default-runner'
            for path in [lib, vir, runner]:
                path.write_text('synthetic fixture: ' + name + '/' + path.name)
            self.build['libraries'][name] = {'rlib': sha(lib), 'vir': sha(vir), 'verified_items': 1}
            self.build['default_oracles'][name] = {'cases': 1, 'runner_sha256': sha(runner)}
            self.pairs.update({str(lib): sha(lib), str(vir): sha(vir)})
        write(self.stage / 'preparation.json', self.prepared)
        self.build.update(source_sha256=copy.deepcopy(self.prepared['variants']),
            infrastructure_sha256=self.prepared['infrastructure_sha256'],
            preparation_sha256=sha(self.stage / 'preparation.json'))
        write(self.stage / 'build-evidence/build.json', self.build)
        for name in ['compare.rs', 'compare', 'disassembly.txt', 'relocations.txt']:
            (self.directory / name).write_text('synthetic fixture: ' + name)
        self.binding = {'status': 'pass', 'phase': 'exploration', 'modes': self.names + ['gmp'],
            'paired_library_sha256': self.pairs, 'source_manifest_sha256': sha(self.stage / 'preparation.json'),
            'build_gate_sha256': sha(self.stage / 'build-evidence/build.json'), 'toolchain': self.build['toolchain'],
            'policy_sha256': self.prepared['policy_sha256'], 'source_sha256': sha(self.directory / 'compare.rs'),
            'binary_sha256': sha(self.directory / 'compare'), 'runtime_sha256': {str(self.tool): sha(self.tool)}}
        write(self.directory / 'binding.json', self.binding)
        self.audit = {'status': 'inspection_complete', 'phase': 'exploration',
            'binary_sha256': self.binding['binary_sha256'], 'binding_sha256': sha(self.directory / 'binding.json'),
            'script_sha256': sha(self.stage / 'audit_codegen.py'), 'actual_default_entries': {
                name + '::arithmetic::' + entry: {} for name in self.names for entry in ['mul_mod', 'square_mod']},
            'artifacts': {name: sha(self.directory / name) for name in ['disassembly.txt', 'relocations.txt']},
            'tools': {str(self.tool): {'sha256': sha(self.tool)}}}
        write(self.directory / 'codegen-audit.json', self.audit)
        self.make_correctness_fixture()

    def make_correctness_fixture(self):
        from correctness import WALL_BUDGET_SECONDS
        self.inputs = self.stage / 'correctness-inputs'
        self.inputs.mkdir()
        self.correctness_dir = self.stage / 'correctness-evidence'
        self.correctness_dir.mkdir()
        (self.inputs / 'runner.rs').write_text('// synthetic imported test infrastructure\n')
        for name, value in [('tiny.commands', b'example\n'), ('tiny.answers', b'7\n'),
                ('bad.commands', b'bad\n'), ('bad.answers', b'syntax\n')]:
            (self.inputs / name).write_bytes(value)
        source_digest = self.prepared['variants']['entry']['native/lib.rs']
        rows = [{'name': 'real_vc', 'file': 'native/lib.rs', 'module': 'example',
            'applicable': True, 'reason': None, 'source_sha256': source_digest,
            'before': 'synthetic source', 'after': 'mutated source'},
            {'name': 'absent_feature', 'file': 'native/lib.rs', 'module': 'example',
                'applicable': False, 'reason': 'Declared absent fixture feature'}]
        self.manifest = {'runner_sha256': sha(self.inputs / 'runner.rs'), 'suites': {
            name: {'kind': kind, 'cases': 1, 'commands_sha256': sha(self.inputs / (name + '.commands')),
                'answers_sha256': sha(self.inputs / (name + '.answers'))}
            for name, kind in [('tiny', 'integer_oracle'), ('bad', 'invalid')]},
            'mutation_registry': {name: copy.deepcopy(rows) for name in self.names[1:]}}
        write(self.inputs / 'manifest.json', self.manifest)
        self.prepared['correctness_inputs_sha256'] = {p.relative_to(self.stage).as_posix(): sha(p)
            for p in self.inputs.iterdir()}
        write(self.stage / 'preparation.json', self.prepared)
        self.build['preparation_sha256'] = sha(self.stage / 'preparation.json')
        self.save_build()
        self.binding['source_manifest_sha256'] = sha(self.stage / 'preparation.json')
        self.save_binding()
        self.correctness = {'status': 'pass', 'run_id': 'a' * 32,
            'execution_started_utc': '2026-01-01T00:00:00+00:00',
            'started_utc': '2026-01-01T00:00:01+00:00',
            'finished_utc': '2026-01-01T00:00:03+00:00',
            'snapshot_sha256': sha(self.stage / 'preparation.json'),
            'timing_executed': False, 'selection_executed': False,
            'promotion_allowed': False, 'pending_oracles': [], 'pending_mutations': [],
            'source_tool_pair_identity_before_after': True, 'verifier': str(self.tool),
            'wall_budget_seconds': WALL_BUDGET_SECONDS, 'elapsed_seconds': 1, 'mutation_commands_started': 6,
            'build_gate_sha256': sha(self.stage / 'build-evidence/build.json'),
            'preparation_sha256': sha(self.stage / 'preparation.json'), 'input_manifest_sha256': sha(self.inputs / 'manifest.json'),
            'source_sha256': self.prepared['variants'], 'toolchain': self.build['toolchain'], 'variants': {}}
        for name in self.names[1:]:
            directory = self.correctness_dir / name
            directory.mkdir()
            runner = directory / 'runner'
            runner.write_bytes(b'synthetic runner')
            libdir = self.stage / 'build-evidence' / name
            command = [self.tool, self.inputs / 'runner.rs', '--import', 'experiment=' + str(libdir / (name + '.vir')),
                '--extern', 'experiment=' + str(libdir / ('lib' + name + '.rlib')), '--compile', '-O', '-o', runner]
            self.receipt(directory / 'runner-build', command, self.stage, 0, b'verification results:: 0 verified, 0 errors\n')
            self.receipt(directory / 'tiny', [runner], self.stage, 0, b'7\n', stdin_sha256=self.manifest['suites']['tiny']['commands_sha256'])
            bad = directory / 'bad-0'
            Path(str(bad) + '.command').write_bytes(b'bad\n')
            self.receipt(bad, [runner], self.stage, 2, b'', b'COMPOSITION_HARNESS_REJECTED syntax\n',
                self.manifest['suites']['bad']['commands_sha256'])
            source_copy = self.correctness_dir / 'mutation-sources' / name
            (source_copy / 'native').mkdir(parents=True)
            original = self.stage / name / 'native/lib.rs'
            (source_copy / 'native/lib.rs').write_bytes(original.read_bytes())
            artifact = directory / 'mutations/real_vc.rs'
            artifact.parent.mkdir()
            artifact.write_bytes(original.read_bytes().replace(b'synthetic source', b'mutated source'))
            command = [self.tool, source_copy / 'native/lib.rs', '--crate-name', name, '--crate-type', 'lib',
                '--verify-module', 'example', '--multiple-errors', '0']
            self.receipt(artifact.with_suffix(''), command, source_copy, 1,
                b'verification results:: 1 verified, 1 errors\nerror: postcondition not satisfied\nerror: aborting due to 1 previous error\n')
            self.correctness['variants'][name] = {'status': 'pass', 'paired_library': self.build['libraries'][name],
                'runner_source_sha256': self.manifest['runner_sha256'], 'runner_sha256': sha(runner), 'runner_verified_items': 0,
                'oracles': {suite: dict(values, status='pass', passed=True) for suite, values in self.manifest['suites'].items()},
                'mutations': {'real_vc': {'status': 'pass', 'applicable': True, 'reason': None, 'semantic_vc_failure': True,
                    'byte_span': {'offset': original.read_bytes().index(b'synthetic source'),
                        'before_hex': b'synthetic source'.hex(), 'after_hex': b'mutated source'.hex()},
                    'source_before_sha256': sha(original), 'source_restored_sha256': sha(original), 'mutated_source_sha256': sha(artifact)},
                    'absent_feature': {'status': 'not_applicable', 'applicable': False, 'reason': 'Declared absent fixture feature'}}}
            self.correctness['variants'][name]['oracles']['bad']['results'] = [{'index': 0, 'expected_site': 'syntax', 'rejected': True}]
        self.save_correctness()

    def receipt(self, prefix, command, cwd, code, stdout, stderr=b'', stdin_sha256=None):
        output, errors = Path(str(prefix) + '.stdout.log'), Path(str(prefix) + '.stderr.log')
        output.write_bytes(stdout)
        errors.write_bytes(stderr)
        write(Path(str(prefix) + '.status.json'), {'status': 'completed', 'timed_out': False,
            'run_id': self.correctness['run_id'], 'snapshot_sha256': self.correctness['snapshot_sha256'],
            'started_utc': '2026-01-01T00:00:01.500000+00:00',
            'finished_utc': '2026-01-01T00:00:02+00:00',
            'process_ownership': 'linux_session_group', 'process_tracking': 'linux_owned_descendant_tree',
            'process_tree_quiescent': True,
            'returncode': code, 'command': list(map(str, command)), 'cwd': str(cwd),
            'stdin_sha256': stdin_sha256, 'timeout_seconds': 300,
            'stdout_sha256': sha(output), 'stderr_sha256': sha(errors)})

    def save_correctness(self):
        self.correctness['artifacts_sha256'] = {p.relative_to(self.correctness_dir).as_posix(): sha(p)
            for p in self.correctness_dir.rglob('*') if p.is_file() and p.name != 'correctness.json'}
        write(self.correctness_dir / 'correctness.json', self.correctness)

    def save_build(self):
        write(self.stage / 'build-evidence/build.json', self.build)
        self.binding['build_gate_sha256'] = sha(self.stage / 'build-evidence/build.json')
        self.save_binding()

    def save_binding(self):
        write(self.directory / 'binding.json', self.binding)
        self.audit['binding_sha256'] = sha(self.directory / 'binding.json')
        write(self.directory / 'codegen-audit.json', self.audit)

    def test_consistent_synthetic_receipts(self):
        self.assertEqual(len(validate_results(self.stage)), 4)

    def test_reject_running_correctness_report(self):
        self.correctness['status'] = 'running'
        self.save_correctness()
        with self.assertRaisesRegex(RuntimeError, 'Incomplete or stale forced/helper/mutation gate'):
            validate_results(self.stage)

    def test_reject_correctness_report_from_another_run(self):
        with self.assertRaisesRegex(RuntimeError, 'fresh source snapshot'):
            validate_results(self.stage, expected_run_id='b' * 32)

    def test_reject_incomplete_cleanup_even_when_top_status_pass(self):
        self.correctness['process_cleanup_incomplete'] = ['entry/tiny.status.json']
        self.save_correctness()
        with self.assertRaisesRegex(RuntimeError, 'forced/helper/mutation gate'):
            validate_results(self.stage)

    def test_reject_missing_applicable_mutant_even_when_pass_is_claimed(self):
        del self.correctness['variants']['entry']['mutations']['real_vc']
        self.save_correctness()
        with self.assertRaisesRegex(RuntimeError, 'Incomplete variant correctness'):
            validate_results(self.stage)

    def test_reject_raw_mixed_mutant_failure_even_when_boolean_claims_pass(self):
        path = self.correctness_dir / 'entry/mutations/real_vc.stderr.log'
        path.write_bytes(b'error[E0308]: mismatched types\n')
        status_path = self.correctness_dir / 'entry/mutations/real_vc.status.json'
        status = json.loads(status_path.read_text())
        status['stderr_sha256'] = sha(path)
        write(status_path, status)
        self.save_correctness()
        with self.assertRaisesRegex(RuntimeError, 'actual semantic VC failure'):
            validate_results(self.stage)

    def test_reject_changed_expected_answers(self):
        (self.inputs / 'tiny.answers').write_bytes(b'8\n')
        with self.assertRaisesRegex(RuntimeError, 'Identity changed'):
            validate_results(self.stage)

    def test_reject_pending_matrix_even_when_top_status_pass(self):
        self.correctness['pending_mutations'] = ['entry/real_vc']
        self.save_correctness()
        with self.assertRaisesRegex(RuntimeError, 'forced/helper/mutation gate'):
            validate_results(self.stage)

    def test_reject_stale_proof_source_map(self):
        self.build['source_sha256']['entry']['native/lib.rs'] = '0' * 64
        self.save_build()
        with self.assertRaisesRegex(RuntimeError, 'stale full-library'):
            validate_results(self.stage)

    def test_reject_incomplete_library_set(self):
        del self.build['libraries']['signed']
        self.save_build()
        with self.assertRaisesRegex(RuntimeError, 'full-library'):
            validate_results(self.stage)

    def test_reject_empty_oracle(self):
        self.build['default_oracles']['odd']['cases'] = 0
        self.save_build()
        with self.assertRaisesRegex(RuntimeError, 'Empty proof or oracle'):
            validate_results(self.stage)

    def test_reject_changed_vir_pair(self):
        (self.stage / 'build-evidence/entry/entry.vir').write_text('different metadata')
        with self.assertRaisesRegex(RuntimeError, 'Identity changed'):
            validate_results(self.stage)

    def test_reject_missing_baseline_square_entry(self):
        del self.audit['actual_default_entries']['baseline::arithmetic::square_mod']
        write(self.directory / 'codegen-audit.json', self.audit)
        with self.assertRaisesRegex(RuntimeError, 'Missing compiled production entry'):
            validate_results(self.stage)

    def test_reject_stale_codegen_binary(self):
        self.audit['binary_sha256'] = '0' * 64
        write(self.directory / 'codegen-audit.json', self.audit)
        with self.assertRaisesRegex(RuntimeError, 'stale linked-codegen'):
            validate_results(self.stage)

    def test_reject_changed_runtime(self):
        self.tool.write_bytes(b'changed tool/runtime fixture')
        with self.assertRaisesRegex(RuntimeError, 'Identity changed'):
            validate_results(self.stage)

    def test_reject_changed_prepared_source(self):
        (self.stage / 'entry/native/lib.rs').write_text('changed source')
        with self.assertRaisesRegex(RuntimeError, 'Identity changed'):
            validate_results(self.stage)


class FailureLogTests(unittest.TestCase):
    def test_clean_checkout_identity_requires_classifier_fixtures_tracked(self):
        def git(*args):
            if args == ('rev-parse', 'HEAD'):
                return 'synthetic-commit'
            if args == ('status', '--porcelain', '--untracked-files=normal'):
                return ''
            if args[:2] == ('ls-files', '--'):
                return ''
            raise AssertionError(args)
        with patch('ci.git', side_effect=git), self.assertRaisesRegex(RuntimeError, 'not tracked'):
            checkout_identity()

    def test_stale_running_correctness_report_cannot_finalize_ci_inventory(self):
        import shutil
        from ci import _fresh_complete_correctness
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = EvidenceBindingTests()
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            stage = root / 'stage'
            shutil.copytree(fixture.stage, stage)
            correctness_path = stage / 'correctness-evidence/correctness.json'
            archive = root / 'inputs.tar.gz'
            archive.write_bytes(b'synthetic archived source snapshot')
            run_id = 'b' * 32
            snapshot = sha(archive)
            started = '2026-11-03T00:00:10+00:00'
            report = {'run_id': run_id, 'execution_started_utc': started,
                'finished_utc': '2026-11-03T00:00:20+00:00', 'input_archive_sha256': snapshot,
                'preparation_sha256': sha(stage / 'preparation.json'), 'inputs_sha256': {},
                'checkout': {'synthetic': 'checkout'}}
            correctness_dir = stage / 'correctness-evidence'
            evidence = json.loads(correctness_path.read_text())
            evidence.update(run_id=run_id, snapshot_sha256=snapshot,
                execution_started_utc=started, started_utc='2026-11-03T00:00:11+00:00',
                finished_utc='2026-11-03T00:00:12+00:00')
            for receipt_path in correctness_dir.rglob('*.status.json'):
                receipt = json.loads(receipt_path.read_text())
                receipt.update(run_id=run_id, snapshot_sha256=snapshot,
                    started_utc='2026-11-03T00:00:11.500000+00:00',
                    finished_utc='2026-11-03T00:00:11.750000+00:00')
                receipt['command'] = [item if item == str(fixture.tool) else item.replace(str(fixture.stage), str(stage))
                    for item in receipt['command']]
                receipt['cwd'] = receipt['cwd'].replace(str(fixture.stage), str(stage))
                write(receipt_path, receipt)
            evidence['artifacts_sha256'] = {path.relative_to(correctness_dir).as_posix(): sha(path)
                for path in correctness_dir.rglob('*') if path.is_file() and path.name != 'correctness.json'}
            write(correctness_path, evidence)
            with patch('ci.checkout_identity', return_value=report['checkout']):
                self.assertIsNotNone(_fresh_complete_correctness(root, report))
                evidence['status'] = 'running'
                write(correctness_path, evidence)
                self.assertIsNone(_fresh_complete_correctness(root, report))

    @unittest.skipUnless(sys.platform == 'linux', 'Workflow retention regression executes native bash')
    def test_portable_failure_keeps_raw_logs_and_original_status_without_precreating_ci_output(self):
        workflow = (Path(__file__).resolve().parents[2] / '.github/workflows/toom4-composition-proof.yml').read_text()
        block = workflow.split('      - name: Run portable tests and retain both exit statuses\n', 1)[1]
        block = block.split('      - name: Freeze exact checkout and prepared inputs\n', 1)[0]
        script = '\n'.join(line[10:] for line in block.split('        run: |\n', 1)[1].splitlines())
        self.assertIn('if: always()', workflow)
        self.assertRegex(workflow, r'path: \|\n\s+results/toom4-composition-portable/\n\s+results/toom4-composition-ci/')
        for ci_code, correctness_code in [(13, 17), (0, 17), (0, 0)]:
            with self.subTest(ci_code=ci_code, correctness_code=correctness_code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shim = root / 'python3'
                shim.write_text('#!' + sys.executable + '\nimport sys\n'
                    'print("raw stdout " + sys.argv[1])\nprint("raw stderr " + sys.argv[1], file=sys.stderr)\n'
                    f'raise SystemExit({ci_code} if sys.argv[1].endswith("/ci_test.py") else {correctness_code})\n')
                shim.chmod(0o755)
                result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], cwd=root,
                    env=dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH']), capture_output=True, timeout=10)
                self.assertEqual(result.returncode, ci_code or correctness_code, result.stderr)
                self.assertFalse((root / 'results/toom4-composition-ci').exists())
                logs = root / 'results/toom4-composition-portable'
                for suite, code in [('ci', ci_code), ('correctness', correctness_code)]:
                    self.assertEqual((logs / (suite + '.exit-status')).read_text(), str(code) + '\n')
                    self.assertEqual((logs / (suite + '.stdout.log')).read_text(),
                        'raw stdout experiments/toom4-composition/' + suite + '_test.py\n')
                    self.assertEqual((logs / (suite + '.stderr.log')).read_text(),
                        'raw stderr experiments/toom4-composition/' + suite + '_test.py\n')

    def test_timeout_preserves_partial_output_and_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(subprocess.TimeoutExpired):
                checked([sys.executable, '-c', "import time; print('partial output', flush=True); time.sleep(10)"],
                    root / 'timeout.log', root, timeout=0.5)
            self.assertIn('partial output', (root / 'timeout.log').read_text())
            self.assertIn('not a verification result', (root / 'timeout.log').read_text())

    def test_subprocess_failure_keeps_raw_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, 'Command failed'):
                command([sys.executable, '-c', "print('failed child output'); raise SystemExit(3)"], root / 'child.log')
            self.assertIn('failed child output', (root / 'child.log').read_text())


class StdlibSelectTests(unittest.TestCase):
    def test_fresh_import_and_posix_selector_from_experiment_directory(self):
        program = r'''
from pathlib import Path
import inspect
import json
import select
import selectors
import socket
import sys
import types

assert inspect.isbuiltin(select.select), 'Experiment code shadows stdlib select.select'
origin = getattr(select, '__file__', None)
assert origin is None or not Path(origin).resolve().is_relative_to(Path.cwd().resolve())
# Execute the installed stdlib's POSIX branch on Windows as well as Linux.
posix = types.ModuleType('composition_posix_selectors')
original_platform = sys.platform
try:
    sys.platform = 'linux'
    exec(compile(Path(selectors.__file__).read_text(encoding='utf-8'),
        selectors.__file__, 'exec'), posix.__dict__)
finally:
    sys.platform = original_platform
reader, writer = socket.socketpair()
with reader, writer, posix.SelectSelector() as selector:
    selector.register(reader, posix.EVENT_READ, 'ready')
    writer.sendall(b'x')
    events = selector.select(timeout=1)
    assert len(events) == 1 and events[0][0].data == 'ready'
    assert events[0][1] == posix.EVENT_READ and reader.recv(1) == b'x'
print(json.dumps({'select_origin': origin, 'posix_selector': 'pass'}))
'''
        result = subprocess.run([sys.executable, '-c', program],
            cwd=Path(__file__).resolve().parent, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['posix_selector'], 'pass')


if __name__ == '__main__':
    unittest.main()

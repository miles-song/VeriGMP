"""Portable CI-binding rejection tests with synthetic files; no arithmetic execution."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from ci import command, validate_results
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

    def save_build(self):
        write(self.stage / 'build-evidence/build.json', self.build)
        self.binding['build_gate_sha256'] = sha(self.stage / 'build-evidence/build.json')
        self.save_binding()

    def save_binding(self):
        write(self.directory / 'binding.json', self.binding)
        self.audit['binding_sha256'] = sha(self.directory / 'binding.json')
        write(self.directory / 'codegen-audit.json', self.audit)

    def test_consistent_synthetic_receipts(self):
        self.assertEqual(len(validate_results(self.stage)), 3)

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

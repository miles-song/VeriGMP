"""Portable correctness-boundary tests; synthetic receipts are not arithmetic proofs."""
from pathlib import Path
import json
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from common import strict_mutant
from common import sha, write
from correctness import (ProcessCleanupError, _linux_owned_processes, capture, check_variant_context, compile_runner, invalid_rejected,
    mutation_bytes, mutation_registry, positive_verification, remaining_timeout, run_mutations, run_oracles)

CLASSIFIER_FIXTURE_SHA256 = {
    'inherited-boundary-probes.json': '7490088839c23ac6c856047f4aac0406bbfa6e721ba928a38b487209b90a973f',
    'old-classifier-offline-probes.json': '6c9d7338aa8ba77c5d8c7fef3df14f032d5390a44e4d39d41fc3b8f4d7fdb5ca',
    'report.json': '562815c91b638d811c48d64f8b22866669ad63e906e3e5c956545b80b29eb802',
}


class SemanticGateTests(unittest.TestCase):
    def test_real_archived_semantic_diagnostics(self):
        archive = Path(__file__).resolve().parent.parent / 'toom4-signed-eval/evidence'
        for name in ['drop_evaluation_carry', 'wrong_cubic_exact_divisor', 'signed_drop_negation_borrow']:
            with self.subTest(name=name):
                result = subprocess.CompletedProcess([], 1, (archive / (name + '.log')).read_text(), '')
                self.assertTrue(strict_mutant(result))

    def test_all_registered_archived_mutation_diagnostics(self):
        root = Path(__file__).resolve().parents[2]
        archive = root / 'experiments/toom4-signed-eval/evidence'
        mutations = json.loads((archive.parent / 'mutations.json').read_text())
        for row in mutations:
            name = row[1]
            with self.subTest(name=name):
                result = subprocess.CompletedProcess([], 1, (archive / (name + '.log')).read_text(), '')
                self.assertTrue(strict_mutant(result))

    def test_frozen_root_classifier_probes(self):
        fixtures = Path(__file__).with_name('test-data') / 'classifier'
        for name, digest in CLASSIFIER_FIXTURE_SHA256.items():
            path = fixtures / name
            with self.subTest(fixture=name):
                self.assertTrue(path.is_file(), 'required classifier fixture is missing')
                self.assertEqual(sha(path), digest, 'classifier fixture differs from the reviewed snapshot')
        probe_paths = [
            fixtures / 'old-classifier-offline-probes.json',
            fixtures / 'report.json',
            fixtures / 'inherited-boundary-probes.json',
        ]
        root_cases = {case.get('case', case.get('id')): case for case in json.loads(
            probe_paths[0].read_text())['cases']}
        for path in probe_paths:
            probe = json.loads(path.read_text())
            for case in probe['cases']:
                fixture = root_cases.get(case.get('case'), case)
                if 'stdout' not in fixture or 'stderr' not in fixture:
                    with self.subTest(probe=path.name, case=case.get('case', case.get('id'))):
                        self.assertEqual(case.get('matches_expected'),
                            case.get('current_result') == case.get('expected'))
                        expected = case.get('expected')
                        replay_fixture = root_cases.get(case.get('case'))
                        self.assertIsNotNone(replay_fixture)
                        result = subprocess.CompletedProcess([], replay_fixture.get('returncode', 1),
                            replay_fixture['stdout'], replay_fixture['stderr'])
                        self.assertEqual(strict_mutant(result), expected)
                    continue
                expected = case.get('expected') if path == probe_paths[2] else case.get(
                    'safe_new_design_expected', case.get('expected'))
                result = subprocess.CompletedProcess([], fixture.get('returncode', 1),
                    fixture['stdout'], fixture['stderr'])
                with self.subTest(probe=path.name, case=case.get('case', case.get('id'))):
                    self.assertEqual(strict_mutant(result), expected)

    def test_diagnostics_can_be_split_between_complete_stream_lines(self):
        summary = 'verification results:: 4 verified, 1 errors (partial verification with `--verify-*`)\n'
        heading = 'error: invariant not satisfied at end of loop body\nerror: aborting due to 1 previous error\n'
        for stdout, stderr in [(summary + heading, ''), ('', summary + heading),
                (summary, heading), (heading, summary)]:
            with self.subTest(stdout=stdout, stderr=stderr):
                self.assertTrue(strict_mutant(subprocess.CompletedProcess([], 1, stdout, stderr)))
        split_at = summary.index('verified')
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
            summary[:split_at], summary[split_at:] + heading)))
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
            summary + 'error: postcondition not sat', 'isfied\n')))
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
            summary, summary + heading)))
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
            heading, 'Out of memory\n' + summary)))

    def test_crlf_is_allowed_bare_carriage_return_and_controls_are_not(self):
        text = ('verification results:: 0 verified, 1 errors\r\n'
            'error: assertion failed\r\n')
        self.assertTrue(strict_mutant(subprocess.CompletedProcess([], 1, text, '')))
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1, None, text)))
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1, text.encode(), '')))
        for extra in ['\r', '\x00', '\t', '\x1b[31m', '\u0085']:
            with self.subTest(extra=repr(extra)):
                self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
                    text + extra, '')))

    def test_summary_and_heading_boundaries_are_exact(self):
        semantic = 'error: postcondition not satisfied\n'
        summary = 'verification results:: 4 verified, 1 errors'
        exact = summary + ' (partial verification with `--verify-*`)\n'
        self.assertTrue(strict_mutant(subprocess.CompletedProcess([], 1, exact, semantic)))
        self.assertTrue(strict_mutant(subprocess.CompletedProcess([], 1, summary + '\n', semantic)))
        for malformed in [summary + ' INVALID_TRAILER\n',
                'verification results:: 04 verified, 1 errors\n',
                'verification results: 4 verified, 1 errors\n',
                'verification result:: 4 verified, 1 errors\n',
                summary + ' (partial verification with --verify-*)\n',
                summary + ' (partial verification with `--verify-*`) extra\n',
                'example quotation: ' + summary + '\n']:
            with self.subTest(malformed=malformed):
                self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1, malformed, semantic)))
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
            summary + '\nverification result:: 2 verified, 1 errors\n', semantic)))
        for heading in ['error:', 'error: postcondition not satisfied.',
                'error: assertion failed as quoted text',
                'error: unrelated problem; diagnostic includes assertion failed',
                'tool emitted error: unsupported diagnostic',
                'note: source says assertion failed', 'error[E0308]: mismatched types',
                'rustc: compiler error']:
            with self.subTest(heading=heading):
                self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1,
                    summary + '\n' + heading + '\n', '')))

    def test_mixed_tool_errors_and_abnormal_exit_never_pass(self):
        semantic = ('verification results:: 4 verified, 1 errors\n'
            'error: postcondition not satisfied\nerror: aborting due to 1 previous error\n')
        self.assertTrue(strict_mutant(subprocess.CompletedProcess([], 1, semantic, '')))
        for code, extra in [(0, ''), (2, ''), (-11, ''), (3221225477, ''), (True, ''), (1.0, ''),
                (1, 'error[E0308]: mismatched types\n'), (1, 'error: failed to read imported metadata\n'),
                (1, 'solver returned unknown\n'), (1, 'resource limit exceeded\n'),
                (1, 'Command timed out\n'), (1, 'verification results:: 5 verified, 0 errors\n')]:
            with self.subTest(code=code, extra=extra):
                self.assertFalse(strict_mutant(subprocess.CompletedProcess([], code, semantic, extra)))

    def test_resource_unknown_compiler_panic_and_malformed_mixes_never_pass(self):
        semantic = ('verification results:: 4 verified, 1 errors\n'
            'error: postcondition not satisfied\nerror: aborting due to 1 previous error\n')
        extras = [
            'memory allocation of 4096 bytes failed\n',
            'terminate called after throwing an instance of std::bad_alloc\n',
            'Cannot allocate memory\n',
            'Z3: allocation failed\n',
            'System.OutOfMemoryException: allocation failed\n',
            'rlimit exceeded\n',
            'Out of memory\n', 'OOM\n', 'fatal error: solver process failed\n',
            'Z3: unknown\n', 'solver returned unknown\n', 'resource limit exceeded\n',
            'Command timed out\n', 'error[E0308]: mismatched types\n',
            'error: arbitrary infrastructure failure\n',
            'killed by signal 9\n', "thread 'main' panicked at canary\n",
        ]
        for extra in extras:
            with self.subTest(extra=extra):
                self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1, semantic, extra)))
        duplicate = semantic + 'verification results:: 4 verified, 1 errors\n'
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1, duplicate, '')))

    def test_source_quotation_is_not_a_semantic_error(self):
        text = 'verification results:: 0 verified, 1 errors\nnote: source says assertion failed\n'
        self.assertFalse(strict_mutant(subprocess.CompletedProcess([], 1, text, '')))

    def test_compile_only_harness_does_not_require_positive_proof_items(self):
        result = subprocess.CompletedProcess([], 0, 'verification results:: 0 verified, 0 errors\n', '')
        self.assertEqual(positive_verification(result), 0)
        result.stdout += 'partial verification\n'
        with self.assertRaisesRegex(RuntimeError, 'complete verification'):
            positive_verification(result)

    def test_invalid_input_requires_its_explicit_validation_site(self):
        marker = 'COMPOSITION_HARNESS_REJECTED scratch_capacity\n'
        self.assertTrue(invalid_rejected(subprocess.CompletedProcess([], 2, '', marker), 'scratch_capacity'))
        for code, stdout, stderr in [(101, '', "thread 'main' panicked at canary\n"),
                (-11, '', marker), (2, '', marker + 'unexpected failure\n'),
                (2, '0\n', marker), (2, '', marker.replace('scratch_capacity', 'syntax'))]:
            with self.subTest(code=code, stdout=stdout, stderr=stderr):
                self.assertFalse(invalid_rejected(subprocess.CompletedProcess([], code, stdout, stderr), 'scratch_capacity'))

    def test_exhausted_budget_cannot_skip_a_pending_command(self):
        with self.assertRaisesRegex(RuntimeError, 'pending checks are incomplete'):
            remaining_timeout(time.monotonic() - 1, 300)


class RegistryTests(unittest.TestCase):
    def test_missing_or_duplicate_expected_anchor_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'native/verified/toom4_interpolate.rs'
            source.parent.mkdir(parents=True)
            rows = [['toom4_interpolate.rs', 'wrong_linear_exact_divisor',
                'divide_exact(ph,15)', 'divide_exact(ph,5)', 'toom4_interpolate']]
            source.write_text('crate::odd_division::divide_exact_odd(ph,15);\n')
            registered = mutation_registry(root, ['odd'], rows)[0]
            self.assertTrue(registered['applicable'])
            self.assertEqual(registered['before'], 'divide_exact_odd(ph,15)')
            self.assertEqual(registered['after'], 'divide_exact_odd(ph,5)')
            for contents in ['', 'divide_exact_odd(ph,15);divide_exact_odd(ph,15);']:
                source.write_text(contents)
                with self.assertRaisesRegex(RuntimeError, 'anchor mismatch'):
                    mutation_registry(root, ['odd'], rows)

    def test_inapplicable_feature_is_declared_independently_of_anchor_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'native/verified/toom4_interpolate.rs'
            source.parent.mkdir(parents=True)
            rows = [['toom4_interpolate.rs', 'fusion_wrong_half_constant',
                'sub_scaled_exact(pmh,z0,64)', 'sub_scaled_exact(pmh,z0,63)', 'toom4_interpolate']]
            source.write_text('toom_words::scale_exact(scratch,64);\n')
            registered = mutation_registry(root, [], rows)[0]
            self.assertFalse(registered['applicable'])
            self.assertEqual(registered['expected_matches'], 0)
            with self.assertRaisesRegex(RuntimeError, 'anchor mismatch'):
                mutation_registry(root, ['fusion'], rows)
            source.write_text('sub_scaled_exact(pmh,z0,64);\n')
            with self.assertRaisesRegex(RuntimeError, 'anchor mismatch'):
                mutation_registry(root, [], rows)


class RawSpanTests(unittest.TestCase):
    def test_lf_crlf_multiline_insertion_and_deletion_preserve_outside_bytes(self):
        for newline in [b'\n', b'\r\n']:
            for before, after in [('one', 'changed'), ('one\ntwo', 'changed\nthree'),
                    ('one\ntwo', ''), ('one', 'changed\nthree')]:
                with self.subTest(newline=newline, before=before, after=after):
                    prefix, suffix = b'\xff untouched\x00' + newline, newline + b'outside\r\x00'
                    old = before.encode().replace(b'\n', newline)
                    new = after.encode().replace(b'\n', newline)
                    original = prefix + old + suffix
                    mutated, span = mutation_bytes(original, before, after)
                    self.assertEqual(mutated, prefix + new + suffix)
                    self.assertEqual(span, {'offset': len(prefix), 'before_hex': old.hex(), 'after_hex': new.hex()})

    def test_missing_duplicate_overlapping_and_cross_newline_anchors_fail_closed(self):
        for original, before in [(b'absent', 'one'), (b'one one', 'one'),
                (b'aaa', 'aa'), (b'one\ntwo\none\r\ntwo', 'one\ntwo')]:
            with self.subTest(original=original, before=before):
                with self.assertRaisesRegex(RuntimeError, 'raw anchor mismatch'):
                    mutation_bytes(original, before, 'changed')

    def test_invalid_span_and_ambiguous_inserted_newline_fail_closed(self):
        for before, after in [('', 'new'), ('one', 'one'), ('one\r\ntwo', 'new')]:
            with self.subTest(before=before, after=after):
                with self.assertRaisesRegex(RuntimeError, 'Invalid registered'):
                    mutation_bytes(b'one\r\ntwo', before, after)
        with self.assertRaisesRegex(RuntimeError, 'Ambiguous mutation replacement newline'):
            mutation_bytes(b'one\r\nother\n', 'one', 'new\nline')


class MutationFixture:
    def __init__(self, test, newline=b'\r\n'):
        temporary = tempfile.TemporaryDirectory()
        test.addCleanup(temporary.cleanup)
        self.stage = Path(temporary.name).resolve()
        self.source = self.stage / 'entry/native/lib.rs'
        self.source.parent.mkdir(parents=True)
        self.original = b'// original statement' + newline + b'// retain outside' + newline
        self.source.write_bytes(self.original)
        self.peer = self.source.with_name('peer.rs')
        self.peer.write_bytes(b'// full-context sibling\r\n')
        self.tool = self.stage / 'synthetic-tool'
        self.tool.write_bytes(b'Synthetic non-executable tool; no compiler is run')
        self.out = self.stage / 'correctness-evidence'
        self.runner = self.out / 'entry/runner'
        self.runner.parent.mkdir(parents=True)
        self.runner.write_bytes(b'synthetic runner')
        libdir = self.stage / 'build-evidence/entry'
        libdir.mkdir(parents=True)
        self.pair = [libdir / 'libentry.rlib', libdir / 'entry.vir']
        for path in [*self.pair, libdir / 'default-runner']:
            path.write_bytes(b'synthetic pair/default runner ' + path.name.encode())
        write(self.stage / 'policy.json', {'modes': ['entry']})
        inputs = self.stage / 'correctness-inputs'
        inputs.mkdir()
        write(inputs / 'manifest.json', {'synthetic_fixture': True})
        self.prepared = {'variants': {'entry': {'native/lib.rs': sha(self.source), 'native/peer.rs': sha(self.peer)}},
            'policy_sha256': sha(self.stage / 'policy.json'), 'infrastructure_sha256': {},
            'correctness_inputs_sha256': {'correctness-inputs/manifest.json': sha(inputs / 'manifest.json')}}
        write(self.stage / 'preparation.json', self.prepared)
        library = {'verified_items': 1, 'rlib': sha(self.pair[0]), 'vir': sha(self.pair[1])}
        build = {'status': 'pass', 'benchmark_run': False, 'source_sha256': self.prepared['variants'],
            'libraries': {'entry': library}, 'default_oracles': {'entry': {'cases': 1,
                'runner_sha256': sha(libdir / 'default-runner')}}, 'infrastructure_sha256': {},
            'preparation_sha256': sha(self.stage / 'preparation.json'),
            'toolchain': {'sha256': {str(self.tool): sha(self.tool)}}}
        write(self.stage / 'build-evidence/build.json', build)
        self.record = {'paired_library': library, 'runner_sha256': sha(self.runner)}
        self.report = {'source_sha256': self.prepared['variants'], 'mutation_commands_started': 0,
            'pending_mutations': ['entry/flip'], 'preparation_sha256': sha(self.stage / 'preparation.json'),
            'build_gate_sha256': sha(self.stage / 'build-evidence/build.json'),
            'input_manifest_sha256': sha(inputs / 'manifest.json'), 'toolchain': build['toolchain'],
            'verifier': str(self.tool), 'variants': {'entry': self.record}}
        self.registry = [{'name': 'flip', 'file': 'native/lib.rs', 'module': 'example',
            'applicable': True, 'reason': None, 'source_sha256': sha(self.source),
            'before': 'original', 'after': 'incorrect'}]
        self.copy = self.out / 'mutation-sources/entry/native/lib.rs'

    def save(self):
        write(self.out / 'correctness.json', self.report)

    def run(self, deadline=None):
        run_mutations(self.stage, 'entry', self.registry, self.tool, self.out, self.record,
            self.report, self.save, time.monotonic() + 10 if deadline is None else deadline)


class MutationExecutionTests(unittest.TestCase):
    def semantic(self, *args, **kwargs):
        return subprocess.CompletedProcess([], 1,
            'verification results:: 1 verified, 1 errors\nerror: postcondition not satisfied\n', '')

    def assert_restored_pending(self, fixture):
        self.assertEqual(fixture.copy.read_bytes(), fixture.original)
        self.assertEqual(fixture.report['pending_mutations'], ['entry/flip'])
        self.assertNotEqual(fixture.record['mutations']['flip']['status'], 'pass')

    def test_mutant_launch_failure_restores_fresh_copy_and_leaves_library_source_untouched(self):
        f = MutationFixture(self)
        with self.assertRaisesRegex(RuntimeError, 'launch_error'):
            f.run()
        self.assert_restored_pending(f)
        self.assertEqual(f.source.read_bytes(), f.original)
        self.assertEqual(f.record['mutations']['flip']['source_restored_sha256'], sha(f.source))
        self.assertEqual(json.loads((f.out / 'entry/mutations/flip.status.json').read_text())['status'], 'launch_error')

    def test_success_observes_only_declared_raw_span_and_clears_pending_after_restoration(self):
        for newline in [b'\n', b'\r\n']:
            with self.subTest(newline=newline):
                f = MutationFixture(self, newline)
                mutated = f.original.replace(b'original', b'incorrect', 1)
                def observe(*args, **kwargs):
                    self.assertEqual(f.copy.read_bytes(), mutated)
                    self.assertEqual(f.source.read_bytes(), f.original)
                    self.assertEqual(f.copy.with_name('peer.rs').read_bytes(), f.peer.read_bytes())
                    self.assertEqual(f.report['pending_mutations'], ['entry/flip'])
                    self.assertEqual(f.record['mutations']['flip']['status'], 'running')
                    return self.semantic()
                with patch('correctness.capture', side_effect=observe) as mocked:
                    f.run()
                mocked.assert_called_once()
                self.assertEqual(f.copy.read_bytes(), f.original)
                self.assertEqual(f.report['pending_mutations'], [])
                item = f.record['mutations']['flip']
                self.assertEqual(item['status'], 'pass')
                self.assertEqual(item['mutated_source_sha256'], hashlib.sha256(mutated).hexdigest())
                self.assertEqual(item['source_before_sha256'], item['source_restored_sha256'])
                self.assertEqual(item['byte_span'], {'offset': 3, 'before_hex': b'original'.hex(), 'after_hex': b'incorrect'.hex()})

    def test_capture_exception_and_nonsemantic_result_restore_and_remain_pending(self):
        for failure in [RuntimeError('timeout fixture'), RuntimeError('decode fixture'),
                subprocess.CompletedProcess([], 1, 'error[E0308]: mismatched types\n', '')]:
            with self.subTest(failure=failure):
                f = MutationFixture(self)
                with patch('correctness.capture', side_effect=failure if isinstance(failure, Exception) else None,
                        return_value=failure), self.assertRaises(RuntimeError):
                    f.run()
                self.assert_restored_pending(f)

    def test_incomplete_process_cleanup_retains_mutant_copy_and_pending_id(self):
        f = MutationFixture(self)
        with patch('correctness.capture', side_effect=ProcessCleanupError('cleanup failed')):
            with self.assertRaisesRegex(ProcessCleanupError, 'Mutation copy retained'):
                f.run()
        self.assertEqual(f.copy.read_bytes(), f.original.replace(b'original', b'incorrect', 1))
        self.assertEqual(f.source.read_bytes(), f.original)
        self.assertEqual(f.report['pending_mutations'], ['entry/flip'])
        self.assertEqual(f.record['mutations']['flip']['status'], 'error')

    def test_context_drift_before_capture_blocks_invocation(self):
        for target in ['tool', 'source', 'pair', 'copy']:
            with self.subTest(target=target):
                f = MutationFixture(self)
                saved, injected = f.save, False
                def save():
                    nonlocal injected
                    saved()
                    if not injected and f.record['mutations']['flip']['status'] == 'running':
                        injected = True
                        path = {'tool': f.tool, 'source': f.source, 'pair': f.pair[0], 'copy': f.copy}[target]
                        path.write_bytes(path.read_bytes() + b'drift')
                with patch.object(f, 'save', side_effect=save), patch('correctness.capture') as mocked:
                    # Keep the real checkpoint writer; only inject one pre-command drift.
                    with self.assertRaises(RuntimeError):
                        f.run()
                mocked.assert_not_called()
                self.assert_restored_pending(f)

    def test_full_context_drift_is_checked_after_success_and_exception(self):
        for target in ['source', 'peer', 'source_extra', 'tool', 'rlib', 'vir', 'runner', 'build', 'manifest',
                'copy_peer', 'copy_extra', 'copy_missing', 'copy_outside_span']:
            for raises in [False, True]:
                with self.subTest(target=target, raises=raises):
                    f = MutationFixture(self)
                    def drift(*args, **kwargs):
                        paths = {'source': f.source, 'peer': f.peer, 'source_extra': f.source.with_name('extra.rs'), 'tool': f.tool,
                            'rlib': f.pair[0], 'vir': f.pair[1], 'runner': f.runner,
                            'build': f.stage / 'build-evidence/build.json',
                            'manifest': f.stage / 'correctness-inputs/manifest.json',
                            'copy_peer': f.copy.with_name('peer.rs'), 'copy_extra': f.copy.with_name('extra.rs'),
                            'copy_missing': f.copy.with_name('peer.rs'), 'copy_outside_span': f.copy}
                        if target == 'copy_missing':
                            paths[target].unlink()
                        else:
                            paths[target].write_bytes(b'changed context')
                        if raises:
                            raise RuntimeError('capture failure plus identity drift')
                        return self.semantic()
                    with patch('correctness.capture', side_effect=drift), self.assertRaises(RuntimeError):
                        f.run()
                    self.assert_restored_pending(f)

    def test_partial_mutation_write_and_artifact_failure_restore_original(self):
        for target in ['source', 'artifact']:
            with self.subTest(target=target):
                f = MutationFixture(self)
                write_bytes = Path.write_bytes
                def fail_write(path, data):
                    if (target == 'source' and path == f.copy and data != f.original
                            or target == 'artifact' and path == f.out / 'entry/mutations/flip.rs'):
                        write_bytes(path, data[:4])
                        raise OSError('partial write fixture')
                    return write_bytes(path, data)
                with patch('correctness.capture') as mocked, patch.object(Path, 'write_bytes', fail_write):
                    with self.assertRaisesRegex(OSError, 'partial write fixture'):
                        f.run()
                mocked.assert_not_called()
                self.assert_restored_pending(f)

    def test_failed_or_corrupt_restoration_cannot_mark_pass(self):
        for corrupt in [False, True]:
            with self.subTest(corrupt=corrupt):
                f = MutationFixture(self)
                write_bytes = Path.write_bytes
                def fail_restore(path, data):
                    if path == f.copy and data == f.original:
                        if not corrupt:
                            raise OSError('restore failure fixture')
                        data += b'corrupt restoration'
                    return write_bytes(path, data)
                with patch('correctness.capture', side_effect=self.semantic), patch.object(Path, 'write_bytes', fail_restore):
                    with self.assertRaises((RuntimeError, OSError)):
                        f.run()
                self.assertEqual(f.report['pending_mutations'], ['entry/flip'])
                item = f.record['mutations']['flip']
                self.assertEqual(item['status'], 'error')
                self.assertIn('restoration_error', item)

    def test_budget_exhaustion_leaves_original_copy_and_pending(self):
        f = MutationFixture(self)
        with patch('correctness.capture') as mocked, self.assertRaisesRegex(RuntimeError, 'pending checks are incomplete'):
            f.run(deadline=time.monotonic() - 1)
        mocked.assert_not_called()
        self.assert_restored_pending(f)


class OracleExecutionTests(unittest.TestCase):
    def fixture(self):
        from ci_test import EvidenceBindingTests
        f = EvidenceBindingTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.record = f.correctness['variants']['entry']
        f.runner = f.correctness_dir / 'entry/runner'
        f.correctness['pending_oracles'] = ['entry/' + name for name in f.manifest['suites']]
        f.check = lambda: check_variant_context(f.stage, 'entry', f.tool, f.correctness_dir,
            f.record, f.correctness)
        def completed(name):
            f.correctness['pending_oracles'].remove('entry/' + name)
        f.run = lambda: run_oracles(f.stage, f.runner.parent, f.runner, f.manifest,
            f.record, f.save_correctness, f.check, time.monotonic() + 30, completed)
        return f

    def result(self, command, prefix, *args, **kwargs):
        if prefix.name == 'tiny':
            return subprocess.CompletedProcess([], 0, '7\n', '')
        return subprocess.CompletedProcess([], 2, '', 'COMPOSITION_HARNESS_REJECTED syntax\n')

    def targets(self, f):
        return {'runner': f.runner, 'source': f.stage / 'entry/native/lib.rs',
            'source_extra': f.stage / 'entry/native/extra.rs', 'tool': f.tool,
            'rlib': f.stage / 'build-evidence/entry/libentry.rlib',
            'vir': f.stage / 'build-evidence/entry/entry.vir',
            'runner_source': f.inputs / 'runner.rs', 'commands': f.inputs / 'tiny.commands',
            'answers': f.inputs / 'bad.answers', 'manifest': f.inputs / 'manifest.json',
            'prepared': f.stage / 'preparation.json', 'build': f.stage / 'build-evidence/build.json'}

    def test_root_runner_swap_between_suites_is_stopped_before_second_invocation(self):
        f = self.fixture()
        original, observed = f.runner.read_bytes(), []
        def swap(*args, **kwargs):
            observed.append(sha(f.runner))
            f.runner.write_bytes(b'wrong runner between suites' if len(observed) == 1 else original)
            return self.result(*args, **kwargs)
        with patch('correctness.capture', side_effect=swap), self.assertRaisesRegex(RuntimeError, 'Identity changed'):
            f.run()
        self.assertEqual(len(observed), 1)
        self.assertEqual(f.correctness['pending_oracles'], ['entry/tiny', 'entry/bad'])
        self.assertEqual(f.record['oracles']['tiny']['status'], 'error')
        self.assertNotIn('bad', f.record['oracles'])

    def test_every_oracle_checks_full_context_before_and_after_even_on_exception(self):
        for suite in ['tiny', 'bad-0']:
            for target in [*self.targets(self.fixture()), 'line']:
                if target == 'line' and suite == 'tiny':
                    continue
                for raises in [False, True]:
                    with self.subTest(suite=suite, target=target, raises=raises):
                        f = self.fixture()
                        def drift(command, prefix, *args, **kwargs):
                            if prefix.name == suite:
                                path = (kwargs['stdin'] if target == 'line' else self.targets(f)[target])
                                path.write_bytes(b'changed consuming context')
                                if raises:
                                    raise RuntimeError('capture exception plus drift')
                            return self.result(command, prefix, *args, **kwargs)
                        with patch('correctness.capture', side_effect=drift), self.assertRaises(RuntimeError):
                            f.run()
                        pending = ['entry/tiny', 'entry/bad'] if suite == 'tiny' else ['entry/bad']
                        self.assertEqual(f.correctness['pending_oracles'], pending)
                        self.assertEqual(f.record['oracles']['tiny' if suite == 'tiny' else 'bad']['status'], 'error')
        for target in self.targets(self.fixture()):
            with self.subTest(before=target):
                f = self.fixture()
                self.targets(f)[target].write_bytes(b'drift before command')
                with patch('correctness.capture') as mocked, self.assertRaises(RuntimeError):
                    f.run()
                mocked.assert_not_called()
                self.assertEqual(f.correctness['pending_oracles'], ['entry/tiny', 'entry/bad'])

    def test_oracle_success_clears_pending_only_after_post_check(self):
        f = self.fixture()
        events = []
        check = f.check
        def context():
            events.append('check')
            check()
        def consume(*args, **kwargs):
            events.append('capture')
            self.assertIn('entry/tiny' if args[1].name == 'tiny' else 'entry/bad', f.correctness['pending_oracles'])
            return self.result(*args, **kwargs)
        f.check = context
        with patch('correctness.capture', side_effect=consume):
            f.run()
        self.assertEqual(events, ['check', 'capture', 'check', 'check', 'check', 'capture', 'check'])
        self.assertEqual(f.correctness['pending_oracles'], [])

    def test_compile_checks_context_before_and_after_even_on_exception(self):
        for target in self.targets(self.fixture()):
            if target == 'runner':
                continue  # This executable is the new compile output, not a pre-existing input.
            for phase in ['before', 'after', 'exception']:
                with self.subTest(target=target, phase=phase):
                    f = self.fixture()
                    f.runner.unlink()
                    del f.record['runner_sha256']
                    def consume(*args, **kwargs):
                        f.runner.write_bytes(b'new synthetic compiled runner')
                        self.targets(f)[target].write_bytes(b'compile context drift')
                        if phase == 'exception':
                            raise RuntimeError('compile capture exception plus drift')
                        return subprocess.CompletedProcess([], 0, 'verification results:: 0 verified, 0 errors\n', '')
                    if phase == 'before':
                        self.targets(f)[target].write_bytes(b'compile input drift')
                    with patch('correctness.capture', side_effect=consume) as mocked, self.assertRaises(RuntimeError):
                        compile_runner(f.stage, 'entry', f.tool, f.correctness_dir, f.record, f.correctness,
                            time.monotonic() + 30)
                    self.assertEqual(mocked.call_count, 0 if phase == 'before' else 1)
                    self.assertEqual(f.record['status'], 'error')
                    self.assertEqual(f.correctness['pending_oracles'], ['entry/tiny', 'entry/bad'])


class RawReceiptValidationTests(unittest.TestCase):
    def fixture(self):
        from ci_test import EvidenceBindingTests
        fixture = EvidenceBindingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_missing_or_forged_raw_span_fails_receipt_validation(self):
        from correctness import validate_correctness
        for missing in [False, True]:
            with self.subTest(missing=missing):
                f = self.fixture()
                item = f.correctness['variants']['entry']['mutations']['real_vc']
                if missing:
                    del item['byte_span']
                else:
                    item['byte_span']['offset'] += 1
                f.save_correctness()
                with self.assertRaisesRegex(RuntimeError, 'Missing actual semantic VC failure'):
                    validate_correctness(f.stage, f.build)

    def test_crlf_receipts_validate_narrow_bytes_and_reject_normalized_artifact(self):
        from correctness import validate_correctness
        f = self.fixture()
        for name in f.names:
            source = f.stage / name / 'native/lib.rs'
            original = source.read_bytes().replace(b'\n', b'\r\n')
            source.write_bytes(original)
            f.prepared['variants'][name]['native/lib.rs'] = sha(source)
            f.build['source_sha256'][name]['native/lib.rs'] = sha(source)
            if name == 'baseline':
                continue
            row = f.manifest['mutation_registry'][name][0]
            row['source_sha256'] = sha(source)
            (f.correctness_dir / 'mutation-sources' / name / 'native/lib.rs').write_bytes(original)
            artifact = f.correctness_dir / name / 'mutations/real_vc.rs'
            artifact.write_bytes(original.replace(b'synthetic source', b'mutated source', 1))
            item = f.correctness['variants'][name]['mutations']['real_vc']
            item.update(source_before_sha256=sha(source), source_restored_sha256=sha(source),
                mutated_source_sha256=sha(artifact))
        write(f.inputs / 'manifest.json', f.manifest)
        f.prepared['correctness_inputs_sha256']['correctness-inputs/manifest.json'] = sha(f.inputs / 'manifest.json')
        write(f.stage / 'preparation.json', f.prepared)
        f.build['preparation_sha256'] = sha(f.stage / 'preparation.json')
        f.save_build()
        f.correctness.update(build_gate_sha256=sha(f.stage / 'build-evidence/build.json'),
            preparation_sha256=sha(f.stage / 'preparation.json'), input_manifest_sha256=sha(f.inputs / 'manifest.json'))
        f.save_correctness()
        self.assertEqual(validate_correctness(f.stage, f.build), sha(f.correctness_dir / 'correctness.json'))
        artifact = f.correctness_dir / 'entry/mutations/real_vc.rs'
        artifact.write_bytes(artifact.read_bytes().replace(b'\r\n', b'\n'))
        f.correctness['variants']['entry']['mutations']['real_vc']['mutated_source_sha256'] = sha(artifact)
        f.save_correctness()
        with self.assertRaisesRegex(RuntimeError, 'Identity changed'):
            validate_correctness(f.stage, f.build)


class RawEvidenceTests(unittest.TestCase):

    def test_owned_tree_inventory_tracks_adopted_and_reused_descendant_identities(self):
        records = {100: (1, 10), 101: (100, 11), 102: (99, 12),
            103: (99, 13), 104: (103, 50)}
        children = {1: [100], 100: [101], 99: [102, 103], 103: [104]}
        with patch('correctness.os.getpid', return_value=99), \
                patch('correctness._linux_proc_snapshot', return_value=(records, children)):
            observed, _ = _linux_owned_processes(100, 10, {100: 10, 104: 40}, {102: 12})
        self.assertEqual(observed, {100: 10, 101: 11, 103: 13, 104: 50})

    @unittest.skipUnless(sys.platform == 'linux', 'Correctness orchestration requires the Linux runtime')
    def test_cleanup_failure_does_not_finalize_matrix_artifact_hashes(self):
        from ci_test import EvidenceBindingTests
        from correctness import correctness
        f = EvidenceBindingTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.correctness_dir.rename(f.stage / 'previous-synthetic-correctness')
        def failed_cleanup(command, prefix, *args, **kwargs):
            write(Path(str(prefix) + '.status.json'), {'status': 'process_error',
                'pid': 123456789, 'process_ownership': 'linux_session_group', 'process_tree_quiescent': False})
            raise ProcessCleanupError('synthetic unconfirmed cleanup; no process launched')
        with patch.dict(os.environ, VERUS_BIN=str(f.tool)), patch('correctness.capture', side_effect=failed_cleanup):
            self.assertFalse(correctness(f.stage))
        report = json.loads((f.correctness_dir / 'correctness.json').read_text())
        self.assertEqual(report['status'], 'error')
        self.assertTrue(report['process_cleanup_incomplete'])
        self.assertEqual(report['artifacts_sha256'], {})
        self.assertEqual(report['pending_oracles'],
            [name + '/' + suite for name in f.names[1:] for suite in f.manifest['suites']])

    @unittest.skipUnless(sys.platform == 'linux', 'Cleanup-failure injection targets Linux group ownership')
    def test_incomplete_group_cleanup_never_finalizes_raw_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('correctness.subprocess.Popen') as spawn, patch('correctness.os.waitid'), \
                    patch('correctness.os.killpg', side_effect=OSError('injected group cleanup failure')):
                spawn.return_value.pid = 123456789  # Mock only: no real process is launched or signaled.
                spawn.return_value.returncode = 0
                spawn.return_value.wait.return_value = 0
                with self.assertRaises(ProcessCleanupError):
                    capture(['synthetic'], root / 'receipt', root)
            status = json.loads((root / 'receipt.status.json').read_text())
            self.assertEqual(status['status'], 'process_error')
            self.assertEqual(status['returncode'], 0)
            self.assertFalse(status['process_tree_quiescent'])
            self.assertNotIn('stdout_sha256', status)
            self.assertNotIn('stderr_sha256', status)

    @unittest.skipUnless(sys.platform == 'linux', 'Owned session/group reaping is a Linux runtime guarantee')
    def test_owned_descendants_cannot_write_after_timeout_completion_or_exception(self):
        import ctypes
        libc = ctypes.CDLL(None)
        subreaper = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0), 0)
        original_subreaper = subreaper.value
        for mode in ['timeout', 'completed', 'exception']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                child = ("from pathlib import Path; import os,time; os.setsid(); root=Path(" + repr(str(root)) + "); "
                    "(root/'started').write_text(str(os.getpid())); print('child started',flush=True); "
                    "time.sleep(1.2); (root/'late').write_text('late write'); print('late output',flush=True)")
                parent = ("import subprocess,sys,time; from pathlib import Path; "
                    "subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); "
                    "root=Path(" + repr(str(root)) + ")\n"
                    "while not (root/'started').exists(): time.sleep(0.01)\n" +
                    ("time.sleep(10)" if mode != 'completed' else ""))
                unowned = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
                try:
                    if mode == 'exception':
                        waitid = os.waitid
                        def fail_wait(*args):
                            if (root / 'started').exists():
                                raise RuntimeError('injected wait exception')
                            return waitid(*args)
                        with patch('correctness.os.waitid', side_effect=fail_wait), self.assertRaisesRegex(RuntimeError, 'injected wait'):
                            capture([sys.executable, '-c', parent], root / 'receipt', root, timeout=0.5)
                    elif mode == 'timeout':
                        with self.assertRaisesRegex(RuntimeError, 'timeout'):
                            capture([sys.executable, '-c', parent], root / 'receipt', root, timeout=0.5)
                    else:
                        self.assertEqual(capture([sys.executable, '-c', parent], root / 'receipt', root, timeout=2).returncode, 0)
                    status = json.loads((root / 'receipt.status.json').read_text())
                    self.assertEqual(status['status'], 'process_error' if mode == 'exception' else mode)
                    self.assertEqual(status['process_ownership'], 'linux_session_group')
                    self.assertEqual(status['process_tracking'], 'linux_owned_descendant_tree')
                    self.assertTrue(status['process_tree_quiescent'])
                    self.assertEqual(status['descendants_reaped'], 1)
                    self.assertEqual(libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0), 0)
                    self.assertEqual(subreaper.value, original_subreaper)
                    child_pid = int((root / 'started').read_text())
                    with self.assertRaises(ChildProcessError):
                        os.waitpid(child_pid, os.WNOHANG)
                    time.sleep(1.3)
                    self.assertFalse((root / 'late').exists())
                    self.assertEqual(status['stdout_sha256'], sha(root / 'receipt.stdout.log'))
                    self.assertEqual(status['stderr_sha256'], sha(root / 'receipt.stderr.log'))
                    self.assertIsNone(unowned.poll())
                finally:
                    unowned.kill()
                    unowned.wait()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows portable capture reports direct-process ownership only')
    def test_windows_capture_does_not_claim_linux_tree_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture([sys.executable, '-c', 'pass'], root / 'receipt', root)
            status = json.loads((root / 'receipt.status.json').read_text())
            self.assertEqual(status['process_ownership'], 'direct_process_only')
            self.assertFalse(status['process_tree_quiescent'])

    def test_nonzero_and_timeout_retain_separate_unmodified_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, '-c',
                "import os; os.write(1,b'raw\\r\\nstdout'); os.write(2,b'raw stderr'); raise SystemExit(3)"]
            result = capture(command, root / 'failure', root)
            self.assertEqual(result.returncode, 3)
            self.assertEqual((root / 'failure.stdout.log').read_bytes(), b'raw\r\nstdout')
            self.assertEqual((root / 'failure.stderr.log').read_bytes(), b'raw stderr')
            with self.assertRaisesRegex(RuntimeError, 'timeout'):
                capture([sys.executable, '-c',
                    "import os,time; os.write(1,b'partial out'); os.write(2,b'partial err'); time.sleep(10)"],
                    root / 'timeout', root, timeout=0.5)
            self.assertEqual((root / 'timeout.stdout.log').read_bytes(), b'partial out')
            self.assertEqual((root / 'timeout.stderr.log').read_bytes(), b'partial err')
            status = json.loads((root / 'timeout.status.json').read_text())
            self.assertTrue(status['timed_out'])
            self.assertIsNone(status['returncode'])

    def test_launch_and_decode_failure_preserve_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, 'launch_error'):
                capture([root / 'no-such-executable'], root / 'launch', root)
            self.assertEqual(json.loads((root / 'launch.status.json').read_text())['status'], 'launch_error')
            with self.assertRaisesRegex(RuntimeError, 'Non-UTF-8'):
                capture([sys.executable, '-c', "import os; os.write(2,b'\\xff')"], root / 'decode', root)
            self.assertEqual((root / 'decode.stderr.log').read_bytes(), b'\xff')
            self.assertIn('decode_error', json.loads((root / 'decode.status.json').read_text()))


if __name__ == '__main__':
    unittest.main()

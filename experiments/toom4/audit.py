"""Audit archived source identities and recompute both complete timing matrices."""
from pathlib import Path
import csv
import hashlib
import json
import re
import statistics

HERE = Path(__file__).resolve().parent
BASE = 'e22a4dd00a28681fd27d68e2a78fa304cf17563e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Path leaves archive')
    return path


def read(relative):
    return json.loads(safe(HERE, relative).read_text())


def audit():
    index = read('index.json')
    publication = read('publication.json')
    files = publication['files']
    if index['baseline_commit'] != BASE or index['production_files_changed']:
        raise ValueError('Wrong baseline or promotion scope')
    for relative, entry in files.items():
        path = safe(HERE, relative)
        if sha(path) != entry['published_sha256']:
            raise ValueError('Published bytes changed: ' + relative)
        if entry['transform'] not in ['none', 'host_path_redaction']:
            raise ValueError('Unknown publication transform')
        if entry['transform'] == 'none' and entry['original_sha256'] != sha(path):
            raise ValueError('Original byte identity mismatch')
        if re.search(r'/mnt/[a-z]/|(?<![0-9a-zA-Z])[A-Za-z]:[\\/]|Users[/\\]+\d+', path.read_text()):
            raise ValueError('Host path in archive: ' + relative)
    verification = read('evidence/verification.json')
    if verification['status'] != 'pass' or not verification['identity_checks_before_after']:
        raise ValueError('Incomplete historical gate')
    original_gate = publication['historical_verification_original_sha256']
    if original_gate != files['evidence/verification.json']['original_sha256']:
        raise ValueError('Historical report identity mismatch')
    reconstruction = read('reconstruction-check.json')
    if reconstruction['status'] != 'exact_source_reconstructed' or reconstruction['baseline_commit'] != BASE or reconstruction['historical_original_gate_sha256'] != original_gate:
        raise ValueError('Reconstruction identity mismatch')
    if reconstruction['source_files'] != len(verification['source_sha256']) or reconstruction['fresh_verification_status'] != 'not_run' or reconstruction['fresh_benchmark_status'] != 'not_run':
        raise ValueError('Reconstruction scope mismatch')
    if verification['libraries']['baseline']['verified'] != index['baseline_library_proof_items']:
        raise ValueError('Baseline proof count mismatch')
    if verification['libraries']['candidate']['verified'] != index['library_proof_items'] or verification['verified_runner'] != index['library_proof_items']:
        raise ValueError('Candidate proof count mismatch')
    if verification['oracle']['cases'] != index['oracle_cases'] or verification['oracle']['direct_toom4_cases'] != index['new_oracle_cases']:
        raise ValueError('Oracle scope mismatch')
    if verification['invalid_commands_rejected'] != index['invalid_commands']:
        raise ValueError('Invalid-command count mismatch')
    if len(verification['mutations']) != index['semantic_mutants'] or not all(item['semantically_rejected'] for item in verification['mutations']):
        raise ValueError('Incomplete semantic mutation evidence')
    if not verification['codegen']['no_allocator_general_division_element_bounds_panic']:
        raise ValueError('Incomplete code generation gate')
    for required in ['toom4_multiply', 'toom4_square']:
        if not any(required in name for name in verification['codegen']['reachable_functions']):
            raise ValueError('Missing reachable forced kernel')
    if len(verification['source_sha256']) != index['source_snapshot_files']:
        raise ValueError('Source snapshot size mismatch')
    for item in index['changed_source_paths']:
        relative = 'candidate/' + item['path']
        if sha(HERE / 'overlay' / item['path']) != verification['source_sha256'][relative] or item['candidate_sha256'] != verification['source_sha256'][relative]:
            raise ValueError('Changed source overlay mismatch')
    for relative, digest in verification['source_sha256'].items():
        if '/' not in relative and sha(safe(HERE, relative)) != digest:
            raise ValueError('Historical checker source mismatch')
    if sha(HERE / 'candidate.patch') != index['source_patch_sha256']:
        raise ValueError('Source patch mismatch')
    window = read('evidence/confirmation-window.json')
    if window['status'] != 'pass' or window['tags'] != ['default1', 'default2'] or not window['benchmark_started']:
        raise ValueError('Incomplete confirmation window')
    summary = read('evidence/performance-summary.json')
    if summary['status'] != 'pass' or summary['verification_report_sha256'] != original_gate:
        raise ValueError('Unbound performance summary')
    if summary['confirmation_window_sha256'] != files['evidence/confirmation-window.json']['original_sha256']:
        raise ValueError('Unbound confirmation window')
    if summary['analysis_script_sha256'] != sha(HERE / 'summarize_confirmations.py'):
        raise ValueError('Analysis source mismatch')
    shapes = {(op, n, top) for op in [0, 1] for n, top in [(1, 1), (1, 64), (2, 1),
        *[(n, 63) for n in [23, 24, 25, 63, 64, 65, 127, 128, 129, 191, 192, 193, 255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 2048, 4096]]]}
    result = {'status': 'pass', 'scope': 'Archive integrity, not a fresh proof or benchmark run',
        'baseline_commit': BASE, 'mapped_artifacts': len(files), 'source_snapshot_files': len(verification['source_sha256']), 'runs': {}}
    for tag in ['default1', 'default2']:
        binding = read('evidence/' + tag + '-binding.json')
        measured = read('evidence/' + tag + '/measurements.json')
        raw = HERE / 'evidence' / tag / 'benchmark.csv'
        if binding['status'] != measured['status'] or binding['status'] != 'pass' or not binding['source_tool_artifact_checks_before_after']:
            raise ValueError('Incomplete measurement')
        if binding['verification_report_sha256'] != original_gate or binding['measurements_sha256'] != files['evidence/' + tag + '/measurements.json']['original_sha256']:
            raise ValueError('Measurement source/report binding mismatch')
        if binding['raw_sha256'] != sha(raw) or measured['raw_sha256'] != sha(raw):
            raise ValueError('Raw CSV binding mismatch')
        if window['bindings'][tag]['sha256'] != files['evidence/' + tag + '-binding.json']['original_sha256'] or window['bindings'][tag]['raw_sha256'] != sha(raw):
            raise ValueError('Confirmation binding mismatch')
        if measured['verified_library_identities'] != verification['libraries']:
            raise ValueError('Measured library mismatch')
        if measured['benchmark_binary_sha256'] != verification['benchmark_binary_sha256']:
            raise ValueError('Measured binary mismatch')
        if measured['benchmark_source_sha256'] != verification['benchmark_source_sha256'] or measured['benchmark_source_sha256'] != sha(HERE / 'compare.rs'):
            raise ValueError('Measured driver mismatch')
        # Historical /lib aliases and resolved /usr/lib targets have the same bytes.
        if sorted(measured['linked_library_sha256'].values()) != sorted(verification['runtime_library_sha256'].values()):
            raise ValueError('Measured runtime library mismatch')
        samples = list(csv.DictReader(raw.open(newline='')))
        groups = {}
        for row in samples:
            key = tuple(int(row[field]) for field in ['operation', 'limbs', 'top', 'mode'])
            groups.setdefault(key, []).append(row)
        if set(groups) != {(*shape, mode) for shape in shapes for mode in range(3)}:
            raise ValueError('Incomplete shape matrix')
        medians = {}
        for key, rows in groups.items():
            if len(rows) != 7 or {int(row['repetition']) for row in rows} != set(range(7)):
                raise ValueError('Incomplete repetitions')
            if any(int(row['iterations']) <= 0 or int(row['ns']) < 10_000_000 for row in rows):
                raise ValueError('Short measurement batch')
            medians[key] = statistics.median(int(row['ns']) / int(row['iterations']) for row in rows)
        if len(measured['measurements']) != 52 or {(row['operation'], row['limbs'], row['top']) for row in measured['measurements']} != shapes:
            raise ValueError('Incomplete measurement summary')
        summarized_run = next(run for run in summary['runs'] if run['tag'] == tag)
        summarized = {(0 if row['operation'] == 'mul_mod' else 1, row['limbs'], row['top']): row for row in summarized_run['comparisons']}
        if len(summarized_run['comparisons']) != 52 or set(summarized) != shapes:
            raise ValueError('Incomplete performance matrix')
        for row in measured['measurements']:
            key = row['operation'], row['limbs'], row['top']
            expected = {'baseline_ns': medians[*key, 0], 'candidate_ns': medians[*key, 1], 'gmp_ns': medians[*key, 2],
                'candidate_over_baseline': medians[*key, 1] / medians[*key, 0], 'candidate_over_gmp': medians[*key, 1] / medians[*key, 2]}
            if any(row[field] != value or summarized[key][field] != value for field, value in expected.items()):
                raise ValueError('Raw median/ratio mismatch')
        observed = {'samples': len(samples), 'minimum_recorded_ns': min(int(row['ns']) for row in samples),
            'regressions_vs_baseline': sum(row['candidate_over_baseline'] > 1 for row in measured['measurements']),
            'primary_gmp_failures': sum(row['candidate_over_gmp'] > 1 for row in measured['measurements'] if row['limbs'] in [256, 512, 1024, 2048, 4096] and row['top'] == 63),
            'key_gmp_failures': sum(row['candidate_over_gmp'] > 1.2 for row in measured['measurements']), 'raw_sha256': sha(raw)}
        observed['performance_status'] = 'target_not_met' if observed['primary_gmp_failures'] or observed['key_gmp_failures'] else 'registered_library_target_met'
        if any(index['runs'][tag][key] != value or summarized_run[key] != value for key, value in observed.items()):
            raise ValueError('Summary omits failures')
        result['runs'][tag] = observed
    result['registered_gmp_target_status'] = 'target_not_met' if any(run['performance_status'] == 'target_not_met' for run in result['runs'].values()) else 'registered_library_target_met'
    if index['registered_gmp_target_status'] != result['registered_gmp_target_status'] or summary['performance_status'] != result['registered_gmp_target_status']:
        raise ValueError('Incorrect performance acceptance status')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))

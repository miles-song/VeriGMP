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


def audit(require_preparation_record=True):
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
    if require_preparation_record:
        reconstruction = read('reconstruction-check.json')
        if reconstruction['status'] != 'exact_source_reconstructed' or reconstruction['baseline_commit'] != BASE or reconstruction['historical_original_gate_sha256'] != original_gate:
            raise ValueError('Reconstruction identity mismatch')
        if reconstruction['source_files'] != len(verification['source_sha256']) or reconstruction['fresh_verification_status'] != 'not_run' or reconstruction['fresh_benchmark_status'] != 'not_run':
            raise ValueError('Reconstruction scope mismatch')
    if verification['libraries']['baseline']['verified'] != index['baseline_library_proof_items']:
        raise ValueError('Baseline proof count mismatch')
    if verification['libraries']['previous']['verified'] != index['previous_library_proof_items']:
        raise ValueError('Previous-control proof count mismatch')
    if verification['libraries']['candidate']['verified'] != index['library_proof_items'] or verification['verified_runner'] != index['library_proof_items']:
        raise ValueError('Candidate proof count mismatch')
    if verification['oracle']['cases'] != index['oracle_cases'] or verification['oracle']['odd_division_cases'] != index['new_oracle_cases']:
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
        relative = item['side'] + '/' + item['path']
        if sha(HERE / 'overlay' / item['side'] / item['path']) != verification['source_sha256'][relative] or item['candidate_sha256'] != verification['source_sha256'][relative]:
            raise ValueError('Changed source overlay mismatch')
    for relative, digest in verification['source_sha256'].items():
        if '/' not in relative and sha(safe(HERE, relative)) != digest:
            raise ValueError('Historical checker source mismatch')
    for name, digest in index['source_patch_sha256'].items():
        if sha(HERE / name) != digest:
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
        ordered=[(1,1),(1,64),(2,1),*[(n,63) for n in [23,24,25,63,64,65,127,128,129,191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096]]]
        expected_order=[(op,n,top,rep,(j+rep)%4) for n,top in ordered for op in [0,1] for rep in range(7) for j in range(4)]
        if [tuple(int(row[f]) for f in ['operation','limbs','top','repetition','mode']) for row in samples]!=expected_order:
            raise ValueError('Recorded measurement order differs from registered rotation')

        groups = {}
        for row in samples:
            key = tuple(int(row[field]) for field in ['operation', 'limbs', 'top', 'mode'])
            groups.setdefault(key, []).append(row)
        if set(groups) != {(*shape, mode) for shape in shapes for mode in range(4)}:
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
            expected = {'baseline_ns': medians[*key, 0], 'previous_ns': medians[*key, 1], 'candidate_ns': medians[*key, 2], 'gmp_ns': medians[*key, 3],
                'candidate_over_baseline': medians[*key, 2] / medians[*key, 0],
                'candidate_over_previous': medians[*key, 2] / medians[*key, 1], 'candidate_over_gmp': medians[*key, 2] / medians[*key, 3]}
            if any(row[field] != value or summarized[key][field] != value for field, value in expected.items()):
                raise ValueError('Raw median/ratio mismatch')
        observed = {'samples': len(samples), 'minimum_recorded_ns': min(int(row['ns']) for row in samples),
            'regressions_vs_baseline': sum(row['candidate_over_baseline'] > 1 for row in measured['measurements']),
            'regressions_vs_previous': sum(row['candidate_over_previous'] > 1 for row in measured['measurements']),
            'primary_gmp_failures': sum(row['candidate_over_gmp'] > 1 for row in measured['measurements'] if row['limbs'] in [256, 512, 1024, 2048, 4096] and row['top'] == 63),
            'key_gmp_failures': sum(row['candidate_over_gmp'] > 1.2 for row in measured['measurements']), 'raw_sha256': sha(raw)}
        observed['performance_status'] = 'target_not_met' if observed['primary_gmp_failures'] or observed['key_gmp_failures'] else 'registered_library_target_met'
        if any(index['runs'][tag][key] != value or summarized_run[key] != value for key, value in observed.items()):
            raise ValueError('Summary omits failures')
        result['runs'][tag] = observed
    for name, item in verification['libraries'].items():
        log = safe(HERE, 'evidence/'+name+'-library.log').read_text()
        if re.findall(r'verification results:: (\d+) verified, (\d+) errors', log) != [(str(item['verified']), '0')]:
            raise ValueError('Positive proof log mismatch')
    for mutant in verification['mutations']:
        text = safe(HERE, 'evidence/'+mutant['name']+'.log').read_text()
        if not re.search(r'verification results:: \d+ verified, [1-9]\d* errors', text):
            raise ValueError('Missing failed verification obligation')
        if not any(term in text for term in ['requires not satisfied','precondition not satisfied','invariant not satisfied','postcondition not satisfied','assertion failed']):
            raise ValueError('Missing semantic rejection')
        if re.search(r'error\[E\d+\]|solver returned unknown|resource limit|timed out|timeout|could not compile|failed to load|panicked at|segmentation fault|internal compiler error', text, re.I):
            raise ValueError('Invalid proof rejection')
    for name in ['runner-build.log','codegen.log']:
        log=safe(HERE,'evidence/'+name).read_text()
        if re.findall(r'verification results:: (\d+) verified, (\d+) errors',log)!=[('289','0')] or 'partial verification' in log:
            raise ValueError('Runner/codegen positive log mismatch')
    if len(verification['legacy_entrypoints'])!=5:
        raise ValueError('Missing standalone entry compatibility')
    for name,item in verification['legacy_entrypoints'].items():
        log=safe(HERE,'evidence/legacy-'+name+'.log').read_text()
        if item['executed'] or item['verified']<=0 or re.findall(r'verification results:: (\d+) verified, (\d+) errors',log)!=[(str(item['verified']),'0')]:
            raise ValueError('Legacy entry compilation scope mismatch')
    from odd_codegen import inspect_odd
    if inspect_odd(safe(HERE,'evidence/codegen.s').read_text())!=verification['odd_codegen']:
        raise ValueError('Odd exact API codegen replay differs')
    if files['evidence/codegen.s']['original_sha256']!=verification['artifact_sha256']['codegen.s']:
        raise ValueError('Codegen source artifact mismatch')
    parent=read('parent-entry/verification.json')
    previous={p.removeprefix('previous/'):h for p,h in verification['source_sha256'].items() if p.startswith('previous/')}
    parent_candidate={p.removeprefix('candidate/'):h for p,h in parent['source_sha256'].items() if p.startswith('candidate/')}
    if previous!=parent_candidate:
        raise ValueError('Previous control differs from the frozen parent entry candidate')
    root=read('evidence/root-prebenchmark-audit.json')
    if root['status']!='pass' or root['report_sha256']!=original_gate or root['source_files']!=len(verification['source_sha256']):
        raise ValueError('Independent prebenchmark audit binding mismatch')
    for name,digest in root['strict_semantic_log_sha256'].items():
        if files['evidence/'+name]['original_sha256']!=digest:
            raise ValueError('Independent semantic-log identity mismatch')
    manifest=read('evidence/source-manifest.json')
    if manifest['source_sha256']!=verification['source_sha256']:
        raise ValueError('Independent review source snapshot differs')
    final=read('evidence/final-audit.json')
    if final['status']!='pass' or final['verification_sha256']!=original_gate or final['benchmark_run']:
        raise ValueError('Final local audit scope mismatch')
    comparison=read('evidence/performance-comparison.json')
    if comparison['summary_sha256']!=files['evidence/performance-summary.json']['original_sha256'] or comparison['analysis_script_sha256']!=sha(HERE/'compare_confirmations.py'):
        raise ValueError('Repeated-regression analysis binding mismatch')
    maps=[{(row['operation'],row['limbs'],row['top']):row for row in run['comparisons']} for run in summary['runs']]
    for key,field,direction in [('consistent_regressions_vs_e22','candidate_over_baseline',1),('consistent_regressions_vs_previous','candidate_over_previous',1),('consistent_improvements_vs_previous','candidate_over_previous',-1)]:
        expected=[{'operation':k[0],'limbs':k[1],'top':k[2],'ratios':[row[k][field] for row in maps]} for k in sorted(maps[0]) if all(direction*(row[k][field]-1)>0 for row in maps)]
        if comparison[key]!=expected:raise ValueError('Repeated outcome list changed: '+key)
        result[key]=len(expected)
    result['registered_gmp_target_status'] = 'target_not_met' if any(run['performance_status'] == 'target_not_met' for run in result['runs'].values()) else 'registered_library_target_met'
    if index['registered_gmp_target_status'] != result['registered_gmp_target_status'] or summary['performance_status'] != result['registered_gmp_target_status']:
        raise ValueError('Incorrect performance acceptance status')
    root_performance = read('evidence/root-performance-audit.json')
    if root_performance['status'] != 'pass' or root_performance['performance_target_met'] or root_performance['benchmark_rerun']:
        raise ValueError('Independent performance audit scope mismatch')
    if [row['tag'] for row in root_performance['runs']] != ['default1', 'default2']:
        raise ValueError('Independent performance audit run mismatch')
    fields = {'raw_sha256': 'raw_sha256', 'samples': 'samples', 'minimum_ns': 'minimum_recorded_ns',
        'principal_failed': 'primary_gmp_failures', 'key_failed': 'key_gmp_failures',
        'baseline_regressions': 'regressions_vs_baseline', 'previous_regressions': 'regressions_vs_previous'}
    for row in root_performance['runs']:
        observed = result['runs'][row['tag']]
        if row['groups'] != 52 or any(row[key] != observed[value] for key, value in fields.items()):
            raise ValueError('Independent performance audit differs from raw samples')
        run = next(item for item in summary['runs'] if item['tag'] == row['tag'])
        for operation, ratios in row['largest_shape'].items():
            largest = next(item for item in run['comparisons'] if item['operation'] == operation and item['limbs'] == 4096 and item['top'] == 63)
            if ratios != [largest[key] for key in ['candidate_over_baseline', 'candidate_over_previous', 'candidate_over_gmp']]:
                raise ValueError('Independent largest-shape ratios differ')
    for key in ['consistent_regressions_vs_e22', 'consistent_regressions_vs_previous']:
        if root_performance[key] != result[key]:
            raise ValueError('Independent repeated-regression count mismatch')
    return result


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))

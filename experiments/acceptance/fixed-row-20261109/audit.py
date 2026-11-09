#!/usr/bin/env python3
"""Audit retained public evidence only. Never execute proof or benchmark artifacts."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = 'd12759a022d2e285d0bc6b5869ccfb5c1d85f665'
NATIVE = '5790ad2fbadc9877332124c6a66ae3b70b016d03'
sha = lambda data: hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition: raise ValueError(message)


def audit(root):
    index = json.loads((root / 'index.json').read_text())
    require(index['source_commit'] == SOURCE and index['native_tree'] == NATIVE and index['gmp_parity'] is False, 'Claim identity')
    archive = root / index['archive']['path']
    require(sha(archive.read_bytes()) == index['archive']['sha256'], 'Archive SHA256')
    with zipfile.ZipFile(archive) as z:
        require(set(z.namelist()) == set(index['files']) and len(z.namelist()) == len(set(z.namelist())), 'Archive file set')
        raw = {name: z.read(name) for name in z.namelist()}
    for name, record in index['files'].items():
        require(not name.startswith('/') and '..' not in Path(name).parts and '\\' not in name, 'Unsafe archive path')
        require(len(raw[name]) == record['bytes'] and sha(raw[name]) == record['sha256'], 'Member identity: ' + name)
    get = lambda path: json.loads(raw[path])
    retained = lambda original: raw[index['original_paths'][original]]
    hashed = lambda original, expected: require(sha(retained(original)) == expected, 'Original binding: ' + original)
    receipt = get('candidate/full-r05-toolbound/receipt.json')
    require(receipt['source_commit'] == SOURCE and receipt['native_tree'] == NATIVE and receipt['scope'] == 'full-library', 'Proof source/scope')
    require(receipt['returncode'] == 0 and receipt['verification_summary'] == ['verification results:: 371 verified, 0 errors'], '371/0 retained proof')
    require(all(receipt[key] for key in ('sources_unchanged', 'tools_unchanged', 'resolution_unchanged')), 'Proof stability')
    require(len(receipt['source_hashes']) == 58 and len(receipt['tool_hashes']) == 111, '58 source/111 tools')
    require(receipt['tool_hashes'] == get('candidate/full-r05-toolbound/tools-before.json') == get('candidate/full-r05-toolbound/tools-after.json'), 'Contemporaneous tool maps')
    require(receipt['environment'] == get('candidate/full-r05-toolbound/environment.json'), 'Explicit proof environment')
    require(receipt['environment']['RUSTUP_TOOLCHAIN'] == '1.99.1-x86_64-unknown-linux-gnu', 'Pinned Rust')
    require(receipt['tool_resolution_before'] == receipt['tool_resolution_after'], 'Actual compiler/sysroot resolution equality')
    for name, expected in receipt['source_hashes'].items(): require(sha(raw['candidate/full-r05-toolbound/snapshot/' + name]) == expected, 'Proof source: ' + name)
    for name, expected in receipt['artifacts'].items(): require(sha(raw['candidate/full-r05-toolbound/' + name]) == expected, 'Proof pair: ' + name)
    require(b'verification results:: 371 verified, 0 errors' in raw['candidate/full-r05-toolbound/proof.log'], 'Actual proof log')
    flags = receipt['argv']
    require(all(flag in flags for flag in ('--no-cheating', '--compile', '-O', '--export')) and '--verify-module' not in flags, 'Full strict verification/compile')
    historical = get('candidate/full-r04/receipt.json')
    require(len(historical['tool_hashes']) == 54 and 'environment' not in historical, 'Historical r04 tool gap retained')
    require(get('candidate/static-review/provenance-addendum.json')['original_review_preserved'], 'Original static review preserved')
    baseline = get('baseline/summary.json')
    require(baseline['native_tree'] == '72dc8a5da2cbb7eddcdd26c219d50770e8b73b06' and baseline['proof_summary'] == ['358', '0'], 'Baseline 358/0')
    for name, key in [('libverigmp.rlib', 'rlib_sha256'), ('verigmp.vir', 'vir_sha256')]: require(sha(raw['baseline/' + name]) == baseline['library_pair'][key], 'Baseline pair')
    with tarfile.open(fileobj=io.BytesIO(raw['baseline/source.tar'])) as tar:
        require(all((member.name == 'native' or member.name.startswith('native/')) and (member.isfile() or member.isdir()) for member in tar.getmembers()), 'Public arithmetic-only baseline source')
        baseline_sources = get('baseline/source-before.json')
        require(baseline_sources == get('baseline/source-after.json'), 'Baseline source stability')
        for name, expected in baseline_sources.items():
            data = tar.extractfile(name).read(); require(sha(data) == expected['sha256'] and len(data) == expected['bytes'], 'Actual baseline source bytes')
    require(get('baseline/tools-before.json') == get('baseline/tools-after.json'), 'Retained baseline tool stability')
    binding = get('local-gates/binding.json')
    require(binding['candidate_source_commit'] == SOURCE and binding['candidate_native_tree'] == NATIVE, 'Native consumer binding')
    require(binding['candidate_receipt_sha256'] == sha(raw['candidate/full-r05-toolbound/receipt.json']), 'Consumed proof receipt')
    require(binding['baseline_summary_sha256'] == sha(raw['baseline/summary.json']), 'Consumed baseline receipt')
    for pair in binding['pairs'].values():
        for item in pair.values(): hashed(item['path'], item['sha256'])
    for name, expected in binding['harness'].items(): require(sha(raw['local-gates/source/' + name]) == expected, 'Public harness identity')
    gates, supplemental = get('local-gates/receipt.json'), get('local-gates/audited-mutations.json')
    for original, expected in gates['evidence'].items(): hashed(original, expected)
    original_group = get('local-gates/run-01/proof-gates.json')
    require(original_group['mutation_gate'] is False and supplemental['original_group_passed'] is False
            and gates['mutations']['original_five_attempt_group_passed'] is False, 'Original failed five-attempt group preserved')
    hashed(supplemental['source_tool_receipt'], supplemental['source_tool_receipt_sha256'])
    require(get('local-gates/run-01/binding.json')['candidate_receipt_sha256'] == sha(raw['candidate/full-r04/receipt.json']), 'Original mutation r04 provenance')
    require(sha(raw['local-gates/seal.py']) == supplemental['auditor_sha256'] == gates['seal_script_sha256'], 'Supplement auditor identity')
    genuine = {'wide-omit-acc', 'first-wrong-carry', 'wrong-first-row-store', 'wrong-add-row-store'}
    require(set(gates['mutations']['typed_failed_vc']) == genuine and len(supplemental['mutations']) == 5, 'Four genuine scoped VC rejections')
    for mutation in supplemental['mutations']:
        name = mutation['name']; prefix = 'local-gates/run-01/mutations/' + name + '/'
        original = get(prefix + 'mutation.json')
        require(original in original_group['mutations'] and mutation['original_status'] == original['status'], 'Unchanged original classifier')
        require(all(mutation[key] == original[key] for key in ('name', 'module', 'old', 'new', 'source_hashes', 'returncode', 'verification_summary')), 'Supplement matches original attempt')
        for path, expected in mutation['raw_logs'].items(): hashed(path, expected)
        for path, expected in mutation['source_hashes'].items(): require(sha(raw[prefix + path]) == expected, 'Actual mutant source bytes')
        changed = 'native/verified/' + mutation['module'] + '.rs'
        require([path for path, expected in mutation['source_hashes'].items() if receipt['source_hashes'].get(path) != expected] == [changed], 'Single actual native mutant')
        source = raw['candidate/full-r05-toolbound/snapshot/' + changed]
        require(mutation['old'].encode() in source and source.replace(mutation['old'].encode(), mutation['new'].encode(), 1) == raw[prefix + changed], 'Declared first-occurrence mutation matches source')
        flags = original['argv']; require(flags[-2:] == ['--verify-module', mutation['module']] and '--no-cheating' in flags, 'Scoped strict mutation command')
        stdout, stderr = raw[prefix + 'mutation-' + name + '.stdout'], raw[prefix + 'mutation-' + name + '.stderr']
        require(original['returncode'] == 1, 'Actual mutant return status')
        if name in genuine:
            require(mutation['status'] == 'typed_failed_vc' and mutation['module'] == 'fixed_row' and mutation['verification_summary'] == [['12', '1']]
                    and b'12 verified, 1 errors' in stdout and b'resource limit' not in stderr and b'error[E' not in stderr, 'Actual typed failed VC')
            diagnostic = b'requires not satisfied' if name.startswith('wrong-') else (b'invariant not satisfied' if name == 'first-wrong-carry' else b'postcondition not satisfied')
            require(diagnostic in stderr and original['status'] == ('not_detected' if name.startswith('wrong-') else 'typed_failed_vc'), 'Original diagnostic/classifier qualification')
        else:
            require(name == 'dispatch-omit15' and mutation['status'] == 'not_accepted' and original['status'] == 'not_detected'
                    and b'postcondition not satisfied' in stderr and b'resource limit (rlimit) exceeded' in stderr, 'Fifth dispatch attempt remains unaccepted')
    results, total, windows = {}, 0, []
    for phase in index['phases']:
        prefix = 'candidate/' + phase + '/'
        plan, report, post, window = [get(prefix + name) for name in ('plan.json', 'report.json', 'postflight.json', 'window.json')]
        require(plan['native_source_commit'] == SOURCE and plan['native_tree'] == NATIVE and plan['cpu'] == 8, 'Measured source/CPU')
        require(plan['env'] == {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'} and plan['blocks'] == 7 and plan['minimum_batch_ns'] == 10_000_000, 'Frozen environment/rules')
        principal_cells = [('principal', n, pattern, op, count) for n, count in [(1024, 512), (4096, 64)] for pattern in ('random', 'max') for op in ('mul', 'square')]
        leaf_cells = [('leaf', n, pattern, 'forced', 262144) for n in (14, 15, 16, 19, 20, 21, 22, 23, 24) for pattern in ('random', 'max')]
        boundary_counts = [(63, 65536), (64, 32768), (65, 32768), (127, 16384), (128, 16384), (129, 16384), (191, 8192), (192, 8192), (193, 8192), (511, 2048), (512, 2048), (513, 2048), (1023, 1024), (1024, 512), (1025, 512), (4095, 128), (4096, 64), (4097, 64)]
        expected_cells = principal_cells + leaf_cells if 'principal-leaves' in phase else [('boundary', n, 'random', op, count) for n, count in boundary_counts for op in ('mul', 'square')]
        require([tuple(cell[key] for key in ('group', 'n', 'pattern', 'op', 'count')) for cell in plan['cells']] == expected_cells
                and plan['orientation'] == (0 if phase.endswith('run1') else 1), 'Exact fixed cells/counts/independent orientation')
        for key in ('driver_sha256', 'wrapper_sha256', 'watchdog_sha256'):
            member = {'driver_sha256': 'candidate/measure.py', 'wrapper_sha256': 'candidate/run-window.ps1', 'watchdog_sha256': 'controller/resume-watchdog.ps1'}[key]
            require(sha(raw[member]) == plan[key], 'Measured controller identity')
        hashed(plan['binding_path'], plan['binding_sha256'])
        require(sha(raw['local-gates/timing-inputs.json']) == plan['timing_inputs_sha256'], 'Timing input registration')
        for side, item in plan['binaries'].items(): hashed(item['path'], item['sha256'])
        require(sha(raw[prefix + 'linkage-before.json']) == plan['linkage_before_sha256'], 'Frozen linker manifest')
        links = [get(prefix + name) for name in ('linkage-before.json', 'linkage-window-start.json', 'linkage-after.json')]
        for side in ('old', 'new'):
            for link in links:
                require(all(link[side][key] == links[0][side][key] for key in ('argv', 'env', 'returncode', 'files')), 'Canonical loader drift')
            for entry in links[0][side]['files'].values(): require(binding['linked_libraries'][entry['canonical']] == entry['sha256'], 'Linked dependency identity')
        rows = [json.loads(line) for line in raw[prefix + 'raw.jsonl'].splitlines()]
        require(len(rows) == plan['sample_invocations'] == len(plan['cells']) * 28 and len(report['cells']) == len(plan['cells']), 'Complete cell/sample schedule')
        require(post['status'] == 'pass' and post['binaries_pairs_inputs_stable'] and post['driver_sha256'] == plan['driver_sha256']
                and set(post['tool_hashes_unchanged']) == set(binding['tools']) and all(post['tool_hashes_unchanged'].values())
                and binding['tools'] == receipt['tool_hashes'] and post['canonical_linkage_stable'], 'Complete111-tool postflight checks')
        require(post['report_sha256'] == sha(raw[prefix + 'report.json']) and post['raw_sha256'] == report['raw_sha256'] == sha(raw[prefix + 'raw.jsonl']), 'Raw/report/post bindings')
        require(report['plan_sha256'] == post['plan_sha256'] == sha(raw[prefix + 'plan.json']), 'Plan binding')
        pre = get(prefix + 'preflight.json')
        require(pre['status'] == 'pass' and pre['plan_sha256'] == sha(raw[prefix + 'plan.json']) and pre['benchmark_samples'] == 0 and pre['operations'] == len(plan['cells']) * 2, 'Outside-sample preflight')
        counts, medians = Counter(), []
        for position, row in enumerate(rows):
            cell_id, block, slot = position // 28, position % 28 // 4, position % 4
            cell = plan['cells'][cell_id]
            side = (('old', 'new', 'new', 'old') if (cell_id + block + plan['orientation']) % 2 == 0 else ('new', 'old', 'old', 'new'))[slot]
            require((row['cell'], row['block'], row['position'], row['side']) == (cell_id, block, slot, side), 'Actual ABBA/BAAB order')
            require(row['argv'] == [plan['binaries'][side]['path'], 'sample', cell['input'], cell['op'], str(cell['count'])] and row['returncode'] == 0 and row['stderr'] == '', 'Actual invocation semantics')
            fields = row['stdout'].split()
            require(fields[:3] == ['sample', cell['op'], str(cell['count'])] and len(fields) == 7 and int(fields[3]) == row['ns'] and list(map(int, fields[4:])) == cell['checksums'], 'Actual checksum/count/timer output')
            require(row['ns'] >= 10_000_000, 'At least 10ms per batch')
            counts[cell_id, side] += 1
        require(set(counts.values()) == {14} and len(counts) == len(plan['cells']) * 2, '14 observations per side/cell')
        for i, cell in enumerate(plan['cells']):
            hashed(cell['input'], cell['input_sha256']); hashed(cell['expected'], cell['expected_sha256'])
            sample = {side: [row['ns'] / cell['count'] for row in rows if row['cell'] == i and row['side'] == side] for side in ('old', 'new')}
            median = {side: statistics.median(values) for side, values in sample.items()}; ratio = median['new'] / median['old']
            require(sample == report['cells'][i]['samples'] and median == report['cells'][i]['median_ns_per_operation'] and ratio == report['cells'][i]['new_over_old'], 'Retained medians/raw observations')
            medians.append(dict(group=cell['group'], n=cell['n'], pattern=cell['pattern'], op=cell['op'], ratio=ratio))
        principal = [item['ratio'] for item in medians if item['group'] == 'principal']
        principal_gm = math.exp(statistics.mean(math.log(value) for value in principal)) if principal else None
        worst = max(item['ratio'] for item in medians)
        require(worst == report['worst_new_over_old'] and principal_gm == report['principal_gm_new_over_old'] and report['numerical_go'], 'Recomputed numerical GO')
        require(worst <= 1.03 and (principal_gm is None or len(principal) == 8 and principal_gm <= 0.97), 'Unchanged acceptance gates')
        require(window['suspend_status'] == window['resume_status'] == window['screen_exit'] == 0 and window['qemu_alive'] and window['qemu_cpu_advance_ms'] > 0, 'Observed resume and CPU advance')
        require(window['phase'] == phase and window['outer_timeout_seconds'] == 120 and window['independent_watchdog_seconds'] == 140, 'Actual declared wrapper limits')
        require(not window['watchdog_fired'] and window['within_watchdog_deadline'] and window['window_wall_seconds'] < 120, 'Actual window below120s')
        require(window['watchdog_script_sha256'] == plan['watchdog_sha256'] and raw[prefix + 'resume-watchdog.stop'] == b'resumed by root finally', 'Watchdog/normal-finally receipt')
        windows.append((datetime.fromisoformat(window['started_utc']), datetime.fromisoformat(window['finished_utc'])))
        results[phase] = dict(observations=len(rows), principal_gm=principal_gm, worst=worst, min_batch_ns=min(row['ns'] for row in rows), cells=medians)
        total += len(rows)
    require(total == 3472, 'All3472 actual observations')
    windows.sort(); require(all(left[1] < right[0] for left, right in zip(windows, windows[1:])), 'Independent nonoverlapping windows')
    for revision in ('r00', 'r01'):
        rejection = get('candidate/measurement-plan-' + revision + '-rejected-before-sampling/REJECTION.json')
        require(rejection['status'] == 'rejected_before_sampling' and rejection['samples'] == 0, 'Presampling rejection qualification')
    return dict(status='pass', scope='retained public artifact integrity/statistics audit; no proof/build/benchmark execution',
                archive_sha256=index['archive']['sha256'], retained_files=len(raw), observations=total, phases=results,
                mutation_rejections=4, original_mutation_group_passed=False, dispatch_resource_limit_accepted=False,
                acceptance_status=index['status'], gmp_parity=False,
                limitations=['Retained tool hash maps attest identities; tool binaries are deliberately omitted.',
                            'Original Windows wrapper uses a120s owned command timeout and140s independent resume watchdog; actual windows were below120s. No hard real-time guarantee is inferred.',
                            'Archive audit does not replace root final independent acceptance, local gate qualifications, or source proof review.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, default=ROOT); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = audit(args.root)
    if args.output: args.output.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({key: value for key, value in result.items() if key != 'phases'}, indent=2))

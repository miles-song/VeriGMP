#!/usr/bin/env python3
"""Bind corrected untimed metadata to the exact original compiled experiment."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from common import checked_prepared, file_sha, write_json
from operations import generate, verify_anchors
from test_operations import validate_operation_report
from measure import validate_build
from check_package import (ORIGINAL_BUILD, PREVIOUS_ARCHIVE, PREFIX, read_json,
                           sha, validate_payloads, validate_rebind, validate_sources,
                           validate_static)


def host_path(name):
    match = re.fullmatch(r'/mnt/([a-z])/(.*)', name)
    if os.name == 'nt' and match:
        return Path(match[1].upper()+':/'+match[2])
    return Path(name)


def expect_rejection(action, fragment):
    try:
        action()
    except RuntimeError as error:
        if fragment not in str(error):
            raise RuntimeError('unexpected tamper rejection: '+str(error)) from error
        return str(error)
    raise RuntimeError('tampered evidence was accepted: '+fragment)


class ChangedPayload:
    def __init__(self, bundle, name, data):
        self.bundle, self.name, self.data = bundle, name, data

    def read(self, name):
        return self.data if name == self.name else self.bundle.read(name)


def measurement_guard_fixtures(build, original):
    # Exercise the unchanged Linux measurement preflight, never its main/runner.
    # Temporary fixture grants are deleted here and authorize no timing window.
    cpu = min(os.sched_getaffinity(0))
    result = {}
    with tempfile.TemporaryDirectory(prefix='verigmp-metadata-guard-') as folder:
        path = Path(folder)/'build.json'
        quiet_path = Path(folder)/'fixture-only-quiet.json'
        def attempt(candidate, **quiet_changes):
            write_json(path, candidate)
            quiet = dict(status='granted', phase=0, cpu=cpu, build_sha256=file_sha(path),
                         independent_prereview='pass', known_heavy_jobs_quiescent=True,
                         fixture_only=True, timing_authorized=False)
            quiet.update(quiet_changes)
            write_json(quiet_path, quiet)
            return validate_build(path, quiet_path, 0, cpu)
        if attempt(build)[0] != build:
            raise RuntimeError('unchanged measurement preflight rejected metadata build')
        result['valid_metadata_build'] = 'pass'
        result['original_metadata_stale'] = expect_rejection(lambda: attempt(original), 'frozen harness/protocol drift')
        result['prereview_missing'] = expect_rejection(lambda: attempt(build, independent_prereview='pending'), 'quiet/prereview grant mismatch')
        bad = copy.deepcopy(build)
        bad['binaries']['both']['sha256'] = '0'*64
        result['frozen_binary'] = expect_rejection(lambda: attempt(bad), 'frozen binary drift')
        bad = copy.deepcopy(build)
        bad['inputs_sha256'][PREFIX+'measure.py'] = '0'*64
        result['frozen_harness_input'] = expect_rejection(lambda: attempt(bad), 'frozen harness/protocol drift')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-package', required=True, type=Path)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepared, data = checked_prepared(args.prepared)
    old = args.previous_package.resolve()
    out = args.output.resolve()
    if out.exists():
        raise RuntimeError('use a fresh metadata-only output')
    receipt = json.loads((old/'package.json').read_text())
    archive = old/'evidence.zip'
    if receipt['archive_sha256'] != PREVIOUS_ARCHIVE or file_sha(archive) != PREVIOUS_ARCHIVE:
        raise RuntimeError('wrong immutable prior package')
    if archive.stat().st_size != receipt['archive_bytes']:
        raise RuntimeError('prior archive size mismatch')
    with zipfile.ZipFile(archive) as bundle:
        manifest = validate_payloads(bundle, receipt)
        previous = read_json(bundle, 'source/prepared.json')
        validate_sources(bundle, previous)
        original = validate_static(bundle)
        if original['prepared_sha256'] != sha(bundle.read('source/prepared.json')):
            raise RuntimeError('original prepared provenance mismatch')
        if data['cells'] != previous['cells']:
            raise RuntimeError('native source changed; metadata reuse forbidden')
        # Revalidate all live original source/proof/static/harness payloads.
        # The original directories are read only and are never rebound in place.
        roots = dict(zip(('source','producer','static','harness-fixtures'),
                         map(host_path, receipt['payload_roots'][:4])))
        for row in manifest['entries']:
            if row['path'] == 'operation-counts.json':
                path = host_path(receipt['payload_roots'][4])
            else:
                prefix, suffix = row['path'].split('/', 1)
                path = roots[prefix]/suffix
            if path.stat().st_size != row['bytes'] or file_sha(path) != row['sha256']:
                raise RuntimeError('original live payload drift: '+str(path))
        out.mkdir(parents=True)
        status = dict(status='running', benchmark_executed=False, calibration_executed=False,
                      proof_reexecuted=False, binaries_rebuilt=False, arithmetic_changed=False)
        write_json(out/'verification.json', status)
        try:
            history = out/'history'
            history.mkdir()
            for name in ('package.json','manifest.json','package-check.json'):
                shutil.copyfile(old/name, history/name)
            (history/'prepared.json').write_bytes(bundle.read('source/prepared.json'))
            (history/'operation-counts.json').write_bytes(bundle.read('operation-counts.json'))
            for name in previous['inputs_sha256']:
                target = history/'inputs'/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read('source/inputs/'+name))
            operations = out/'operation-counts.json'
            report = generate(prepared, data, operations)
            fixture = validate_operation_report(report, data, original['key_shapes'], verify_anchors(prepared))
            fixture.update(prepared_sha256=file_sha(prepared/'prepared.json'),
                           operation_counts_sha256=file_sha(operations))
            write_json(out/'operation-fixtures.json', fixture)
            build = copy.deepcopy(original)
            changed = sorted(name for name in set(original['inputs_sha256'])|set(data['inputs_sha256'])
                             if original['inputs_sha256'].get(name) != data['inputs_sha256'].get(name))
            build.update(source_head=data['source_head'], prepared_sha256=file_sha(prepared/'prepared.json'),
                         inputs_sha256=data['inputs_sha256'], operation_counts_sha256=file_sha(operations),
                         protocol_sha256=data['inputs_sha256'][PREFIX+'PROTOCOL.md'],
                         metadata_rebind=dict(original_build_sha256=ORIGINAL_BUILD,
                             original_build_path=str(roots['static']/'bench-build/bench-build.json'),
                             original_source_head=original['source_head'],
                             previous_archive_sha256=PREVIOUS_ARCHIVE,
                             previous_archive_path=str(archive),
                             prepared_sha256=file_sha(prepared/'prepared.json'),
                             changed_inputs=changed, arithmetic_changed=False,
                             binaries_rebuilt=False, proof_reexecuted=False,
                             benchmark_executed=False, calibration_executed=False))
            old_input = lambda name: bundle.read('source/inputs/'+name)
            new_input = lambda name: (prepared/'inputs'/name).read_bytes()
            validate_rebind(original, build, data, previous, old_input, new_input)
            # Verify the executable inputs at the exact paths consumed by measure.py.
            for label, row in build['binaries'].items():
                if file_sha(host_path(row['path'])) != row['sha256']:
                    raise RuntimeError('live frozen benchmark binary drift: '+label)
            controls = {}
            bad = copy.deepcopy(report)
            target = next(row for row in bad['rows'] if row['op'] == 2)
            target['cells']['both']['visits']['base_word_multiplications'] += 1
            controls['exact_operation_count'] = expect_rejection(lambda: validate_operation_report(
                bad, data, original['key_shapes'], verify_anchors(prepared)), 'exact 86-cell')
            controls['superseded_operation_receipt'] = expect_rejection(lambda: validate_operation_report(
                read_json(bundle, 'operation-counts.json'), data, original['key_shapes'], verify_anchors(prepared)), 'exact 86-cell')
            controls['original_build'] = expect_rejection(lambda: validate_static(ChangedPayload(bundle,
                'static/bench-build/bench-build.json', bundle.read('static/bench-build/bench-build.json')+b'\n')), 'original build identity')
            binary = 'static/bench-build/both-bench'
            controls['binary_payload'] = expect_rejection(lambda: validate_static(ChangedPayload(
                bundle, binary, bundle.read(binary)+b'\0')), 'benchmark binary mismatch')
            bad_build = copy.deepcopy(build)
            bad_build['binaries']['both']['sha256'] = '0'*64
            controls['binary_receipt'] = expect_rejection(lambda: validate_rebind(
                original, bad_build, data, previous, old_input, new_input), 'nonmetadata frozen build change')
            def changed_input(name):
                return new_input(name)+(b'\n' if name == PREFIX+'measure.py' else b'')
            controls['frozen_input'] = expect_rejection(lambda: validate_rebind(
                original, build, data, previous, old_input, changed_input), 'current input snapshot drift')
            def changed_source(label, name):
                source = (prepared/label/name).read_bytes()
                return source.replace(b'position+=2;', b'position+=1;') if name.endswith('/square_base.rs') else source
            controls['diagonal_stride'] = expect_rejection(lambda: verify_anchors(
                prepared, changed_source), 'source schedule anchor missing')
            controls['unchanged_measurement_preflight'] = measurement_guard_fixtures(build, original)
            write_json(out/'bench-build.json', build)
            status.update(status='metadata_only_pass', source_head=data['source_head'],
                prepared_sha256=file_sha(prepared/'prepared.json'),
                original_archive_sha256=PREVIOUS_ARCHIVE, original_build_sha256=ORIGINAL_BUILD,
                metadata_build_sha256=file_sha(out/'bench-build.json'),
                operation_counts_sha256=file_sha(operations),
                operation_fixtures_sha256=file_sha(out/'operation-fixtures.json'),
                revalidated_original_payloads=len(manifest['entries']),
                unchanged_native_files_per_cell=57, unchanged_native_rust_files_per_cell=50,
                unchanged_binaries={label:row['sha256'] for label,row in build['binaries'].items()},
                unchanged_compilation_inputs='original bench.rs, producer rlib/vir, compiler flags and tool hashes',
                unchanged_measurement_dependencies='measure.py imports only byte/AST-identical cells and PRIMARY',
                changed_metadata_inputs=changed, tamper_controls=controls)
            checked_prepared(prepared)
            write_json(out/'verification.json', status)
            print(json.dumps(status, indent=2))
        except BaseException as error:
            status.update(status='fail', failure=repr(error))
            write_json(out/'verification.json', status)
            raise


if __name__ == '__main__':
    main()

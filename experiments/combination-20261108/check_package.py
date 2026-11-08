#!/usr/bin/env python3
"""Offline evidence integrity, exact schedule and metadata-only reuse audit."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile
from operations import verify_anchors
from test_operations import validate_operation_report

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent/'evidence'
BASE = '515f1efa0d79bcb73272df9f54917f156decf1e1'
PREVIOUS_ARCHIVE = '85a8d8705b387285621f26af4d2684c33929eacb47b6774be96ddd5117b136f6'
ORIGINAL_BUILD = '48dc256f11b7944f30e9be7358d749b6f8e33211f234171e738af3b8f7c3fe9f'
EXPECTED = {'baseline':'7e8d3f151d3eda7c5a3df285f882618a26022d0f7b7661ff266812a4b123f446',
            'double':'ff3843b5b822bc9b2080bd0f26d6b604cf17b1147de193848e01ac8526c00f4a',
            'checks':'652224b6d79a7c2bc769b4abdb7ae955e975da87cdf55f2ed5b9fb90cefb9756',
            'both':'495f1689b95ebd7ed3151a13d6cec505ed77f80177adcc6dadc9567f8836f06b'}
PREFIX = 'experiments/combination-20261108/'
METADATA_INPUTS = {PREFIX+name for name in ('PROTOCOL.md','README.md','RECEIPT.md',
    'operations.py','test_operations.py','check_package.py','pack_evidence.py','rebind_metadata.py')}
REBOUND_FIELDS = {'source_head','prepared_sha256','inputs_sha256','operation_counts_sha256',
                  'protocol_sha256','metadata_rebind'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(bundle, name):
    return json.loads(bundle.read(name))


def validate_payloads(bundle, receipt):
    names = bundle.namelist()
    if len(names) != len(set(names)) or names.count('manifest.json') != 1:
        raise RuntimeError('archive path collision')
    manifest = read_json(bundle, 'manifest.json')
    if sha(bundle.read('manifest.json')) != receipt['manifest_sha256']:
        raise RuntimeError('manifest identity mismatch')
    if any(manifest[k] for k in ('benchmark_executed','calibration_executed','performance_accepted')):
        raise RuntimeError('archive claims timing or acceptance')
    entries = manifest['entries']
    paths = [row['path'] for row in entries]
    if len(entries) != manifest['entry_count'] or len(paths) != len(set(paths)):
        raise RuntimeError('manifest count/path mismatch')
    if set(names) != set(paths)|{'manifest.json'} or len(entries) != receipt['logical_payloads']:
        raise RuntimeError('unmanifested archive payload')
    for row in entries:
        data = bundle.read(row['path'])
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise RuntimeError('evidence payload hash mismatch: '+row['path'])
    return manifest


def validate_sources(bundle, prepared):
    if prepared['base'] != BASE or prepared['status'] != 'pass':
        raise RuntimeError('wrong fixed base')
    for label, digest in EXPECTED.items():
        cell = prepared['cells'][label]
        mapping = cell['native_sha256']
        canonical = json.dumps(mapping, sort_keys=True, separators=(',',':')).encode()
        if cell['native_manifest_sha256'] != digest or sha(canonical) != digest:
            raise RuntimeError('four-cell source identity mismatch: '+label)
        for path, expected in mapping.items():
            if sha(bundle.read('source/'+label+'/'+path)) != expected:
                raise RuntimeError('reconstructed native source mismatch: '+label+'/'+path)
    for path, digest in prepared['inputs_sha256'].items():
        if sha(bundle.read('source/inputs/'+path)) != digest:
            raise RuntimeError('frozen input snapshot mismatch: '+path)


def validate_static(bundle):
    original_bytes = bundle.read('static/bench-build/bench-build.json')
    if sha(original_bytes) != ORIGINAL_BUILD:
        raise RuntimeError('original build identity mismatch')
    build = json.loads(original_bytes)
    producer = read_json(bundle, 'producer/verification.json')
    check = read_json(bundle, 'static/verification.json')
    harness = read_json(bundle, 'harness-fixtures/verification.json')
    if producer['status'] != 'full_library_pass' or producer['verified_items'] != 366:
        raise RuntimeError('combined proof receipt mismatch')
    if producer['native_manifest_sha256'] != EXPECTED['both']:
        raise RuntimeError('combined proof source mismatch')
    if check['status'] != 'pass' or check['bench_build_sha256'] != ORIGINAL_BUILD or build['status'] != 'static_pass':
        raise RuntimeError('static gate receipt mismatch')
    if harness['status'] != 'pass' or harness['benchmark_executed']:
        raise RuntimeError('harness receipt mismatch')
    if build['native_manifests'] != EXPECTED:
        raise RuntimeError('original build native binding mismatch')
    for label, row in build['producers'].items():
        if row['source_native_manifest_sha256'] != EXPECTED[label] or not row['all_50_native_rust_hashes_equal']:
            raise RuntimeError('producer source binding mismatch: '+label)
        for name, digest in row['payload_sha256'].items():
            if sha(bundle.read('static/producers/'+label+'/'+name)) != digest:
                raise RuntimeError('producer payload mismatch: '+label+'/'+name)
        for name, digest in row['exports_sha256'].items():
            if sha(bundle.read('static/producers/'+label+'/'+name)) != digest:
                raise RuntimeError('producer export mismatch: '+label+'/'+name)
    for label, row in build['binaries'].items():
        if sha(bundle.read('static/bench-build/'+Path(row['path']).name)) != row['sha256']:
            raise RuntimeError('benchmark binary mismatch: '+label)
    return build


def selected_ast(source, names):
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            selected.append(ast.dump(node, include_attributes=False))
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            selected.append(ast.dump(node, include_attributes=False))
    if len(selected) != len(names):
        raise RuntimeError('operation dependency declarations missing')
    return selected


def validate_rebind(original, build, prepared, previous, old_input, new_input):
    if {k:v for k,v in build.items() if k not in REBOUND_FIELDS} != {k:v for k,v in original.items() if k not in REBOUND_FIELDS}:
        raise RuntimeError('nonmetadata frozen build change')
    meta = build['metadata_rebind']
    if meta['original_build_sha256'] != ORIGINAL_BUILD or meta['previous_archive_sha256'] != PREVIOUS_ARCHIVE:
        raise RuntimeError('metadata reuse provenance mismatch')
    if any(meta[k] for k in ('arithmetic_changed','binaries_rebuilt','proof_reexecuted',
                            'benchmark_executed','calibration_executed')):
        raise RuntimeError('metadata-only boundary mismatch')
    if prepared['cells'] != previous['cells'] or build['native_manifests'] != EXPECTED:
        raise RuntimeError('reused native source drift')
    if build['inputs_sha256'] != prepared['inputs_sha256']:
        raise RuntimeError('rebound input manifest mismatch')
    if original['inputs_sha256'] != previous['inputs_sha256']:
        raise RuntimeError('original input manifest mismatch')
    changed = {name for name in set(original['inputs_sha256'])|set(build['inputs_sha256'])
               if original['inputs_sha256'].get(name) != build['inputs_sha256'].get(name)}
    if changed - METADATA_INPUTS or meta['changed_inputs'] != sorted(changed):
        raise RuntimeError('compiled/measurement input drift')
    for name, digest in original['inputs_sha256'].items():
        if sha(old_input(name)) != digest:
            raise RuntimeError('original input snapshot drift: '+name)
    for name, digest in build['inputs_sha256'].items():
        if sha(new_input(name)) != digest:
            raise RuntimeError('current input snapshot drift: '+name)
    dependencies = {'FULL_SIZES','PRIMARY','cells'}
    if selected_ast(old_input(PREFIX+'operations.py'), dependencies) != selected_ast(new_input(PREFIX+'operations.py'), dependencies):
        raise RuntimeError('measurement operation cells or primary subset changed')
    imports = [n for n in ast.walk(ast.parse(new_input(PREFIX+'measure.py')))
               if isinstance(n, ast.ImportFrom) and n.module == 'operations']
    if len(imports) != 1 or {a.name for a in imports[0].names} != {'cells','PRIMARY'}:
        raise RuntimeError('unexpected measurement dependency on analytic counts')
    if build['protocol_sha256'] != prepared['inputs_sha256'][PREFIX+'PROTOCOL.md']:
        raise RuntimeError('rebound protocol binding mismatch')
    if build['prepared_sha256'] != meta['prepared_sha256']:
        raise RuntimeError('rebound prepared binding mismatch')
    if build['source_head'] != prepared['source_head']:
        raise RuntimeError('rebound source commit mismatch')
    return changed


def main():
    archive = EVIDENCE/'evidence.zip'
    receipt = json.loads((EVIDENCE/'package.json').read_text())
    if archive.stat().st_size != receipt['archive_bytes'] or sha(archive.read_bytes()) != receipt['archive_sha256']:
        raise RuntimeError('archive identity mismatch')
    with zipfile.ZipFile(archive) as bundle:
        validate_payloads(bundle, receipt)
        prepared = read_json(bundle, 'source/prepared.json')
        validate_sources(bundle, prepared)
        original = validate_static(bundle)
        previous = read_json(bundle, 'metadata/history/prepared.json')
        if original['prepared_sha256'] != sha(bundle.read('metadata/history/prepared.json')):
            raise RuntimeError('original prepared provenance mismatch')
        build_bytes = bundle.read('metadata/bench-build.json')
        build = json.loads(build_bytes)
        validate_rebind(original, build, prepared, previous,
            lambda name: bundle.read('metadata/history/inputs/'+name),
            lambda name: bundle.read('source/inputs/'+name))
        if build['prepared_sha256'] != sha(bundle.read('source/prepared.json')):
            raise RuntimeError('current prepared receipt hash mismatch')
        ops_bytes = bundle.read('operation-counts.json')
        if build['operation_counts_sha256'] != sha(ops_bytes):
            raise RuntimeError('corrected operation count identity mismatch')
        if ops_bytes != bundle.read('metadata/operation-counts.json'):
            raise RuntimeError('corrected operation receipt copies differ')
        anchors = verify_anchors(None, lambda label,name: bundle.read('source/'+label+'/'+name))
        fixture = validate_operation_report(json.loads(ops_bytes), prepared, build['key_shapes'], anchors)
        fixture.update(prepared_sha256=build['prepared_sha256'], operation_counts_sha256=sha(ops_bytes))
        if fixture != read_json(bundle, 'metadata/operation-fixtures.json'):
            raise RuntimeError('enumerated operation fixture receipt mismatch')
        if json.loads(ops_bytes)['prepared_sha256'] != build['prepared_sha256']:
            raise RuntimeError('corrected operation prepared binding mismatch')
        reuse = read_json(bundle, 'metadata/verification.json')
        if reuse['status'] != 'metadata_only_pass' or reuse['metadata_build_sha256'] != sha(build_bytes):
            raise RuntimeError('metadata reuse receipt mismatch')
        if reuse['operation_counts_sha256'] != sha(ops_bytes) or reuse['operation_fixtures_sha256'] != sha(bundle.read('metadata/operation-fixtures.json')):
            raise RuntimeError('metadata reuse operation binding mismatch')
        if any(reuse[k] for k in ('arithmetic_changed','binaries_rebuilt','proof_reexecuted',
                                 'benchmark_executed','calibration_executed')):
            raise RuntimeError('reuse receipt claims nonmetadata work')
        historical_package = read_json(bundle, 'metadata/history/package.json')
        if historical_package['archive_sha256'] != PREVIOUS_ARCHIVE or historical_package['manifest_sha256'] != sha(bundle.read('metadata/history/manifest.json')):
            raise RuntimeError('prior package provenance mismatch')
        for name,digest in build['inputs_sha256'].items():
            if sha((ROOT/name).read_bytes()) != digest:
                raise RuntimeError('checkout frozen input drift: '+name)
    output = dict(status='pass',payloads=receipt['logical_payloads'],source_cells=4,
        combined_verified_items=366,operation_cells=86,enumerated_square_base_sizes=129,
        original_build_sha256=ORIGINAL_BUILD,metadata_build_sha256=sha(build_bytes),
        proof_reexecuted=False,binaries_rebuilt=False,benchmark_executed=False,
        calibration_executed=False,archive_sha256=receipt['archive_sha256'])
    (EVIDENCE/'package-check.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__ == '__main__':
    main()

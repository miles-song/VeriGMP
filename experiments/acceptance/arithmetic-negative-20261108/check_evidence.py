#!/usr/bin/env python3
"""Offline source, archive, restoration, and negative-result replay only."""
import hashlib
import io
import json
from pathlib import Path
import types
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCTION = 'de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9'
BASE = '515f1efa0d79bcb73272df9f54917f156decf1e1'
COMBINATION = 'f9c2977233a573ddf32dae3993b46626678ca3ca'
DOUBLE = '3ce342e2f09964518c9ff889b2538006c44741c0'
RAW = '7e3476d8f0fb15accc0824fb9982c3a2c66c3fb055c5bffe5a8a52d0faecf825'
DOUBLE_STATIC = '024dbbb3d9f292804f7ab8b7a677546d4e5b1fe0088896182527c4d70efa723c'
COMBO_STATIC = 'f195f84f88e571b7e022f88b4f6baa13a55f65222937cf16488ed7581a396991'
GMP = '0ccdfb6d6f5c039465f6d002cf7e4c072d48ac6a2cffc8dd6c748dec31592804'
BUILD = dict(W1='310ee8eed5b7ad0d86d51e69300739c953b411d667548964424f144d3a8ad7f6',
             W2='e8ee2615528153f640f696948a79637d47b342c4c803f7d867d4b17bf6b00d2a')
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda data: json.loads(data)


def git_hash(kind, data):
    return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()


def git_tree(data):
    entries = {}
    while data:
        end = data.index(b'\0')
        mode, name = data[:end].split(b' ', 1)
        entries[name.decode()] = (mode.decode(), data[end+1:end+21].hex())
        data = data[end+21:]
    return entries


def main():
    if not __debug__:
        raise RuntimeError('Run this audit without Python optimization flags')
    manifest = load((HERE/'manifest.json').read_bytes())
    assert (manifest['production_base'],manifest['integration_base'],manifest['inherited_source']) == (PRODUCTION,BASE,COMBINATION)
    assert manifest['disposition'] == 'VALID NEGATIVE EVIDENCE / NO-GO PROMOTION'
    assert all(manifest[k] is False for k in ['native_promotion_accepted','performance_accepted',
        'gmp_parity_accepted','new_benchmark','new_calibration','new_build','new_proof'])
    evidence = (HERE/'evidence.zip').read_bytes()
    assert sha(evidence) == manifest['evidence_archive_sha256']
    with zipfile.ZipFile(io.BytesIO(evidence)) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names))
        assert set(names) == {'objects/'+h for h in manifest['object_bytes']}
        objects = {h: bundle.read('objects/'+h) for h in manifest['object_bytes']}
    for digest, data in objects.items():
        assert sha(data) == digest and len(data) == manifest['object_bytes'][digest]
    assert set(manifest['payload_sha256'].values()) == set(objects)

    def read(name):
        return objects[manifest['payload_sha256'][name]]

    for name in ['RESULTS.md','CHECKER_USAGE.md','native-byte-audit.json','summary.json',
                 'all-cell-ratios.csv','check_evidence.py','test_evidence.py','build_checkpoint.py']:
        assert (HERE/name).read_bytes() == read('checkpoint/'+name), name
    if 'validation/validation.json' in manifest['payload_sha256']:
        validation_bytes = read('validation/validation.json')
        assert (HERE/'validation.json').read_bytes() == validation_bytes
        validation = load(validation_bytes)
        assert validation['status'] == 'pass' and validation['actual_existing_receipts_modified'] is False
        assert {r['check'] for r in validation['checks']} == {'checkpoint','tamper','combination-static','double-static'}
        validation_sources = {'checkpoint':read('checkpoint/check_evidence.py'),
            'tamper':read('checkpoint/test_evidence.py'),
            'combination-static':(ROOT/'experiments/combination-20261108/check_package.py').read_bytes(),
            'double-static':read('double-static/check_package.py')}
        for row in validation['checks']:
            data = read('validation/'+row['check']+'.log')
            assert sha(data) == row['log_sha256'] and load(data)['status'] == 'pass'
            assert row['source_sha256'] == sha(validation_sources[row['check']])
    source = load(read('checkpoint/native-byte-audit.json'))
    assert source['native_files'] == 57 and source['native_rust_files'] == 50 and source['public_readme_files'] == 2
    assert source['baseline_complete_producer_verified_items'] == 358 and source['fresh_proof'] is False
    commits = {}
    for ref, identity in source['identities'].items():
        data = read('git-commits/'+ref)
        assert git_hash('commit', data) == ref
        commits[ref] = dict(line.split(b' ',1) for line in data.split(b'\n\n',1)[0].splitlines() if b' ' in line)
        assert commits[ref][b'tree'].decode() == identity['tree']
    assert source['identities'][PRODUCTION]['native_tree'] == source['identities'][BASE]['native_tree'] == source['identities'][COMBINATION]['native_tree']
    tree_objects = {}
    for name in manifest['payload_sha256']:
        if name.startswith('baseline-git-trees/'):
            digest = name.split('/')[-1]
            assert git_hash('tree', read(name)) == digest
            tree_objects[digest] = git_tree(read(name))
    root_tree = tree_objects[commits[PRODUCTION][b'tree'].decode()]
    assert root_tree['native'][1] == source['identities'][PRODUCTION]['native_tree']
    protected = source['protected_sha256']
    actual_native = {p.relative_to(ROOT).as_posix() for p in (ROOT/'native').rglob('*') if p.is_file()}
    assert actual_native == {p for p in protected if p.startswith('native/')}
    for name, expected in protected.items():
        data = read('production-baseline/'+name)
        assert sha(data) == expected and (ROOT/name).read_bytes() == data, name
        entries = root_tree
        components = name.split('/')
        for component in components[:-1]:
            entries = tree_objects[entries[component][1]]
        assert git_hash('blob', data) == entries[components[-1]][1], name

    # Reuse original static packages without flattening away their failure history.
    double_manifest = load(read('double-static/manifest.json'))
    double_bytes = read('double-static/evidence.zip')
    assert sha(double_bytes) == double_manifest['archive_sha256'] == DOUBLE_STATIC
    with zipfile.ZipFile(io.BytesIO(double_bytes)) as z:
        assert len(z.namelist()) == len(set(z.namelist())) == len(double_manifest['object_bytes'])
        assert set(z.namelist()) == {'objects/'+h for h in double_manifest['object_bytes']}
        double_objects = {h:z.read('objects/'+h) for h in double_manifest['object_bytes']}
    for digest, data in double_objects.items():
        assert sha(data) == digest and len(data) == double_manifest['object_bytes'][digest]
    def d_read(name): return double_objects[double_manifest['payload_sha256'][name]]
    d_build_bytes = d_read('check-3/bench-build/bench-build.json')
    d_build = load(d_build_bytes)
    assert sha(d_build_bytes) == BUILD['W1']
    assert load(d_read('producer-2/verification.json'))['verified_items'] == 365
    baseline = load(d_read('check-3/baseline/verification.json'))
    assert baseline['library_verified_items'] == 358
    assert baseline['exports_sha256']['libverigmp.rlib'] == source['baseline_rlib_sha256']
    assert baseline['exports_sha256']['verigmp.vir'] == source['baseline_vir_sha256']
    for name, digest in load(d_read('check-3/verification.json'))['source']['native_sha256'].items():
        assert sha(d_read('check-3/source/'+name)) == digest == sha(read('double-publication/'+name))
    assert {name for name in protected if name.endswith('.rs') and read('production-baseline/'+name) != read('double-publication/'+name)} == {'native/specs/square.rs','native/verified/square_low.rs'}
    combo_link = manifest['existing_combination_archive']
    combo_bytes = (ROOT/combo_link['path']).read_bytes()
    assert sha(combo_bytes) == combo_link['sha256'] == COMBO_STATIC
    combo_folder = (ROOT/combo_link['path']).parent
    with zipfile.ZipFile(io.BytesIO(combo_bytes)) as z:
        c_manifest_bytes = z.read('manifest.json')
        assert sha(c_manifest_bytes) == combo_link['manifest_sha256']
        assert c_manifest_bytes == (combo_folder/'manifest.json').read_bytes()
        c_manifest = load(c_manifest_bytes)
        assert len(z.namelist()) == len(set(z.namelist())) == combo_link['logical_payloads']+1
        assert set(z.namelist()) == {r['path'] for r in c_manifest['entries']} | {'manifest.json'}
        combo_payloads = {r['path']:z.read(r['path']) for r in c_manifest['entries']}
    for row in c_manifest['entries']:
        assert sha(combo_payloads[row['path']]) == row['sha256'] and len(combo_payloads[row['path']]) == row['bytes']
    c_build_bytes = combo_payloads['metadata/bench-build.json']
    c_build = load(c_build_bytes)
    assert sha(c_build_bytes) == BUILD['W2']
    assert load(combo_payloads['producer/verification.json'])['verified_items'] == 366
    assert c_build['metadata_rebind']['original_build_sha256'] == '48dc256f11b7944f30e9be7358d749b6f8e33211f234171e738af3b8f7c3fe9f'
    assert {k:r['proof_items'] for k,r in c_build['producers'].items()} == {'baseline':358,'double':365,'checks':359,'both':366}
    # Exact source and compiler inputs remain checkable by the unchanged static checker.
    for name, digest in c_build['inputs_sha256'].items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    for tag in ['double-prereview','combination-prereview']:
        verdict = load(read(tag+'/verdict.json'))
        assert verdict['static_candidate_verdict'] == verdict['frozen_protocol_verdict'] == 'ACCEPT'
        seal = load(read(tag+'/review-artifacts.json'))
        rows = seal.get('sha256') or {r['path']:r['sha256'] for r in seal['entries']}
        for name, digest in rows.items():
            logical = tag+'/'+name
            if logical in manifest['payload_sha256']:
                assert sha(read(logical)) == digest
            else:
                assert any(r['review']==tag and r['name']==name and r['sha256']==digest for r in manifest['redundant_reviewer_snapshot_archives'])

    review_seal_bytes = read('measurement-review/review-artifacts.json')
    assert sha(review_seal_bytes) == manifest['independent_measurement_review_manifest_sha256'] == '8745ff70654273d48621c4411499ef881865b34aad3ee7275e67657c9ad77332'
    raw_bytes = (HERE/'frozen-measurements.zip').read_bytes()
    assert sha(raw_bytes) == manifest['raw_archive_sha256'] == RAW
    for name, row in load(review_seal_bytes)['files'].items():
        data = raw_bytes if name == 'frozen-measurements.zip' else read('measurement-review/'+name)
        assert sha(data) == row['sha256'] and len(data) == row['bytes']
    verdict = load(read('measurement-review/verdict.json'))
    assert verdict['review_status'] == 'ACCEPT evidence reconstruction' and verdict['independent_review'] == 'Astra Max'
    assert verdict['window_verdicts'] == {'W1':'NO-GO','W2':'NO-GO'}
    audit = load(read('measurement-review/audit.json'))
    assert audit['status'] == 'pass' and audit['frozen_measurements_sha256'] == RAW
    assert all(audit[k] is False for k in ['new_benchmark_or_process_management','pooled','postselection','statistical_retries'])
    replay_source = read('measurement-review/reconstruct.py')
    assert sha(replay_source) == 'fc9cff79827775ed63b1be934f6f526c6fc939816d17c44b333e6f4e3bfff456'
    replay = types.ModuleType('frozen_astra_reconstruction')
    replay.__file__ = str(HERE/'archived-reconstruct.py')
    exec(compile(replay_source, replay.__file__, 'exec'), replay.__dict__)
    binaries = {}
    for build, getter, prefix in [(d_build,d_read,'check-3/bench-build/'),(c_build,combo_payloads.__getitem__,'static/bench-build/')]:
        for row in build['binaries'].values():
            data = getter(prefix+Path(row['path']).name)
            assert sha(data) == row['sha256']
            binaries[row['path']] = data
    # Resolver exposes only read_bytes; no binary is loaded or executed.
    replay.win = lambda path: types.SimpleNamespace(read_bytes=lambda: binaries[path])
    plan_bytes = read('window-plan/plan.json')
    assert sha(plan_bytes) == '5511f0b78921d3e847d5624a6e27a7b257cea9783caf4922c94d694ba6e2b70c'
    plan = load(plan_bytes)
    for name, digest in plan['support_sha256'].items():
        assert sha(read('window-plan/'+name)) == digest
    results = {}
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as raw:
        assert len(raw.namelist()) == len(set(raw.namelist())) == 68
        assert {p:sha(raw.read(p)) for p in raw.namelist()} == manifest['raw_archive_members_sha256']
        for tag, kind in [('W1','double'),('W2','combination')]:
            expected = audit['windows'][tag]
            for name, digest in expected['input_sha256'].items():
                assert sha(raw.read(tag+'/'+name)) == digest
            host = load(raw.read(tag+'/host-receipt.json'))
            grant_bytes = read('window-plan/root-go-'+tag+'.json')
            grant = load(grant_bytes)
            assert host['root_grant_sha256'] == sha(grant_bytes)
            assert host['plan_sha256'] == sha(plan_bytes)
            assert grant['status'] == 'granted' and grant['timing_authorized'] is True and grant['all_active_workers_quiescent'] is True
            assert host['status'] == 'registered_runs_collected_performance_pending_analysis'
            assert host['avd_restored'] is True and host['pause_seconds'] == expected['host_pause_seconds'] < 480
            assert host['cpu'] == 8 and len(host['resume']) == 2 and all(r['nt_status']==0 and r['status']=='resumed' for r in host['resume'])
            restored = [r['process'] for r in host['observations'] if r.get('phase')=='after-finally-restore']
            assert {(r['pid'],r['start_ticks']) for r in restored} == {(17360,'639296423233476241'),(11540,'639296423237280818')}
            assert all(r['all_threads_suspended'] is False for r in restored)
            assert b'virtual device is running' in raw.read(tag+'/avd-status-after-finally.stdout.log')
            for command in host['commands']:
                assert command['returncode'] == 0
                for stream in ['stdout','stderr']:
                    assert sha(raw.read(tag+'/'+command['name']+'.'+stream+'.log')) == command[stream+'_sha256']
            for p in expected['provenance']:
                data = raw.read(tag+'/'+p['file'])
                assert sha(data) == p['sha256']
                record = load(data)
                assert record['status'] == 'pass' and record['cpu'] == 8
                assert record['dynamic_loader_environment'] == dict(LD_LIBRARY_PATH=None,LD_PRELOAD=None,LD_AUDIT=None)
                assert all(b['gmp_sha256']==GMP and b['gmp_realpath']=='/usr/lib/x86_64-linux-gnu/libgmp.so.10.5.0' for b in record['binaries'])
            runs = []
            for phase in [0,1]:
                name = f'double-run-{phase+1}' if tag=='W1' else f'combination-phase-{phase}'
                folder = zipfile.Path(raw, at=tag+'/'+name+'/')
                report = load((folder/'measurement.json').read_bytes())
                build_bytes = d_build_bytes if tag=='W1' else c_build_bytes
                assert report['build'] == load(build_bytes) and report['build_sha256'] == BUILD[tag]
                actual = replay.audit_run(folder, phase, kind, None)
                assert actual == expected['runs'][phase]
                assert actual['verdict'] == 'NO-GO'
                runs.append(dict(run_id=actual['run_id'],verdict=actual['verdict'],
                    samples=actual['accepted_samples'],calibrations=actual['calibrations'],actual=actual['actual']))
            results[tag] = dict(verdict='NO-GO',host_restored=True,pause_seconds=host['pause_seconds'],runs=runs)
    print(json.dumps(dict(status='pass',scope='VALID NEGATIVE EVIDENCE / NO-GO PROMOTION',
        native_files=57,public_readme_files=2,baseline_producer_items=358,windows=results,
        executed_benchmark=False,executed_verifier=False,executed_binary=False),indent=2))


if __name__ == '__main__':
    main()

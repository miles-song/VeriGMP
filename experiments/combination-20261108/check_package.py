#!/usr/bin/env python3
"""Offline evidence archive integrity and no-timing audit."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=Path(__file__).resolve().parent/'evidence'
BASE='515f1efa0d79bcb73272df9f54917f156decf1e1'
EXPECTED={'baseline':'7e8d3f151d3eda7c5a3df285f882618a26022d0f7b7661ff266812a4b123f446',
          'double':'ff3843b5b822bc9b2080bd0f26d6b604cf17b1147de193848e01ac8526c00f4a',
          'checks':'652224b6d79a7c2bc769b4abdb7ae955e975da87cdf55f2ed5b9fb90cefb9756',
          'both':'495f1689b95ebd7ed3151a13d6cec505ed77f80177adcc6dadc9567f8836f06b'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    archive=EVIDENCE/'evidence.zip';receipt=json.loads((EVIDENCE/'package.json').read_text())
    if archive.stat().st_size!=receipt['archive_bytes'] or sha(archive.read_bytes())!=receipt['archive_sha256']:
        raise RuntimeError('archive identity mismatch')
    with zipfile.ZipFile(archive) as bundle:
        names=bundle.namelist()
        if len(names)!=len(set(names)) or names.count('manifest.json')!=1:
            raise RuntimeError('archive path collision')
        manifest=json.loads(bundle.read('manifest.json'))
        if manifest['benchmark_executed'] or manifest['calibration_executed'] or manifest['performance_accepted']:
            raise RuntimeError('archive claims timing or acceptance')
        if len(manifest['entries'])!=manifest['entry_count']:
            raise RuntimeError('manifest count mismatch')
        for row in manifest['entries']:
            data=bundle.read(row['path'])
            if len(data)!=row['bytes'] or sha(data)!=row['sha256']:
                raise RuntimeError('evidence payload hash mismatch: '+row['path'])
        def read(path):return json.loads(bundle.read(path))
        prepared=read('source/prepared.json')
        if prepared['base']!=BASE or prepared['status']!='pass':
            raise RuntimeError('wrong fixed base')
        for label,digest in EXPECTED.items():
            if prepared['cells'][label]['native_manifest_sha256']!=digest:
                raise RuntimeError('four-cell source identity mismatch: '+label)
            for path,expected in prepared['cells'][label]['native_sha256'].items():
                if sha(bundle.read(label+'/'+path))!=expected:
                    raise RuntimeError('reconstructed native source mismatch: '+label+'/'+path)
        producer=read('producer/verification.json')
        check=read('static/verification.json')
        build=read('static/bench-build/bench-build.json')
        ops=read('operation-counts.json')
        harness=read('harness-fixtures/verification.json')
        if producer['status']!='full_library_pass' or producer['verified_items']!=366:
            raise RuntimeError('combined proof receipt mismatch')
        if producer['native_manifest_sha256']!=EXPECTED['both']:
            raise RuntimeError('combined proof source mismatch')
        if check['status']!='pass' or build['status']!='static_pass':
            raise RuntimeError('static gate receipt mismatch')
        if len(ops['rows'])!=86 or len([r for r in ops['rows'] if r['both_factors_reached']])<11:
            raise RuntimeError('reachability receipt mismatch')
        if harness['status']!='pass' or harness['benchmark_executed']:
            raise RuntimeError('harness receipt mismatch')
        for label,row in build['producers'].items():
            if row['source_native_manifest_sha256']!=EXPECTED[label] or not row['all_50_native_rust_hashes_equal']:
                raise RuntimeError('producer source binding mismatch: '+label)
        for label,row in build['binaries'].items():
            if sha(bundle.read('static/bench-build/'+Path(row['path']).name))!=row['sha256']:
                raise RuntimeError('benchmark binary mismatch: '+label)
    output=dict(status='pass',payloads=receipt['logical_payloads'],source_cells=4,
        combined_verified_items=366,operation_cells=86,benchmark_executed=False,
        archive_sha256=receipt['archive_sha256'])
    (EVIDENCE/'package-check.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__=='__main__':
    main()

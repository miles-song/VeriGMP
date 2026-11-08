#!/usr/bin/env python3
"""Package immutable source, proof, untimed gate and frozen-build evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile
from common import LABELS, file_sha, write_json

FEATURE = Path(__file__).resolve().parent
EVIDENCE = FEATURE / 'evidence'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','producer','check','operations','harness'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    source=args.source.resolve();producer=args.producer.resolve();check=args.check.resolve()
    operations=args.operations.resolve();harness=args.harness.resolve()
    if json.loads((source/'prepared.json').read_text())['status']!='pass':
        raise RuntimeError('unprepared source')
    if json.loads((producer/'verification.json').read_text())['status']!='full_library_pass':
        raise RuntimeError('combined proof missing')
    if json.loads((check/'verification.json').read_text())['status']!='pass':
        raise RuntimeError('static gate missing')
    if json.loads((check/'bench-build/bench-build.json').read_text())['benchmark_executed']:
        raise RuntimeError('benchmark already executed before prereview')
    if json.loads(operations.read_text())['status']!='pass':
        raise RuntimeError('operation-count receipt missing')
    if json.loads((harness/'verification.json').read_text())['benchmark_executed']:
        raise RuntimeError('harness fixtures are not untimed')
    EVIDENCE.mkdir(exist_ok=True)
    archive=EVIDENCE/'evidence.zip';manifest_path=EVIDENCE/'manifest.json'
    roots=[('source',source),('producer',producer),('static',check),
           ('harness-fixtures',harness)]
    payload=[]
    for prefix,root in roots:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                name=(Path(prefix)/path.relative_to(root)).as_posix()
                payload.append((name,path))
    payload.append(('operation-counts.json',operations))
    payload.sort(key=lambda row:row[0])
    if len({name for name,_ in payload})!=len(payload):
        raise RuntimeError('duplicate evidence path')
    entries=[dict(path=name,bytes=path.stat().st_size,sha256=file_sha(path)) for name,path in payload]
    manifest=dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),
        benchmark_executed=False,calibration_executed=False,performance_accepted=False,
        entry_count=len(entries),entries=entries)
    write_json(manifest_path,manifest)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for name,path in payload:
            bundle.write(path,name)
        bundle.write(manifest_path,'manifest.json')
    receipt=dict(status='pass',archive='evidence.zip',archive_bytes=archive.stat().st_size,
        archive_sha256=file_sha(archive),manifest='manifest.json',manifest_sha256=file_sha(manifest_path),
        logical_payloads=len(entries),benchmark_executed=False,calibration_executed=False,
        payload_roots=[str(path) for _,path in roots]+[str(operations)])
    write_json(EVIDENCE/'package.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()

"""Record the explicitly authorized public-origin feature backup."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent/'VeriGMP-negative-experiments-20261108'
HEAD='840e2ff09ff5cfc5f0c3b967f1d2c941cb627bdb'
BRANCH='codex/gmp-fused-interpolation-20261108'
report=dict(status='running',head=HEAD,branch=BRANCH,root_destination_authorized=True,
    destination='origin',visibility='public',changed_visibility=False,commands=[])
def save():(OUT/'backup.json').write_text(json.dumps(report,indent=2)+'\n')
def run(name,argv):
    row=dict(name=name,argv=argv,cwd=str(ROOT),start_utc=datetime.now(timezone.utc).isoformat())
    report['commands'].append(row);save()
    result=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120)
    for stream in ('stdout','stderr'):
        data=getattr(result,stream);(OUT/(name+'.'+stream+'.log')).write_bytes(data)
        row[stream+'_sha256']=hashlib.sha256(data).hexdigest()
    row.update(returncode=result.returncode,stop_utc=datetime.now(timezone.utc).isoformat());save()
    assert result.returncode==0,(name,result.stderr.decode(errors='replace'))
    return result.stdout.decode().strip()
try:
    assert run('status',['git','status','--porcelain'])==''
    assert run('head',['git','rev-parse','HEAD'])==HEAD
    assert run('branch',['git','branch','--show-current'])==BRANCH
    report['origin_url']=run('origin',['git','remote','get-url','origin'])
    assert report['origin_url']=='git@github.com:miles-song/VeriGMP.git'
    visibility=json.loads(run('visibility',['gh','repo','view','miles-song/VeriGMP','--json','isPrivate,nameWithOwner,url']))
    assert visibility['isPrivate'] is False
    report['github_visibility']=visibility
    run('push',['git','push','origin','HEAD:refs/heads/'+BRANCH])
    remote=run('remote-confirmation',['git','ls-remote','--heads','origin','refs/heads/'+BRANCH])
    assert remote==HEAD+'\trefs/heads/'+BRANCH
    report.update(status='public_origin_backup_confirmed',confirmed_remote_sha=HEAD)
except BaseException as error:
    report.update(status='fail',failure=repr(error));raise
finally:save()
print(json.dumps(dict(status=report['status'],head=HEAD,visibility='public',branch=BRANCH),indent=2))

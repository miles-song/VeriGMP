"""Confirm that the exact follow-up source SHA is on the authorized origin."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

out=Path(__file__).resolve().parent
root=Path('/mnt/c/Users/23247/.codex/worktrees/gmp-fused-interpolation-20261108/VeriGMP-negative-experiments-20261108')
git=['/mnt/c/Program Files/Git/cmd/git.exe','-C','C:/Users/23247/.codex/worktrees/gmp-fused-interpolation-20261108/VeriGMP-negative-experiments-20261108']
head='cb9f26860accdfb3471e5e668b42a6a732da3608'
branch='codex/gmp-fused-interpolation-20261108'
record=dict(status='running',root_destination_authorized=True,destination='origin',visibility='public',
            changed_visibility=False,commands=[])
def save():(out/'backup.json').write_text(json.dumps(record,indent=2)+'\n')
def call(name,argv):
    row=dict(name=name,argv=argv,cwd=str(root),start_utc=datetime.now(timezone.utc).isoformat())
    record['commands'].append(row);save()
    result=subprocess.run(argv,cwd=root,capture_output=True,timeout=120)
    for stream in ('stdout','stderr'):
        data=getattr(result,stream);(out/(name+'.'+stream+'.log')).write_bytes(data)
        row[stream+'_sha256']=hashlib.sha256(data).hexdigest()
    row.update(returncode=result.returncode,stop_utc=datetime.now(timezone.utc).isoformat());save()
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
    return result.stdout.decode().strip()
try:
    record['head']=call('head',git+['rev-parse','HEAD'])
    assert record['head']==head
    assert call('status',git+['status','--porcelain'])==''
    assert call('branch',git+['branch','--show-current'])==branch
    record['origin_url']=call('origin',git+['remote','get-url','origin'])
    assert record['origin_url']=='git@github.com:miles-song/VeriGMP.git'
    record['github_visibility']=json.loads(call('visibility',['/mnt/c/Program Files/GitHub CLI/gh.exe','repo','view','miles-song/VeriGMP','--json','isPrivate,nameWithOwner,url']))
    assert record['github_visibility']['isPrivate'] is False
    remote=call('remote-confirmation',git+['ls-remote','--heads','origin','refs/heads/'+branch])
    assert remote==head+'\trefs/heads/'+branch
    record.update(status='public_origin_backup_confirmed',confirmed_remote_sha=head)
except BaseException as error:
    record.update(status='fail',failure=repr(error));raise
finally:save()
print(json.dumps({k:record[k] for k in ('status','head','visibility','branch')},indent=2))

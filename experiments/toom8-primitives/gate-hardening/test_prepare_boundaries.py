"""Exercise the actual preparation CLI against destination-escape manifests."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
source=Path(__file__).with_name('prepare.py').read_bytes();results=[]
with tempfile.TemporaryDirectory(prefix='verigmp-prepare-boundaries-') as temporary:
    root=Path(temporary).resolve();archives=root/'archives';gate=archives/'gate-hardening';gate.mkdir(parents=True)
    (gate/'prepare.py').write_bytes(source);data=b'public fixture\n';(archives/'known.rs').write_bytes(data);digest=hashlib.sha256(data).hexdigest()
    sentinel=root/'escape.rs';sentinel.write_bytes(b'preserve\n')
    names=['../escape.rs','sub/../../escape.rs',str(sentinel),'..\\escape.rs','nested/../escape.rs','valid/../escape.rs','candidate/native/known.rs']
    for i,name in enumerate(names):
        out=root/f'output-{i}'
        feature={'accepted_gate':'fixture','original_verification_sha256':'0'*64,'checker':'unused.py',
            'source_map':{name:{'archive_path':'known.rs','published_sha256':digest,'original_sha256':digest,'bytes_exact':True}}}
        (gate/'index.json').write_text(json.dumps({'features':{'wide-odd':feature}}))
        process=subprocess.run([sys.executable,str(gate/'prepare.py'),'--feature','wide-odd','--output',str(out)],capture_output=True,text=True)
        valid=i==len(names)-1
        assert (process.returncode==0)==valid,(i,process.stdout,process.stderr)
        assert sentinel.read_bytes()==b'preserve\n'
        if valid:assert (out/name).read_bytes()==data
        else:assert 'Unsafe destination name' in process.stderr and not list(out.rglob('known.rs'))
        results.append({'case':i,'accepted':valid,'returncode':process.returncode})
print(json.dumps({'status':'pass','source_sha256':hashlib.sha256(source).hexdigest(),'escape_names_rejected':6,'valid_reconstruction':1,'cases':results}))

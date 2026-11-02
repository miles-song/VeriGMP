"""Check actual CLI destination validation and preserved existing destinations."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile
source=Path(__file__).with_name('prepare.py').read_bytes();results=[]
with tempfile.TemporaryDirectory(prefix='verigmp-normalization-boundaries-') as temporary:
    root=Path(temporary).resolve();archive=root/'archive';archive.mkdir();(archive/'evidence').mkdir()
    (archive/'prepare.py').write_bytes(source);sentinel=root/'escape.rs';sentinel.write_bytes(b'preserve\n')
    names=['../escape.rs','sub/../../escape.rs',str(sentinel),'..\\escape.rs','nested/../escape.rs','valid/../escape.rs']
    for i,name in enumerate(names):
        out=root/f'output-{i}';(archive/'evidence/verification.json').write_text(json.dumps({'source_sha256':{name:'0'*64}}))
        process=subprocess.run([sys.executable,str(archive/'prepare.py'),'--output',str(out)],capture_output=True,text=True)
        assert process.returncode!=0 and 'Unsafe destination name' in process.stderr
        assert sentinel.read_bytes()==b'preserve\n' and not out.exists()
        results.append({'case':i,'returncode':process.returncode,'escape_rejected':True})
    existing=root/'existing';existing.mkdir();(existing/'sentinel').write_bytes(b'preserve\n')
    process=subprocess.run([sys.executable,str(archive/'prepare.py'),'--output',str(existing)],capture_output=True,text=True)
    assert process.returncode!=0 and 'Refusing to overwrite a stage' in process.stderr and (existing/'sentinel').read_bytes()==b'preserve\n'
print(json.dumps({'status':'pass','source_sha256':hashlib.sha256(source).hexdigest(),'escape_names_rejected':6,'existing_destination_preserved':True,'cases':results}))

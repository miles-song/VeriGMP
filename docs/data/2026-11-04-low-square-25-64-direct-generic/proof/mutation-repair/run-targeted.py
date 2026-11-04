#!/usr/bin/env python3
"""Freeze and verify the unchanged arithmetic with the repaired mutation gate."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


root=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve()
output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'scripts'))
from verify import environment
from verify_toom import check_toom


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


env=environment()
verifier=(root/'deps/verus/verus-x86-linux/verus').resolve()
pin=json.loads((root/'native/toolchain.json').read_text())
tools=[verifier]+[verifier.parent/name for name in ('rust_verify','z3','vstd.vir','libvstd.rlib',
    'libverus_builtin.rlib','libverus_builtin_macros.so','libverus_state_machines_macros.so')]
tool_hashes={p.name:digest(p) for p in tools}
files=sorted((root/'native').rglob('*.rs'))+sorted((root/'native/controls').glob('*.cpp'))
files+=sorted((root/'native').glob('*.json'))+sorted((root/'scripts').glob('*.py'))
inputs={p.relative_to(root):p.read_bytes() for p in files}
hashes={p.as_posix():hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest() for p,data in inputs.items()}
manifest=''.join(f'{p}\t{h}\n' for p,h in sorted(hashes.items()))
(output/'source-sha256.tsv').write_text(manifest,encoding='utf-8')
report={'status':'running','arithmetic_source_commit':'810b867e7b4e2c43c82e107db2a79c425e52bf29',
    'parent_receipt_commit':'0d3c8e9f9fa827ac01c9a760efe35c99fd29cce3',
    'source_hashes_lf':hashes,'source_manifest_sha256':digest(output/'source-sha256.tsv'),
    'runner_sha256':digest(Path(__file__)),'tool_sha256':tool_hashes,'commands':[],
    'performance':'Existing matched ABBA/BAAB data retained; no timing performed in this repair gate'}
target=output/'verification.json'


def run(command,log,cwd):
    report['commands'].append(list(map(str,command)))
    result=subprocess.run(list(map(str,command)),cwd=cwd,env=env,text=True,capture_output=True,timeout=240)
    text=result.stdout+result.stderr
    (output/log).write_text(text,encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Command failed: {log}; exit={result.returncode}')
    return text


try:
    version=run([verifier,'--version'],'toolchain.log',root)
    if pin['verus_version'] not in version or pin['rust_toolchain'] not in version:
        raise RuntimeError('Verifier/Rust identity mismatch')
    report['tool_version']=version
    report['rustc']=run(['rustup','run',pin['rust_toolchain'],'rustc','-vV'],'rustc.log',root)
    forbidden=r'\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)'
    for path,data in inputs.items():
        if path.suffix=='.rs' and re.search(forbidden,data.decode()):
            raise RuntimeError(f'Unapproved proof escape: {path}')
    with tempfile.TemporaryDirectory(prefix='verigmp-leaf-mutation-') as temp:
        snapshot=Path(temp)
        for path,data in inputs.items():
            destination=snapshot/path
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(data)
        library=output/'libverigmp.rlib'
        metadata=output/'verigmp.vir'
        log=run([verifier,snapshot/'native/lib.rs','--crate-name','verigmp','--crate-type','lib',
            '--export',metadata,'--compile','-O','-o',library],'library.log',snapshot)
        match=re.search(r'verification results:: (\d+) verified, 0 errors',log)
        if not match:
            raise RuntimeError('Missing successful library verification')
        report['library']={'verified_items':int(match[1]),'files':{p.name:digest(p) for p in (library,metadata)}}
        report['toom']=check_toom(snapshot,verifier,env,output/'toom',measure=False)
        if any((snapshot/path).read_bytes()!=data for path,data in inputs.items()):
            raise RuntimeError('Mutated source was not restored in the immutable snapshot')
    if any((root/path).read_bytes()!=data for path,data in inputs.items()):
        raise RuntimeError('Source changed during targeted verification')
    if any(digest(p)!=tool_hashes[p.name] for p in tools):
        raise RuntimeError('Tool bytes changed during targeted verification')
    report['status']='pass'
except Exception as error:
    report.update(status='error',error=f'{type(error).__name__}: {error}')
finally:
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','error','library') if k in report},indent=2))
raise SystemExit(0 if report['status']=='pass' else 1)

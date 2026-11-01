#!/usr/bin/env python3
"""Verify, compile and measure one immutable arithmetic-library snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from verify_limbs import check_limbs
from verify_pow2 import check_pow2
from verify_multiply import check_multiply
from verify_fast import check_fast
from verify_toom import check_toom

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment():
    env=dict(os.environ)
    if (ROOT/'deps/cargo/bin/rustup').exists():
        env['CARGO_HOME']=str(ROOT/'deps/cargo');env['RUSTUP_HOME']=str(ROOT/'deps/rustup')
        env['PATH']=str(ROOT/'deps/cargo/bin')+os.pathsep+env['PATH']
    return env


def git_identity():
    def git(*args):
        result=subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True)
        return result.stdout.strip() if result.returncode==0 else None
    return {'head':git('rev-parse','HEAD'),'tracked_status':git('status','--porcelain','--untracked-files=no'),
            'invoking_ci_commit':os.environ.get('GITHUB_SHA')}


def verify(output,export_dir):
    output.mkdir(parents=True,exist_ok=True)
    report={'status':'running','scope':'VeriGMP arithmetic refinement','git':git_identity()}
    target=output/'verification.json';target.write_text(json.dumps(report)+'\n')
    try:
        env=environment();pin=json.loads((ROOT/'native/toolchain.json').read_text())
        verifier=Path(env.get('VERUS_BIN',ROOT/'deps/verus/verus-x86-linux/verus')).resolve()
        def run(command,log,cwd=ROOT):
            result=subprocess.run(list(map(str,command)),cwd=cwd,env=env,text=True,capture_output=True,timeout=240)
            content=result.stdout+result.stderr;(output/log).write_text(content,encoding='utf-8')
            if result.returncode:raise RuntimeError(f'Command failed; inspect {log}')
            return content
        version=run([verifier,'--version'],'toolchain.log')
        if pin['verus_version'] not in version or pin['rust_toolchain'] not in version:
            raise RuntimeError('Verifier/Rust version mismatch')
        tools=[verifier]+[verifier.parent/n for n in ('rust_verify','z3','vstd.vir','libvstd.rlib',
            'libverus_builtin.rlib','libverus_builtin_macros.so','libverus_state_machines_macros.so')]
        identities={p.name:digest(p) for p in tools}
        report['actual_toolchain']={'version_output':version,'file_sha256':identities,
            'rustc':run(['rustup','run',pin['rust_toolchain'],'rustc','-vV'],'rustc.log')}
        sources=sorted((ROOT/'native').rglob('*.rs'))
        files=sources+sorted((ROOT/'native/controls').glob('*.cpp'))+sorted((ROOT/'scripts').glob('*.py'))
        files+=sorted((ROOT/'native').glob('*.json'))
        files+=[ROOT/p for p in ('README.md','AGENTS.md','LICENSE','.gitattributes','.gitignore','.github/workflows/verify.yml')]
        inputs={p.relative_to(ROOT):p.read_bytes() for p in files}
        report['source_hashes_lf']={p.as_posix():hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest() for p,data in inputs.items()}
        forbidden=r'\b(assume|admit|axiom)\s*\(|verifier::(external_body|external_fn_specification|external|trusted|verify\s*=\s*false)'
        for p in sources:
            if re.search(forbidden,inputs[p.relative_to(ROOT)].decode()):raise RuntimeError(f'Unapproved proof escape: {p}')
        with tempfile.TemporaryDirectory(prefix='verigmp-') as temp:
            snapshot=Path(temp)
            for path,data in inputs.items():
                destination=snapshot/path;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            library=snapshot/'libverigmp.rlib';metadata=snapshot/'verigmp.vir'
            log=run([verifier,snapshot/'native/lib.rs','--crate-name','verigmp','--crate-type','lib',
                '--export',metadata,'--compile','-O','-o',library],'library.log',snapshot)
            match=re.search(r'verification results:: (\d+) verified, 0 errors',log)
            if not match:raise RuntimeError('Missing successful library verification')
            report['library']={'verified_items':int(match[1]),'files':{p.name:digest(p) for p in (library,metadata)}}
            for name,check in [('limbs',check_limbs),('pow2',check_pow2),('multiply',check_multiply),('fast_multiply',check_fast),('toom',check_toom)]:
                report[name]=check(snapshot,verifier,env,output/name)
            if any((ROOT/p).read_bytes()!=data for p,data in inputs.items()):raise RuntimeError('Source changed during verification')
            if any(digest(p)!=identities[p.name] for p in tools):raise RuntimeError('Verifier files changed during verification')
            export_dir.mkdir(parents=True,exist_ok=True)
            for p in (library,metadata):shutil.copy2(p,export_dir/p.name)
        report['status']='pass'
    except Exception as error:
        report.update(status='error',error=f'{type(error).__name__}: {error}')
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ('status','error','library')},indent=2))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--export-dir',type=Path,default=ROOT/'build')
    args=parser.parse_args();raise SystemExit(verify(args.output.resolve(),args.export_dir.resolve()))

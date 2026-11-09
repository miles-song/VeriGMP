#!/usr/bin/env python3
"""External operational receipt for one focused gate; never compiles or times."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

OUT=Path(__file__).resolve().parent
ROOT=Path('/mnt/c/Users/23247/.codex/worktrees/gmp-fused-interpolation-20261108/VeriGMP-negative-experiments-20261108')
WINDOWS_ROOT='C:/Users/23247/.codex/worktrees/gmp-fused-interpolation-20261108/VeriGMP-negative-experiments-20261108'
HEAD='840e2ff09ff5cfc5f0c3b967f1d2c941cb627bdb'
BASE='4510b46e4010dd287c9cf760f0195f2edc32e1f7'
DEPS=Path('/mnt/e/3sat/VeriCount/deps')
BASELINE=Path('/mnt/e/3sat/VeriGMP-precondition-evidence-20261108/baseline-binding')
GIT=['/mnt/c/Program Files/Git/cmd/git.exe','-C',WINDOWS_ROOT]

def now():return datetime.now(timezone.utc).isoformat()
def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):
    with Path(path).open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')
def git(*args):return subprocess.check_output(GIT+list(args),stderr=subprocess.PIPE,timeout=60)
def manifest(folder):
    return {p.relative_to(folder).as_posix():file_sha(p) for p in sorted((folder/'native').rglob('*')) if p.is_file()}

def bind():
    receipt=dict(status='running',phase='source-tool-baseline-binding',start_utc=now(),driver_pid=os.getpid(),
        full_native_proof=False,compile=False,timing=False,verus_invoked=False,git_argv=GIT)
    save(OUT/'binding.json',receipt)
    try:
        assert not git('status','--porcelain').strip()
        assert git('rev-parse','HEAD').decode().strip()==HEAD
        names=git('ls-tree','-r','--name-only',HEAD,'native').decode().splitlines()
        candidate={name:git('show',HEAD+':'+name) for name in names}
        baseline={name:git('show',BASE+':'+name) for name in names}
        expected={name:sha(data) for name,data in candidate.items()}
        for name,data in candidate.items():
            assert (ROOT/name).read_bytes()==data
            target=OUT/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        receipt['source']=dict(head=HEAD,tree=git('rev-parse',HEAD+'^{tree}').decode().strip(),
            baseline=BASE,baseline_native_tree=git('rev-parse',BASE+':native').decode().strip(),
            source_sha256=expected,baseline_sha256={name:sha(data) for name,data in baseline.items()},
            manifest_sha256=sha(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()))
        assert manifest(OUT/'source')==expected
        pin=json.loads(candidate['native/toolchain.json'])
        archive=DEPS/'verus-download'/pin['archive']
        assert file_sha(archive)==pin['sha256']
        verifier=DEPS/'verus/verus-x86-linux/verus'
        hashes={}
        with zipfile.ZipFile(archive) as bundle:
            for name in ('verus','rust_verify','z3','vstd.vir','libvstd.rlib','libverus_builtin.rlib',
                         'libverus_builtin_macros.so','libverus_state_machines_macros.so'):
                expected_hash=sha(bundle.read('verus-x86-linux/'+name))
                assert file_sha(verifier.parent/name)==expected_hash, name
                hashes[name]=expected_hash
        sysroot=DEPS/'rustup/toolchains'/pin['rust_toolchain']
        for path in [DEPS/'cargo/bin/rustup',sysroot/'bin/rustc',*sorted((sysroot/'lib').glob('*LLVM*.so*')),
                     *sorted((sysroot/'lib').glob('libLLVM.so.*')),*sorted((sysroot/'lib').glob('librustc_driver*.so'))]:
            hashes[str(path)]=file_sha(path)
        receipt['tools']=dict(archive_sha256=pin['sha256'],actual_sha256=hashes,
            version_file=json.loads((verifier.parent/'version.json').read_text()),
            python_executable=sys.executable,python_sha256=file_sha(sys.executable))
        old=json.loads((BASELINE/'verification.json').read_text())
        assert old['status']=='pass' and old['library_verified_items']==358
        rust_hashes={name:sha(data) for name,data in baseline.items() if name.endswith('.rs')}
        old_hashes={name:hashval for name,hashval in old['source_git']['source_sha256'].items()
                    if name.startswith('native/') and name.endswith('.rs')}
        assert rust_hashes==old_hashes and len(rust_hashes)==50
        old_tools=old['toolchain']['actual_file_sha256']
        for name,digest in hashes.items():
            basename=Path(name).name
            matches=[value for path,value in old_tools.items() if Path(path).name==basename]
            assert len(matches)==1 and matches[0]==digest, name
        original=Path(old['producer_reuse']['source'])
        build=old['producer_reuse']['original_complete_build_command']
        assert build['returncode']==0 and all(flag in build['argv'] for flag in ('--no-cheating','--compile','-O'))
        for stream in ('stdout','stderr'):
            source=original/('library-proof-release.'+stream+'.log')
            assert file_sha(source)==build[stream+'_sha256']
            shutil.copyfile(source,OUT/('baseline-original.'+stream+'.log'))
        text=(OUT/'baseline-original.stdout.log').read_text()+(OUT/'baseline-original.stderr.log').read_text()
        assert re.findall(r'(?m)^verification results:: (\d+) verified, 0 errors$',text)==['358']
        exports={}
        for name in ('libverigmp.rlib','verigmp.vir'):
            assert file_sha(BASELINE/name)==old['exports_sha256'][name]
            assert file_sha(original/name)==old['exports_sha256'][name]
            exports[name]=old['exports_sha256'][name]
        shutil.copyfile(BASELINE/'verification.json',OUT/'baseline-verification.json')
        receipt['baseline']=dict(reproved=False,library_verified_items=358,rust_files_checked=50,
            source_sha256=rust_hashes,producer_receipt_sha256=file_sha(BASELINE/'verification.json'),
            original_complete_build_command=build,exports_sha256=exports,all_pinned_tools_equal=True)
        receipt.update(status='binding_pass',stop_utc=now())
    except BaseException as error:
        receipt.update(status='fail',failure=repr(error),stop_utc=now());raise
    finally:save(OUT/'binding.json',receipt)
    print(json.dumps(dict(status=receipt['status'],head=HEAD,baseline_items=358,
        manifest_sha256=receipt['source']['manifest_sha256'],binding_sha256=file_sha(OUT/'binding.json'))),flush=True)

def focus():
    binding=json.loads((OUT/'binding.json').read_text());assert binding['status']=='binding_pass'
    backup=json.loads((OUT/'backup.json').read_text())
    assert backup['head']==HEAD and backup['confirmed_remote_sha']==HEAD and backup['root_destination_authorized']
    assert manifest(OUT/'source')==binding['source']['source_sha256']
    for name,digest in binding['tools']['actual_sha256'].items():
        path=(DEPS/'verus/verus-x86-linux'/name) if '/' not in name else Path(name)
        assert file_sha(path)==digest
    env=dict(os.environ,CARGO_HOME=str(DEPS/'cargo'),RUSTUP_HOME=str(DEPS/'rustup'),
             RUSTUP_TOOLCHAIN='1.99.1-x86_64-unknown-linux-gnu')
    env['PATH']=str(DEPS/'cargo/bin')+os.pathsep+env['PATH']
    argv=[str(DEPS/'verus/verus-x86-linux/verus'),'native/lib.rs','--crate-type','lib','--crate-name','verigmp',
          '--verify-module','toom_words','--no-cheating','--multiple-errors','0','--num-threads','2']
    report=dict(status='running',phase='focused-frontend-type-helper',head=HEAD,argv=argv,
        cwd=str(OUT/'source'),start_utc=now(),driver_pid=os.getpid(),compile=False,full_native_proof=False,timing=False,
        binding_sha256=file_sha(OUT/'binding.json'),backup_sha256=file_sha(OUT/'backup.json'),
        driver_sha256=file_sha(__file__),stdout='focused.stdout.log',stderr='focused.stderr.log',
        selected_environment={k:env[k] for k in ('CARGO_HOME','RUSTUP_HOME','RUSTUP_TOOLCHAIN','PATH')},
        terminal=dict(stdin_isatty=sys.stdin.isatty(),stdout_isatty=sys.stdout.isatty(),tty_name=os.ttyname(0) if sys.stdin.isatty() else None))
    with (OUT/'focused.stdout.log').open('wb') as stdout,(OUT/'focused.stderr.log').open('wb') as stderr:
        process=subprocess.Popen(argv,cwd=OUT/'source',env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        report['verus_launcher_pid']=process.pid
        save(OUT/'focused.json',report)
        print(json.dumps(dict(status='launched',driver_pid=os.getpid(),verus_launcher_pid=process.pid,
                             argv=argv,terminal=report['terminal'])),flush=True)
        try:result=process.wait(timeout=900)
        except subprocess.TimeoutExpired:
            process.terminate();process.wait(timeout=30);report.update(status='timeout',stop_utc=now());save(OUT/'focused.json',report);raise
    text=(OUT/'focused.stdout.log').read_text()+(OUT/'focused.stderr.log').read_text()
    summary=re.findall(r'(?m)^verification results:: (\d+) verified, (\d+) errors \(partial verification with `--verify-\*`\)$',text)
    fatal=bool(re.search(r'(?i)\bunknown\b|\brlimit\b|resource\s+limit|timed?\s*out|\btimeout\b|error\[E\d+\]|unexpected token|failed\s+to\s+(?:load|typecheck)',text))
    report.update(returncode=result,stop_utc=now(),summary=summary,fatal_or_frontend_diagnostic=fatal,
                  stdout_sha256=file_sha(OUT/'focused.stdout.log'),stderr_sha256=file_sha(OUT/'focused.stderr.log'))
    report['status']='focused_pass' if result==0 and len(summary)==1 and summary[0][1]=='0' and not fatal else 'fail'
    assert manifest(OUT/'source')==binding['source']['source_sha256']
    save(OUT/'focused.json',report)
    print(json.dumps(dict(status=report['status'],returncode=result,summary=summary,
                         focused_sha256=file_sha(OUT/'focused.json'))),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('bind','focus'))
    args=parser.parse_args();bind() if args.phase=='bind' else focus()

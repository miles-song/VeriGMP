#!/usr/bin/env python3
"""Source-bound four-cell oracle, mutant, codegen and build gate; never timing."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from common import *
from operations import generate as operation_counts
from square_oracle import generate_low
sys.path.insert(0,str(ROOT/'experiments/arithmetic-precondition-checks-20261108'))
from oracle import generate as legacy_oracle
from verus_logs import self_check, strict_semantic_rejection


def rust_sources(mapping):
    return {k:v for k,v in mapping.items() if k.startswith('native/') and k.endswith('.rs')}


def bind_producers(args, prepared, data, tools, out):
    roots={label:getattr(args,label).resolve() for label in LABELS}
    reports={};bindings={}
    for label,folder in roots.items():
        target=out/'producers'/label;target.mkdir(parents=True)
        files=['libverigmp.rlib','verigmp.vir']
        if label=='baseline':
            report=json.loads((folder/'verification.json').read_text())
            if report['status']!='pass' or report['library_verified_items']!=358:
                raise RuntimeError('wrong accepted baseline receipt')
            native=report['source_git']['source_sha256']
            old_tools={Path(k).name:v for k,v in report['toolchain']['actual_file_sha256'].items()}
            exports=report['exports_sha256'];items=358
            command=report['producer_reuse']['original_complete_build_command']
            original=Path(report['producer_reuse']['source'])
            # Include the original full-proof raw stream, validated against its receipt.
            for stream in ('stdout','stderr'):
                source=original/('library-proof-release.'+stream+'.log')
                digest=command[stream+'_sha256']
                if file_sha(source)!=digest:
                    raise RuntimeError('baseline original proof stream changed')
                shutil.copyfile(source,target/('library.'+stream+'.log'))
            proof_text=(target/'library.stdout.log').read_text()+(target/'library.stderr.log').read_text()
            if positive(command['returncode'],proof_text)!=358:
                raise RuntimeError('wrong baseline proof summary')
            files+=['verification.json']
        elif label=='checks':
            report=json.loads((folder/'build-command.json').read_text())
            source=json.loads((folder/'build-source.json').read_text())
            gate_path=args.checks_gate.resolve()
            gate=json.loads(gate_path.read_text())
            if gate['status']!='pass' or gate['producer']['build_source']!=source or gate['producer']['build_command']!=report:
                raise RuntimeError('historical checked-worker proof binding mismatch')
            if source['head']!=CHECKS:
                raise RuntimeError('wrong historical checked-worker source')
            native=source['source_sha256'];old_tools=gate['tools']['actual_sha256']
            exports=report['outputs_sha256'];items=359
            if positive(report['returncode'],(folder/'library.stdout.log').read_text()+(folder/'library.stderr.log').read_text())!=items:
                raise RuntimeError('wrong checked-worker proof summary')
            for name,digest in exports.items():
                if file_sha(folder/name)!=digest:
                    raise RuntimeError('historical producer artifact changed: '+name)
            shutil.copyfile(gate_path,target/'historical-focused-gate.json')
            files+=['build-command.json','build-source.json','library.stdout.log','library.stderr.log']
        else:
            report=json.loads((folder/'verification.json').read_text())
            if report['status']!='full_library_pass':
                raise RuntimeError('missing full producer proof: '+label)
            if label=='double':
                if report['source']['head']!=DOUBLE or report['verified_items']!=365:
                    raise RuntimeError('wrong standalone double producer')
                native=report['source']['sha256'];items=365
            else:
                if report['native_manifest_sha256']!=data['cells']['both']['native_manifest_sha256'] or report['cell']!='both':
                    raise RuntimeError('combined prepared/proof identity mismatch')
                native=report['native_sha256'];items=report['verified_items']
                if items!=366:
                    raise RuntimeError('combined full proof count changed unexpectedly')
            old_tools=report['tools']['sha256'];exports=report['exports_sha256']
            command=next(row for row in report['commands'] if row.get('name')=='library' or 'native/lib.rs' in row['argv'])
            if command['returncode'] or '--no-cheating' not in command['argv'] or '--compile' not in command['argv'] or '-O' not in command['argv']:
                raise RuntimeError('wrong complete proof command')
            for stream in ('stdout','stderr'):
                if file_sha(folder/('library.'+stream+'.log'))!=command[stream+'_sha256']:
                    raise RuntimeError('producer proof stream changed')
            if positive(command['returncode'],(folder/'library.stdout.log').read_text()+(folder/'library.stderr.log').read_text())!=items:
                raise RuntimeError('producer summary mismatch')
            files+=['verification.json','library.stdout.log','library.stderr.log']
        if rust_sources(native)!=rust_sources(data['cells'][label]['native_sha256']):
            raise RuntimeError('all-native-Rust producer identity mismatch: '+label)
        if any(old_tools[name]!=digest for name,digest in tools['sha256'].items()):
            raise RuntimeError('historical producer tool mismatch: '+label)
        for name in ('libverigmp.rlib','verigmp.vir'):
            if file_sha(folder/name)!=exports[name]:
                raise RuntimeError('producer export mismatch: '+label+'/'+name)
        for name in files:
            shutil.copyfile(folder/name,target/name)
        bindings[label]=dict(source_native_manifest_sha256=data['cells'][label]['native_manifest_sha256'],
            proof_items=items,proof_reused=label!='both',all_50_native_rust_hashes_equal=True,
            exports_sha256={name:file_sha(target/name) for name in ('libverigmp.rlib','verigmp.vir')},
            payload_sha256={p.name:file_sha(p) for p in sorted(target.iterdir())})
        reports[label]=report
    return {label:out/'producers'/label/'libverigmp.rlib' for label in LABELS},bindings


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','deps-root','baseline','double','checks','both','checks-gate','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();prepared,data=checked_prepared(args.prepared)
    out=args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError('use fresh external check output')
    out.mkdir(parents=True)
    report=dict(status='running',benchmark_run=False,calibration_run=False,commands=[],
                prepared_sha256=file_sha(prepared/'prepared.json'),source_head=data['source_head'])
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');run=command_runner(out,report,env)
    try:
        verifier,pin,tools=pinned_tools(args.deps_root.resolve(),prepared/'both/native',run,env)
        report['tools']=tools
        libraries,report['producers']=bind_producers(args,prepared,data,tools,out)
        rustc=[args.deps_root.resolve()/'cargo/bin/rustup','run',pin['rust_toolchain'],'rustc']
        flags=['-O','--edition=2024','-L',f'dependency={verifier.parent}']
        result=run(rustc+['-vV'],'rustc-version')
        version=result.stdout.decode()
        if 'release: 1.99.1' not in version:
            raise RuntimeError('wrong compiler')
        sysroot=Path(run(rustc+['--print','sysroot'],'rustc-sysroot').stdout.decode().strip())
        actual_files=[Path(rustc[0]),sysroot/'bin/rustc',*list((sysroot/'lib').glob('*LLVM*.so*')),
                      *list((sysroot/'lib').glob('librustc_driver*.so'))]
        actual_files += [Path(shutil.which(name)).resolve() for name in ('ar','objdump','objcopy','c++','ldd','lscpu','uname')]
        report['ordinary_tools']=dict(rustc=version,sha256={str(path):file_sha(path) for path in actual_files})
        shapes=json.loads((prepared/'baseline/native/performance-target.json').read_text())['key_shapes']['shapes']
        report['oracle']=dict(legacy=legacy_oracle(out/'oracle-legacy',shapes),low_square=generate_low(out/'oracle-square'))
        legacy=ROOT/'experiments/arithmetic-precondition-checks-20261108'
        report['runtime']={}
        run(['c++','-std=c++17',prepared/'baseline/native/controls/gmp_abi.cpp','-lgmp','-o',out/'gmp-abi'],'gmp-abi-build')
        report['gmp_abi']=run([out/'gmp-abi'],'gmp-abi').stdout.decode()
        for label,library in libraries.items():
            for kind,source,fixture in (('legacy',legacy/'runtime.rs',out/'oracle-legacy/cases.bin'),
                                        ('square',FEATURE/'low_runtime.rs',out/'oracle-square/low.bin')):
                binary=out/(label+'-'+kind)
                run(rustc+[source,*flags,'-L',f'dependency={library.parent}','--extern',f'verigmp={library}','-o',binary],label+'-'+kind+'-build')
                result=run([binary,fixture],label+'-'+kind+'-oracle')
                report['runtime'][label+'-'+kind]=dict(status='pass',stdout=result.stdout.decode(),binary_sha256=file_sha(binary))
        report['strict_classifier_fixtures']=self_check()
        report['mutants']=[]
        mutants=[('wrong-worker-forwarding','fast_multiply','native/verified/fast_multiply.rs',
                   'full_inner(dst,a,b,scratch,threshold);','full_inner(dst,a,a,scratch,threshold);'),
                 ('single-cross-in-combination','square_low','native/verified/square_low.rs',
                   'let _carry=add_double_assign(&mut dst[k..],temp);',
                   'let _carry=crate::limbs::add_assign(&mut dst[k..],temp);')]
        for name,module,source,before,after in mutants:
            folder=out/'mutants'/name;shutil.copytree(prepared/'both/native',folder/'native')
            path=folder/source;text=path.read_text()
            if text.count(before)!=1:
                raise RuntimeError('ambiguous mutant anchor')
            path.write_text(text.replace(before,after,1))
            result=run(['taskset','-c','2-15',verifier,'native/lib.rs','--crate-name','verigmp','--crate-type','lib',
                        '--verify-module',module,'--no-cheating','--multiple-errors','0','--num-threads','2'],
                       'mutant-'+name,folder,require=False)
            accepted=strict_semantic_rejection((result.stdout+result.stderr).decode(),result.returncode,module)
            report['mutants'].append(dict(name=name,source_sha256=file_sha(path),strict_logical_rejection=accepted))
            if not accepted:
                raise RuntimeError('incomplete/nonlogical mutant rejection: '+name)
        objects=out/'objects';objects.mkdir()
        report['object_sha256']={}
        for label,library in libraries.items():
            members=run(['ar','t',library],label+'-members').stdout.decode().splitlines()
            members=[name for name in members if name.endswith('.o')]
            if len(members)!=1:
                raise RuntimeError('unexpected object count')
            obj=objects/(label+'.o');obj.write_bytes(run(['ar','p',library,members[0]],label+'-object').stdout)
            report['object_sha256'][label]=file_sha(obj)
        report['codegen']={}
        for label in LABELS[1:]:
            pair=out/('pair-'+label);pair.mkdir()
            shutil.copyfile(objects/'baseline.o',pair/'baseline.o')
            shutil.copyfile(objects/(label+'.o'),pair/'candidate.o')
            run([sys.executable,FEATURE/'codegen.py','--objects',pair,'--output',out/('codegen-'+label)],'codegen-'+label)
            path=out/('codegen-'+label)/'comparison.json';cg=json.loads(path.read_text())
            expected={'double':{'verigmp::square_low::low'},
                      'checks':{'verigmp::fast_multiply::full','verigmp::toom_multiply::full'},
                      'both':{'verigmp::square_low::low','verigmp::fast_multiply::full','verigmp::toom_multiply::full'}}[label]
            if {row['function'] for row in cg['changed']}!=expected or cg['removed']:
                raise RuntimeError('unexpected changed complete function set: '+label)
            added=({'verigmp::square_spec::'+name for name in ('doubled_capacity','doubled_digit_bounds','doubled_sum')}
                   if label in ('double','both') else set())
            if label in ('checks','both'):added.add('verigmp::fast_multiply::full_inner')
            if set(cg['added'])!=added:
                raise RuntimeError('unexpected added function set: '+label)
            funcs=cg['functions']['candidate'];hot=expected|({'verigmp::fast_multiply::full_inner'} if label in ('checks','both') else set())
            assembly=(out/('codegen-'+label)/'candidate-complete.asm').read_text()
            for name in hot:
                body=assembly[assembly.index('<'+name+'>:'):].split('\n\n',1)[0]
                if re.search(r'__rust_(?:alloc|realloc)|malloc|calloc|panic_bounds_check|Seq|radix::value',body):
                    raise RuntimeError('unexpected reached allocation/element-bounds/spec object')
            placeholders=added-{'verigmp::fast_multiply::full_inner'}
            template=cg['functions']['baseline']['verigmp::square_spec::square_range']
            for name in placeholders:
                if funcs[name]['sha256']!=template['sha256'] or funcs[name]['size']!=template['size']:
                    raise RuntimeError('unexpected proof placeholder body')
                if any(name in target for row in funcs.values() for _,_,target in row['normalized_relocations']):
                    raise RuntimeError('proof placeholder reached')
            report['codegen'][label]=dict(comparison_sha256=file_sha(path),changed=cg['changed'],added=cg['added'],removed=cg['removed'])
        counts=operation_counts(prepared,data,out/'operation-counts.json')
        report['operation_counts']=dict(sha256=file_sha(out/'operation-counts.json'),cells=len(counts['rows']),basis=counts['basis'])
        run([sys.executable,FEATURE/'test_measure.py','--output',out/'harness-fixtures'],'harness-fixtures')
        report['harness_fixtures']=json.loads((out/'harness-fixtures/verification.json').read_text())
        build_folder=out/'bench-build';build_folder.mkdir();binaries={}
        for label,library in libraries.items():
            binary=build_folder/(label+'-bench')
            argv=rustc+[legacy/'bench.rs',*flags,'-L',f'dependency={library.parent}',
                        '--extern',f'verigmp={library}','-o',binary]
            run(argv,label+'-bench-build')
            linked=run(['ldd',binary],label+'-bench-linked').stdout.decode()
            gmp=next(line.split('=>',1)[1].split('(',1)[0].strip() for line in linked.splitlines() if 'libgmp.so' in line)
            binaries[label]=dict(path=str(binary),sha256=file_sha(binary),library_sha256=file_sha(library),
                                  gmp_path=gmp,gmp_sha256=file_sha(gmp),argv=list(map(str,argv)),linked=linked)
        host={name:run(command,'host-'+name).stdout.decode() for name,command in
              (('lscpu',['lscpu']),('uname',['uname','-a']))}
        host.update(python=sys.version,process_affinity=sorted(os.sched_getaffinity(0)))
        write_json(out/'host.json',host)
        build=dict(status='static_pass',source_head=data['source_head'],prepared_sha256=file_sha(prepared/'prepared.json'),
                   native_manifests={k:v['native_manifest_sha256'] for k,v in data['cells'].items()},
                   producers=report['producers'],binaries=binaries,key_shapes=shapes,seed=20261108,cell_count=86,
                   inputs_sha256=data['inputs_sha256'],host_sha256=file_sha(out/'host.json'),
                   operation_counts_sha256=file_sha(out/'operation-counts.json'),
                   protocol_sha256=file_sha(FEATURE/'PROTOCOL.md'),proof_tools=tools,
                   measurement_authorized=False,benchmark_executed=False,performance_accepted=False)
        write_json(build_folder/'bench-build.json',build)
        report['bench_build_sha256']=file_sha(build_folder/'bench-build.json')
        checked_prepared(prepared)
        report['status']='pass';write_json(out/'verification.json',report)
        print(json.dumps(dict(status='pass',oracle_cases_per_cell=report['oracle']['legacy']['cases']+report['oracle']['low_square']['cases'],
            proof_counts={k:v['proof_items'] for k,v in report['producers'].items()},
            bench_build_sha256=report['bench_build_sha256'],benchmark_executed=False),indent=2))
    except BaseException as error:
        report.update(status='fail',failure=repr(error));write_json(out/'verification.json',report);raise


if __name__=='__main__':
    main()

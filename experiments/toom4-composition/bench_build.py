"""Compile the actual default-entry comparison against verified library/vir pairs."""
from pathlib import Path
import argparse
import json
import re
from common import check_hashes, check_prepared, checked, now, sha, verified, write

TEMPLATE = r'''
@EXTERNS@
use std::hint::black_box;
use std::time::Instant;
#[link(name="gmp")] extern "C" {
    fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize);
    fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);
}
fn run(op:u32,mode:usize,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32){
    match (op,mode) {
@CALLS@
        (_,@GMP@)=>{
            unsafe{if op==0{__gmpn_mul_n(scratch.as_mut_ptr(),a.as_ptr(),b.as_ptr(),a.len() as isize);}
                else{__gmpn_sqr(scratch.as_mut_ptr(),a.as_ptr(),a.len() as isize);}}
            out.copy_from_slice(&scratch[..a.len()]);
            if top<64{*out.last_mut().unwrap()&=(1u64<<top)-1;}
        },
        _=>panic!("operation/mode"),
    }
}
fn batch(op:u32,mode:usize,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,count:u64)->u128{
    let start=Instant::now();
    for _ in 0..count {
        run(black_box(op),black_box(mode),black_box(&mut *out),black_box(a),black_box(b),black_box(&mut *scratch),black_box(top));
        black_box(&*out);
    }
    start.elapsed().as_nanos()
}
fn main(){
    assert_eq!(std::env::args().len(),1);
    let shapes:Vec<(usize,u32)>=vec![@SHAPES@];
    println!("operation,limbs,top,mode,repetition,iterations,ns");
    eprintln!("operation,limbs,top,mode,iterations,ns");
    for (n,top) in shapes {
        let mut state=16438731u64^(n as u64);let mut random=||{state^=state<<13;state^=state>>7;state^=state<<17;state};
        let a:Vec<_>=(0..n).map(|_|random()).collect();let b:Vec<_>=(0..n).map(|_|random()).collect();
        let mut out=vec![u64::MAX;n];
        for op in [0,1] {
            let mut scratch=vec![0;if op==0{12*n}else{10*n}];
            let mut expected=vec![0;n];run(op,@GMP@,&mut expected,&a,&b,&mut scratch,top);
            let mut counts=[1u64;@MODES@];
            for mode in 0..@MODES@ {
                run(op,mode,&mut out,&a,&b,&mut scratch,top);assert_eq!(out,expected);
                loop {
                    let elapsed=batch(op,mode,&mut out,&a,&b,&mut scratch,top,counts[mode]);
                    assert_eq!(out,expected);
                    eprintln!("{op},{n},{top},{mode},{},{elapsed}",counts[mode]);
                    if elapsed>=20_000_000{break;}
                    counts[mode]=counts[mode].checked_mul(2).unwrap();
                }
            }
            for rep in 0..7 {for j in 0..@MODES@ {
                let mode=(j+rep)%@MODES@;
                let elapsed=batch(op,mode,&mut out,&a,&b,&mut scratch,top,counts[mode]);
                assert_eq!(out,expected);
                println!("{op},{n},{top},{mode},{rep},{},{elapsed}",counts[mode]);
                assert!(elapsed>=10_000_000,"Recorded batch too short; retain failed run, no retry");
            }}
        }
    }
}
'''


def make(stage, phase):
    prepared = check_prepared(stage)
    policy = json.loads((stage / 'policy.json').read_text())
    build = json.loads((stage / 'build-evidence/build.json').read_text())
    if build['status'] != 'pass':
        raise RuntimeError('Library gate did not pass')
    check_hashes(build['infrastructure_sha256'], stage)
    check_hashes(build['toolchain']['sha256'])
    if phase == 'exploration':
        modes = policy['modes']
        shapes = policy['exploration']['shapes']
    else:
        selected = json.loads((stage / 'selection.json').read_text())
        if selected['status'] != 'selected_pending_confirmation':
            raise RuntimeError('No selected candidate')
        gate = json.loads((stage / 'acceptance/verification.json').read_text())
        if gate['status'] != 'pass' or gate['selected'] != selected['selected']:
            raise RuntimeError('Selected full acceptance gate has not passed')
        modes = ['baseline', selected['selected'], 'gmp']
        target = json.loads((stage / 'baseline/native/performance-target.json').read_text())
        shapes = [list(x) for x in sorted(set(map(tuple, target['key_shapes']['shapes'] + policy['exploration']['shapes'])))]
    directory = stage / (phase + '-build')
    directory.mkdir()
    names = modes[:-1]
    calls = []
    for index, name in enumerate(names):
        calls += [f'        (0,{index})=>{name}::arithmetic::mul_mod(out,a,b,scratch,top),',
            f'        (1,{index})=>{name}::arithmetic::square_mod(out,a,scratch,top),']
    source = TEMPLATE.replace('@EXTERNS@', '\n'.join('extern crate ' + name + ';' for name in names))
    source = source.replace('@CALLS@', '\n'.join(calls)).replace('@GMP@', str(len(names)))
    source = source.replace('@MODES@', str(len(modes)))
    source = source.replace('@SHAPES@', ','.join(f'({n},{top})' for n, top in shapes))
    driver = directory / 'compare.rs'
    driver.write_text(source)
    verifier = Path(__import__('os').environ['VERUS_BIN']).resolve()
    command = [verifier, driver, '--compile', '-O', '-o', directory / 'compare']
    identities = {}
    for name in names:
        lib = stage / 'build-evidence' / name / ('lib' + name + '.rlib')
        vir = stage / 'build-evidence' / name / (name + '.vir')
        if sha(lib) != build['libraries'][name]['rlib'] or sha(vir) != build['libraries'][name]['vir']:
            raise RuntimeError('Library metadata pair changed')
        identities[str(lib)] = sha(lib)
        identities[str(vir)] = sha(vir)
        command += ['--import', name + '=' + str(vir), '--extern', name + '=' + str(lib)]
    count = verified(command, directory / 'compile.log', stage)
    abi = directory / 'gmp-abi'
    checked(['c++', '-std=c++17', stage / 'baseline/native/controls/gmp_abi.cpp', '-lgmp', '-o', abi],
        directory / 'gmp-abi-build.log', stage)
    gmp_abi = checked([abi], directory / 'gmp-abi.log', stage).stdout
    linked = checked(['ldd', directory / 'compare'], directory / 'linked.log', stage).stdout
    runtime = {str(Path(path).resolve()): sha(Path(path).resolve()) for path in re.findall(r'=> (\S+) \(', linked)}
    if len([path for path in runtime if Path(path).name.startswith('libgmp')]) != 1:
        raise RuntimeError('Ambiguous GMP runtime')
    disassembly = checked(['objdump', '-d', '-C', '--no-show-raw-insn', directory / 'compare'],
        directory / 'disassembly.txt', stage).stdout
    for name in names[1:]:
        if name + '::arithmetic::' not in disassembly or name + '::toom4_' not in disassembly:
            raise RuntimeError('Actual production entry/Toom-4 missing from matched binary: ' + name)
    report = {'status': 'pass', 'phase': phase, 'compiled_utc': now(), 'modes': modes, 'shapes': shapes,
        'verified_items_including_imports': count, 'policy_sha256': sha(stage / 'policy.json'),
        'build_gate_sha256': sha(stage / 'build-evidence/build.json'), 'gmp_abi': gmp_abi,
        'source_sha256': sha(driver), 'binary_sha256': sha(directory / 'compare'),
        'disassembly_sha256': sha(directory / 'disassembly.txt'),
        'paired_library_sha256': identities, 'runtime_sha256': runtime,
        'toolchain': build['toolchain'], 'source_manifest_sha256': sha(stage / 'preparation.json')}
    check_prepared(stage)
    check_hashes(identities | runtime | build['toolchain']['sha256'])
    write(directory / 'binding.json', report)
    print(json.dumps({'status': 'pass', 'phase': phase, 'modes': modes, 'shape_groups': 2*len(shapes)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['exploration', 'confirmation'])
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    make(args.stage.resolve(), args.phase)

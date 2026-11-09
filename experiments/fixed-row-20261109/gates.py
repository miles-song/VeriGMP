#!/usr/bin/env python3
"""Bounded untimed native fixed-row gates. Does not launch benchmark samples."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import time

import oracle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEPS = Path('/mnt/e/3sat/VeriCount/deps')
RUSTC = DEPS / 'rustup/toolchains/1.99.1-x86_64-unknown-linux-gnu/bin/rustc'
VSTD = DEPS / 'verus/verus-x86-linux'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


class GateRun:
    def __init__(self, output):
        self.output = output
        self.path = output / 'children.json'
        self.rows = json.loads(self.path.read_text()) if self.path.exists() else []
        self.prior_wall = sum(row['wall_seconds'] for path in output.parent.glob('run-*/children.json')
                              if path != self.path for row in json.loads(path.read_text()))
        self.env = dict(os.environ, RUSTUP_HOME=str(DEPS/'rustup'), CARGO_HOME=str(DEPS/'cargo'),
                        RUSTUP_TOOLCHAIN='1.99.1-x86_64-unknown-linux-gnu')
        self.env['PATH'] = str(VSTD) + ':' + str(DEPS/'cargo/bin') + ':' + str(RUSTC.parent) + ':' + self.env['PATH']

    def run(self, name, argv, data=None, timeout=60, directory=None):
        used = self.prior_wall + sum(r['wall_seconds'] for r in self.rows)
        assert used < 480, 'aggregate child wall budget exhausted'
        timeout = min(timeout, 60, 480-used)
        dest = directory or self.output
        dest.mkdir(parents=True, exist_ok=True)
        assert not (dest/(name+'.stdout')).exists(), 'logs may not be overwritten'
        command = ['taskset', '-c', '8', *map(str, argv)]
        start = time.monotonic()
        try:
            result = subprocess.run(command, input=data, cwd=ROOT, env=self.env, capture_output=True, timeout=timeout)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as e:
            stdout, stderr, code = e.stdout or b'', e.stderr or b'', 'timeout'
        wall = time.monotonic()-start
        (dest/(name+'.stdout')).write_bytes(stdout)
        (dest/(name+'.stderr')).write_bytes(stderr)
        row = dict(name=name, argv=command, returncode=code, timeout_seconds=timeout, wall_seconds=wall,
                   stdout=str(dest/(name+'.stdout')), stderr=str(dest/(name+'.stderr')),
                   stdout_sha256=sha(dest/(name+'.stdout')), stderr_sha256=sha(dest/(name+'.stderr')),
                   environment={key:self.env[key] for key in ('PATH','RUSTUP_HOME','CARGO_HOME','RUSTUP_TOOLCHAIN')})
        self.rows.append(row)
        self.path.write_text(json.dumps(self.rows, indent=2)+'\n')
        print(json.dumps(dict(child=name, returncode=code, wall_seconds=wall,
                              aggregate_child_wall_seconds=used+wall, budget_seconds=480)), flush=True)
        return row


def source_binding(args):
    receipt = json.loads((args.new_pair/'receipt.json').read_text())
    assert receipt['returncode'] == 0 and receipt['scope'] == 'full-library'
    assert receipt['verification_summary'] == ['verification results:: 371 verified, 0 errors']
    assert receipt['sources_unchanged'] and receipt['tools_unchanged']
    assert receipt['source_commit'] == 'd12759a022d2e285d0bc6b5869ccfb5c1d85f665'
    assert receipt['native_tree'] == '5790ad2fbadc9877332124c6a66ae3b70b016d03'
    for name, digest in receipt['source_hashes'].items():
        assert sha(ROOT/name) == digest, ('native source mismatch', name)
    for name, digest in receipt['tool_hashes'].items():
        assert sha(name) == digest, ('native proof tool mismatch', name)
    for name, digest in receipt['artifacts'].items():
        assert sha(args.new_pair/name) == digest
    old = json.loads((args.old_pair/'summary.json').read_text())
    assert old['native_tree'] == '72dc8a5da2cbb7eddcdd26c219d50770e8b73b06'
    for key, name in [('rlib_sha256','libverigmp.rlib'), ('vir_sha256','verigmp.vir')]:
        assert sha(args.old_pair/name) == old['library_pair'][key]
    return dict(candidate_receipt_sha256=sha(args.new_pair/'receipt.json'), candidate_source_commit=receipt['source_commit'],
                candidate_native_tree=receipt['native_tree'], baseline_native_tree=old['native_tree'],
                baseline_summary_sha256=sha(args.old_pair/'summary.json'),
                pairs={label:{name:dict(path=str(pair/name),sha256=sha(pair/name)) for name in ('libverigmp.rlib','verigmp.vir')}
                       for label,pair in [('old',args.old_pair),('new',args.new_pair)]},
                tools={**receipt['tool_hashes'],str(RUSTC):sha(RUSTC)},
                harness={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file()})


def prepare(args, run):
    binding = source_binding(args)
    out = args.output
    source = out/'source'
    source.mkdir()
    for p in HERE.iterdir():
        if p.suffix in ('.rs','.py'): shutil.copy2(p, source/p.name)
    row = run.run('rustc-version', [RUSTC,'-vV'])
    assert row['returncode'] == 0
    row = run.run('rustup-resolution', ['rustup','which','rustc'])
    assert row['returncode'] == 0 and Path(row['stdout']).read_text().strip() == str(RUSTC)
    row = run.run('verus-version', [VSTD/'verus','--version'])
    assert row['returncode'] == 0 and '1.99.1-x86_64-unknown-linux-gnu' in Path(row['stdout']).read_text()
    for label, pair in [('old',args.old_pair),('new',args.new_pair)]:
        flags = ['--cfg','has_fixed_row'] if label == 'new' else []
        command = [RUSTC, '--edition=2021', '-O', *flags, source/'runner.rs', '--extern',f'verigmp={pair/"libverigmp.rlib"}',
                   '-L',f'dependency={VSTD}', '--emit=asm,link', '-o',out/('runner-'+label)]
        row = run.run('build-'+label, command)
        assert row['returncode'] == 0, 'ordinary public API runner compile failed'
    row = run.run('linkage',['ldd',out/'runner-new'])
    assert row['returncode'] == 0
    links = {}
    for line in (out/'linkage.stdout').read_text().splitlines():
        if 'linux-vdso' in line:
            continue
        files = re.findall(r'(/[^\s()]+)', line)
        assert len(files) == 1, line
        p = Path(files[0]).resolve(strict=True)
        links[str(p)] = sha(p)
    assert any('libgmp.so' in p for p in links)
    binding['linked_libraries'] = links
    binding['artifacts'] = {p.name:sha(p) for p in out.glob('runner-*') if p.is_file()}
    (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    inputs = out/'inputs'
    inputs.mkdir()
    rng = random.Random(0xF17ED5C20261109)
    cells = []
    groups = [('principal', (1024,4096), ('mul','square'), ('random','max')),
              ('leaf', (14,15,16,19,20,21,22,23,24), ('forced',), ('random','max')),
              ('boundary', (63,64,65,127,128,129,191,192,193,511,512,513,1023,1024,1025,4095,4096,4097), ('mul','square'), ('random',))]
    for group, shapes, operations, patterns in groups:
        for n in shapes:
            for pattern in patterns:
                if pattern == 'max': a = b = (1 << (64*n))-1
                else: a,b = rng.getrandbits(64*n),rng.getrandbits(64*n)
                data = f'63 24 {oracle.words(a,n)} {oracle.words(b,n)}\n'
                path = inputs/f'{group}-{n}-{pattern}.txt'
                path.write_text(data)
                for op in operations:
                    answer = a*(a if op=='square' else b)
                    q = 2*n if op=='forced' else n
                    if q==n: answer %= 1 << (64*(n-1)+63)
                    expected = inputs/f'{group}-{n}-{pattern}-{op}.expected'
                    expected.write_text(oracle.words(answer,q)+'\n')
                    count = (512 if n==1024 else 64) if group=='principal' else 262144 if group=='leaf' else None
                    cells.append(dict(group=group,n=n,pattern=pattern,op=op,count=count,input=str(path),input_sha256=sha(path),
                                      expected=str(expected),expected_sha256=sha(expected)))
    plan = dict(status='prepared_no_samples', binding_sha256=sha(out/'binding.json'), cells=cells,
                runner_command=['taskset','-c','CPU','runner-{old,new}','sample','INPUT','OP','COUNT'],
                count_rule='Principal512@1024/64@4096 and leaf262144 inherited from prior actual-control/prototype screen. Boundary counts remain unset for root predeclaration or separately retained bounded calibration.',
                timing='Only native operation loop is timed. Identical source, compiler flags, inputs, 12*n caller scratch, warmup=min(count,32). GMP checks, frame checks, allocations and checksums excluded from timer.',
                gate=dict(principal_geomean_candidate_over_old_max=.97,worst_principal_cell_max=1.03,worst_regression_cell_max=1.03),
                root_owns='Freeze two independent interleaved schedules, repetitions and window before timing; no retrospective cell subset; no retry; no GMP parity claim.',benchmark_samples=0)
    (out/'timing-inputs.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(dict(status='source_ready_no_samples',binding_sha256=sha(out/'binding.json'),timing_inputs_sha256=sha(out/'timing-inputs.json'))))


def runtime(args, run):
    results = []
    for label in ('old','new'):
        output = args.output/('oracle-'+label)
        output.mkdir()
        callback = lambda name,cmd,data,timeout: run.run(label+'-'+name,cmd,data,timeout,directory=output)
        # Keep raw filenames stable for the oracle's independent comparison.
        def record(name,cmd,data,timeout):
            row = callback(name,cmd,data,timeout)
            shutil.copyfile(output/(label+'-'+name+'.stdout'),output/(name+'.stdout'))
            shutil.copyfile(output/(label+'-'+name+'.stderr'),output/(name+'.stderr'))
            return row
        results.append(oracle.check(args.output/('runner-'+label),output,record,label=='new'))
    invalids = ['direct_a','direct_b','direct_dst','direct_zero','forced_a','forced_zero','forced_dst','forced_scratch','forced_threshold',
                'mul_a','mul_dst','mul_scratch','mul_top0','mul_top65','square_dst','square_scratch','square_top0','square_top65']
    for name in invalids:
        r = run.run('invalid-'+name,[args.output/'runner-new','invalid',name])
        log = Path(r['stderr']).read_text()
        assert isinstance(r['returncode'],int) and r['returncode'] != 0
        assert 'assertion failed' in log and '/native/verified/' in log and 'unknown invalid case' not in log
    r = run.run('workspace',[args.output/'runner-new','workspace'])
    assert r['returncode'] == 0
    bits = 64
    expected = []
    for n in (0,1,((1<<bits)-1)//12,((1<<bits)-1)//12+1,(1<<bits)-1):
        option = lambda factor: f'Some({factor*n})' if 0<n<=((1<<bits)-1)//factor else 'None'
        expected.append(f'{n} {option(12)} {option(10)}')
    assert Path(r['stdout']).read_text().splitlines() == expected
    (args.output/'runtime.json').write_text(json.dumps(dict(status='pass',oracles=results,invalid_assertion_rejections=len(invalids),
        runtime_negative_scope='Observed implementation assertions on deliberately invalid calls; no formal claim beyond preconditions. Small default mul has a12*n contract and4*n runtime guard; test is below4*n.',
        workspace_boundary_checks=5,benchmark_samples=0),indent=2)+'\n')


def recheck(args, run):
    """Re-execute final pair against previously integer-validated immutable fixtures."""
    fixture = args.output.parent/'run-01'
    previous_binding = json.loads((fixture/'binding.json').read_text())
    current = source_binding(args)
    assert previous_binding['candidate_source_commit']==current['candidate_source_commit']
    assert previous_binding['candidate_native_tree']==current['candidate_native_tree']
    for name in ('runner.rs','ordinary.rs'):
        assert sha(fixture/'source'/name)==sha(args.output/'source'/name)
    results = []
    for label in ('old','new'):
        root = fixture/('oracle-'+label)
        report = json.loads((root/'oracle.json').read_text())
        assert report['status']=='pass'
        for name,digest in report['raw'].items(): assert sha(root/name)==digest
        r = run.run('recheck-'+label,[args.output/('runner-'+label)],(root/'input.txt').read_bytes())
        assert r['returncode']==0 and sha(r['stdout'])==report['raw']['oracle.stdout']
        results.append(dict(label=label,cases=report['cases'],source_fixture=str(root),fixture_receipt_sha256=sha(root/'oracle.json'),
                            input_sha256=sha(root/'input.txt'),stdout_sha256=sha(r['stdout']),binary_sha256=sha(args.output/('runner-'+label))))
    (args.output/'recheck.json').write_text(json.dumps(dict(status='pass',checks=results,
        fixtures='Exact fixtures independently compared with Python integers in run-01; final actual native pair re-executed, full output bytes equal.',
        script_sha256=sha(__file__),benchmark_samples=0),indent=2)+'\n')


def consumer(args, run):
    common = [VSTD/'verus','--num-threads','1','--rlimit','10','--no-cheating']
    source = args.output/'source'
    r = run.run('imported-consumer',[*common,source/'consumer.rs','--import',f'verigmp={args.new_pair/"verigmp.vir"}',
        '--extern',f'verigmp={args.new_pair/"libverigmp.rlib"}','--compile','-O','-o',args.output/'consumer'])
    log = Path(r['stdout']).read_text()+Path(r['stderr']).read_text()
    assert r['returncode']==0 and re.search(r'verification results:: \d+ verified, 0 errors',log)
    consumer_summary = re.findall(r'verification results::.*',log)
    r = run.run('consumer-execute',[args.output/'consumer'])
    assert r['returncode']==0 and Path(r['stdout']).read_text()=='actual imported consumer passed\n'
    negatives = {
        'alias-input':'pub fn bad(dst: &mut [u64], b: &[u64]) { verigmp::fixed_row::full::<15>(dst, &dst[..15], b); }',
        'alias-scratch':'pub fn bad(dst: &mut [u64], a: &[u64], b: &[u64]) { verigmp::fast_multiply::full(dst,a,b,dst,24); }',
    }
    for name, text in negatives.items():
        path = args.output/(name+'.rs')
        path.write_text(text+'\n')
        r = run.run(name,[RUSTC,'--edition=2021','--crate-type=lib',path,'--extern',f'verigmp={args.new_pair/"libverigmp.rlib"}',
                         '-L',f'dependency={VSTD}','--emit=metadata','-o',args.output/(name+'.rmeta')])
        log = Path(r['stderr']).read_text()
        expected = 'E0502' if name=='alias-input' else 'E0499'
        assert isinstance(r['returncode'],int) and r['returncode']!=0 and f'error[{expected}]' in log
    (args.output/'consumer.json').write_text(json.dumps(dict(status='pass', imported_consumer=consumer_summary,
        borrow_negatives=2, benchmark_samples=0),indent=2)+'\n')


def mutations(args, run):
    common = [VSTD/'verus','--num-threads','1','--rlimit','10','--no-cheating']
    mutations = [
        ('wide-omit-acc','fixed_row','verified/fixed_row.rs','+(acc as u128)+carry','+carry'),
        ('first-wrong-carry','fixed_row','verified/fixed_row.rs','let mut carry=0u128;','let mut carry=1u128;'),
        ('wrong-first-row-store','fixed_row','verified/fixed_row.rs','dst[N]=carry;','dst[N]=0;'),
        ('wrong-add-row-store','fixed_row','verified/fixed_row.rs','dst[i+N]=carry;','dst[i+N]=0;'),
    ]
    summaries = []
    for name,module,relative,old,new in mutations:
        dest = args.output/'mutations'/name
        shutil.copytree(args.new_pair/'snapshot/native',dest/'native')
        path = dest/'native'/relative
        text = path.read_text()
        assert old in text
        path.write_text(text.replace(old,new,1))
        hashes = {str(p.relative_to(dest)):sha(p) for p in sorted((dest/'native').rglob('*')) if p.is_file()}
        r = run.run('mutation-'+name,[*common,dest/'native/lib.rs','--crate-name','verigmp','--crate-type','lib','--verify-module',module],directory=dest)
        log = Path(r['stdout']).read_text()+Path(r['stderr']).read_text()
        errors = re.findall(r'verification results:: (\d+) verified, (\d+) errors',log)
        rejected = (isinstance(r['returncode'],int) and r['returncode']!=0 and errors and int(errors[-1][1])>0
                    and bool(re.search(r'(postcondition not satisfied|invariant not satisfied|precondition not satisfied|requires not satisfied|assertion failed)',log))
                    and not bool(re.search(r'(error\[E\d+\]|resource limit|timed out|internal error|panicked at)',log)))
        item = dict(name=name,module=module,status='typed_failed_vc' if rejected else 'not_detected',old=old,new=new,
                    source_hashes=hashes,argv=r['argv'],returncode=r['returncode'],verification_summary=errors)
        (dest/'mutation.json').write_text(json.dumps(item,indent=2)+'\n')
        summaries.append(item)
    (args.output/'mutation-gates.json').write_text(json.dumps(dict(mutations=summaries,
        mutation_gate=all(x['status']=='typed_failed_vc' for x in summaries),benchmark_samples=0),indent=2)+'\n')
    assert all(x['status']=='typed_failed_vc' for x in summaries), 'failed/timeout/tool errors are not detection'


def codegen(args, run):
    r = run.run('codegen-build',[RUSTC,'--edition=2021','-O','--crate-type=lib',args.output/'source/codegen.rs',
        '--extern',f'verigmp={args.new_pair/"libverigmp.rlib"}','-L',f'dependency={VSTD}',
        '--emit=asm,obj','-o',args.output/'codegen.o'])
    assert r['returncode']==0
    r = run.run('native-objdump',['objdump','-d','-C','-r',args.output/'runner-new'])
    assert r['returncode']==0
    # Raw assembly/disassembly are retained. Reachability and semantic inspection are recorded separately.
    (args.output/'codegen-artifacts.json').write_text(json.dumps(dict(status='emitted_for_inspection',
        artifacts={p.name:sha(p) for p in [args.output/'codegen.s',args.output/'codegen.o',Path(r['stdout'])]},
        benchmark_samples=0),indent=2)+'\n')


def inspect(args, run):
    number = sum(row['name'].startswith('inspect-codegen') for row in run.rows)+1
    r = run.run('inspect-codegen-'+str(number),[sys.executable,HERE/'inspect_codegen.py',args.output])
    assert r['returncode']==0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action',choices=('prepare','runtime','recheck','consumer','mutations','codegen','inspect'))
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--old-pair',type=Path,default=Path('/mnt/e/3sat/VeriGMP-cross-fusion-baseline-fresh-20261109'))
    p.add_argument('--new-pair',type=Path,default=Path('/mnt/e/3sat/VeriGMP-root-fixed-row-native-20261109/full-r05-toolbound'))
    args = p.parse_args()
    args.output.mkdir(parents=True,exist_ok=args.action!='prepare')
    run = GateRun(args.output)
    before = source_binding(args)
    globals()[args.action](args,run)
    after = source_binding(args)
    assert before==after, 'source, pair, dependency or tool changed during gate'
    identity = args.output/(args.action+'-identity.json')
    assert not identity.exists()
    identity.write_text(json.dumps(dict(action=args.action,source_commit=after['candidate_source_commit'],
        native_tree=after['candidate_native_tree'],source_pair_tool_stability=True,pairs=after['pairs'],
        harness=after['harness'],tools=after['tools'],benchmark_samples=0),indent=2)+'\n')
    print(json.dumps(dict(action=args.action,status='pass',benchmark_samples=0,
                          aggregate_child_wall_seconds=run.prior_wall+sum(x['wall_seconds'] for x in run.rows))))


if __name__=='__main__':
    main()

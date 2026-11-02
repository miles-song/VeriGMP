from pathlib import Path
import csv,difflib,hashlib,json,re,subprocess

STAGE=Path(__file__).resolve().parent;OUT=STAGE/'evidence';binary=OUT/'compare'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
verification=json.loads((OUT/'verification.json').read_text())
assert sha(binary)==verification['benchmark_binary_sha256']
assembly=subprocess.check_output(['objdump','-d','-C','--no-show-raw-insn',binary],text=True)
relocation_text=subprocess.check_output(['readelf','-Wr',binary],text=True)
(OUT/'compare-disassembly.txt').write_text(assembly)
(OUT/'compare-relocations.txt').write_text(relocation_text)
headers=list(re.finditer(r'(?m)^([0-9a-f]+) <(.+)>:\n',assembly))
functions={};symbols={}
for index,match in enumerate(headers):
    start=int(match[1],16);name=match[2];symbols[start]=name
    body=assembly[match.end():headers[index+1].start() if index+1<len(headers) else len(assembly)]
    instructions=[]
    for address,mnemonic,operand in re.findall(r'(?m)^\s*([0-9a-f]+):\s+(\S+)[ \t]*(.*)$',body):
        if mnemonic=='int3':continue
        instructions.append((int(address,16),mnemonic,operand.strip()))
    functions[name]={'address':start,'instructions':instructions}
relocations={}
for line in relocation_text.splitlines():
    fields=line.split()
    if len(fields)<4 or not re.fullmatch('[0-9a-f]+',fields[0]):continue
    if fields[2]=='R_X86_64_RELATIVE':relocations[int(fields[0],16)]=int(fields[3],16)
    elif fields[2] in ['R_X86_64_GLOB_DAT','R_X86_64_JUMP_SLOT'] and len(fields)>4:
        relocations[int(fields[0],16)]=fields[4]
def canonical(name):return re.sub(r'\b(baseline|candidate)::','crate::',name)
def normalized(name,ignore_nops=False):
    rows=functions[name]['instructions']
    if ignore_nops:rows=[row for row in rows if not re.search(r'\bnop[wql]?\b',row[1]+' '+row[2])]
    address_indices={address:i for i,(address,_,_) in enumerate(rows)}
    result=[];calls=[]
    for address,mnemonic,operand in rows:
        comment=re.search(r'#\s*([0-9a-f]+)',operand)
        raw=operand.split('#',1)[0].strip()
        if comment and '(%rip)' in raw:
            target=int(comment[1],16);resolved=relocations.get(target)
            if isinstance(resolved,int):resolved=symbols.get(resolved,'data')
            if resolved is None:resolved='data'
            destination=canonical(resolved)
            raw=re.sub(r'\*?-?0x[0-9a-f]+\(%rip\)', ('*' if raw.startswith('*') else '')+'@'+destination,raw)
            if mnemonic in ['call','jmp']:calls.append(destination)
        else:
            direct=re.match(r'([0-9a-f]+) <(.+)>$',raw)
            if direct:
                target=int(direct[1],16)
                if target in address_indices:raw='@instruction_'+str(address_indices[target])
                elif mnemonic.startswith('j') and functions[name]['address']<=target<=rows[-1][0]:
                    following=next((i for i,(a,_,_) in enumerate(rows) if a>=target),len(rows));raw='@instruction_'+str(following)
                else:
                    raw='@'+canonical(direct[2])
                    if mnemonic in ['call','jmp']:calls.append(canonical(direct[2]))
        result.append((mnemonic+' '+raw).strip())
    return result,sorted(set(calls))
def valid_small_trace(name):
    rows=functions[name]['instructions'];normalized_rows=normalized(name)[0]
    index=next(i for i,row in enumerate(rows) if row[1]=='jbe' and i>0 and rows[i-1][1]=='cmp'
        and re.fullmatch(r'%r\w+,%rcx',rows[i-1][2]))
    trace=[]
    for i,row in enumerate(rows[:index+1]):
        if row[1].startswith('j'):
            trace.append(row[1]+(' @small_branch_taken' if i==index else ' @valid_guard_not_taken'))
        else:trace.append(normalized_rows[i])
    current=int(rows[index][2].split()[0],16);indices={row[0]:i for i,row in enumerate(rows)}
    for _ in range(100):
        i=indices[current];row=rows[i]
        if row[1]=='jmp':
            trace.append('jmp @epilogue');current=int(row[2].split()[0],16);continue
        if row[1].startswith('j'):raise RuntimeError('Unexpected conditional branch in known small path')
        trace.append(normalized_rows[i])
        if row[1]=='ret':return trace
        current=rows[i+1][0]
    raise RuntimeError('Unfinished static small trace')
report={'status':'read_only_analysis','binary_sha256':sha(binary),
    'verification_sha256':sha(OUT/'verification.json'),
    'normalization':'Remove instruction addresses, crate prefixes, local branch labels and RIP-relative addresses; resolve GOT calls through ELF relocations. Panic/data reference addresses normalize to data, not an assertion of equal data bytes. int3 alignment fill excluded; comparisons with and without nop padding both reported.',
    'normalization_is_not_a_formal_equivalence_proof':True,'functions':{},'benchmark_records':{}}
for suffix in ['arithmetic::square_mod','arithmetic::mul_mod','square_low::low','toom_square::full','square::full',
    'square_base::full','square_base::low','toom_low::low','toom_multiply::full',
    'fast_multiply::full','fast_multiply::low','fast_multiply::base_full',
    'fast_words::combine_cross','fast_words::abs_difference']:
    names=['baseline::'+suffix,'candidate::'+('toom4_candidate::square_mod' if suffix=='arithmetic::square_mod' else suffix)];items=[normalized(name) for name in names]
    values=[item[0] for item in items];without=[normalized(name,True)[0] for name in names]
    diff='\n'.join(difflib.unified_diff(values[0],values[1],fromfile=names[0],tofile=names[1],lineterm=''))+'\n'
    diff_path=OUT/('small-path-'+suffix.replace('::','-')+'.diff');diff_path.write_text(diff)
    report['functions'][suffix]={'baseline_address':hex(functions[names[0]]['address']),
        'candidate_address':hex(functions[names[1]]['address']),
        'baseline_address_mod64':functions[names[0]]['address']%64,
        'candidate_address_mod64':functions[names[1]]['address']%64,
        'normalized_identical':values[0]==values[1],
        'normalized_identical_without_nop_padding':without[0]==without[1],
        'instruction_counts':[len(v) for v in values],
        'calls':dict(zip(['baseline','candidate'],[v[1] for v in items])),
        'diff_path':str(diff_path),'diff_sha256':sha(diff_path)}
for tag in ['default1','default2']:
    path=OUT/tag/'benchmark.csv';rows=list(csv.DictReader(path.open()))
    selected=[r for r in rows if int(r['operation'])==1 and int(r['limbs']) in [256,257]]
    expected_order=[(j+rep)%3 for rep in range(7) for j in range(3)]
    report['benchmark_records'][tag]={}
    for n in [256,257]:
        records=[r for r in selected if int(r['limbs'])==n]
        assert [int(r['mode']) for r in records]==expected_order
        mode_counts={str(mode):[int(r['iterations']) for r in records if int(r['mode'])==mode] for mode in range(3)}
        report['benchmark_records'][tag][str(n)]={'top':63,'mode_order':expected_order,
            'baseline_candidate_iteration_counts_equal':mode_counts['0']==mode_counts['1'],
            'iterations_by_mode':mode_counts,'same_iteration_counts_per_mode':len(set(tuple(v) for v in mode_counts.values()))==1,
            'records':records}
report['valid_small_traces']={}
for suffix in ['toom_square::full','toom_multiply::full']:
    traces={kind:valid_small_trace(kind+'::'+suffix) for kind in ['baseline','candidate']}
    report['valid_small_traces'][suffix]={'same_instructions_ignoring_relocation_and_branch_addresses':traces['baseline']==traces['candidate'],
        'scope':'Successful entry checks and length<=threshold branch; recursive callee treated as a call, separately compared by function',
        'traces':traces}
report['static_square_paths']={str(n):{'h':11*n//36,'k':n-11*n//36,'threshold':192,
    'primary_full_square_uses_toom_interpolation':n-11*n//36>192,
    'cross_low_length':11*n//36,'cross_full_length':11*n//36-(11*(11*n//36)//36)} for n in [256,257]}
report['confirmed_difference']={
    'square_entry':'The candidate Toom4 wrapper contains an additional length>=512 branch before selecting the original square_low function; the old arithmetic::square_mod is inlined into this wrapper. Both wrappers push the same three saved registers and reserve the same 32 outgoing-argument bytes on the successful small path.',
    'product_entry':'Below 512 limbs, the Toom4 wrapper pushes three registers, tests length, restores them and tail-jumps to candidate::arithmetic::mul_mod. The latter still contains the original length branch. This is an additional wrapper path relative to the baseline call.',
    'caller_workspace':'No change: product requires 12n scratch limbs; square requires 10n.',
    'causality':'The wrapper instruction differences are observed, so these paths are not instruction-identical. This static audit does not establish the cause or magnitude of any slowdown, and cannot assign the residual difference to noise.'}
report['wrapper_product_normalized_instructions']=normalized('candidate::toom4_candidate::mul_mod')[0]
summary=json.loads((OUT/'performance-summary.json').read_text())
by_run=[{(r['operation'],r['limbs'],r['top']):r for r in run['comparisons']} for run in summary['runs']]
report['regressions_in_both_runs']=[{'operation':key[0],'limbs':key[1],'top':key[2],
    'candidate_over_baseline':[run[key]['candidate_over_baseline'] for run in by_run]}
    for key in by_run[0] if all(run[key]['candidate_over_baseline']>1 for run in by_run)]
report['input_policy']={'driver_sha256':sha(STAGE/'compare.rs'),
    'same_input':'The same immutable a/b vectors created once per shape are supplied to all modes; square uses a; seed is 16438731 xor limbs.',
    'same_buffers':'All modes reuse the same preallocated out and scratch vectors; allocation and GMP correctness comparison occur outside timing.',
    'batch_policy':'Same batch function and 10ms retry rule for all modes; per-mode calibrated iteration counts are intentionally allowed to differ; medians use ns/iteration.'}
(OUT/'small-path-audit.json').write_text(json.dumps(report,indent=2)+'\n')
assert sha(binary)==verification['benchmark_binary_sha256']
print(json.dumps({'report_sha256':sha(OUT/'small-path-audit.json'),
    'function_equalities':{k:v['normalized_identical'] for k,v in report['functions'].items()},
    'batch_counts_equal':{tag:{n:item['same_iteration_counts_per_mode'] for n,item in rows.items()} for tag,rows in report['benchmark_records'].items()}},indent=2))

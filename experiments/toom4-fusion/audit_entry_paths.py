from pathlib import Path
import csv,difflib,hashlib,json,re,shutil,subprocess

STAGE=Path(__file__).resolve().parent;OUT=STAGE/'evidence';binary=OUT/'compare'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
verification=json.loads((OUT/'verification.json').read_text())
assert verification['status']=='pass' and verification['identity_checks_before_after']
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
def canonical(name):return re.sub(r'\b(baseline|previous|candidate)::','crate::',name)
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
report={'status':'read_only_analysis','binary_sha256':sha(binary),
    'verification_sha256':sha(OUT/'verification.json'),'analysis_script_sha256':sha(Path(__file__)),
    'normalization':'Remove addresses, crate prefixes and local labels; resolve GOT calls through ELF relocations. Data references normalize to data without asserting equal data bytes; int3 alignment fill is excluded.',
    'normalization_is_not_a_formal_equivalence_proof':True,'kernels':{},'entry_and_driver_functions':{}}
report['analysis_tools']={name:{'version':subprocess.check_output([name,'--version'],text=True).splitlines()[0],
    'sha256':sha(Path(shutil.which(name)).resolve())} for name in ['objdump','readelf']}
suffixes=['toom_words::add_shifted','square_low::low','toom_square::full','square::full','square_base::full','square_base::low',
    'toom_low::low','toom_multiply::full','fast_multiply::full','fast_multiply::low','fast_multiply::base_full',
    'fast_words::combine_cross','fast_words::abs_difference']
for suffix in suffixes:
    names={kind:kind+'::'+suffix for kind in ['baseline','previous','candidate']}
    present={kind:name for kind,name in names.items() if name in functions}
    values={kind:normalized(name) for kind,name in present.items()}
    report['kernels'][suffix]={'absent_symbols':[name for name in names.values() if name not in functions],
        'instruction_counts':{kind:len(v[0]) for kind,v in values.items()},
        'normalized_equal':None if len(values)!=3 else len({tuple(v[0]) for v in values.values()})==1,
        'normalized_equal_without_nop_padding':None if len(values)!=3 else len({tuple(normalized(name,True)[0]) for name in present.values()})==1,
        'addresses':{kind:hex(functions[name]['address']) for kind,name in present.items()},
        'calls':{kind:v[1] for kind,v in values.items()}}
    for old,new in [('baseline','previous'),('previous','candidate'),('baseline','candidate')]:
        if old not in values or new not in values:continue
        diff='\n'.join(difflib.unified_diff(values[old][0],values[new][0],fromfile=names[old],tofile=names[new],lineterm=''))+'\n'
        path=OUT/('entry-audit-'+suffix.replace('::','-')+'-'+old+'-'+new+'.diff');path.write_text(diff)
        report['kernels'][suffix].setdefault('diff_sha256',{})[path.name]=sha(path)
for name in functions:
    if name.startswith(('baseline::arithmetic::','previous::toom4_candidate::','candidate::toom4_candidate::')) or name in ['compare::run','compare::batch','compare::main']:
        rows,calls=normalized(name)
        report['entry_and_driver_functions'][name]={'address':hex(functions[name]['address']),
            'address_mod64':functions[name]['address']%64,'instruction_count':len(rows),'calls':calls,
            'initial_instructions':rows[:30],'normalized_instructions':rows}
report['review_boundary']='This report exposes actual matched-binary instructions and normalized comparisons. It does not infer runtime causality or assert that an inlined source helper has a standalone machine symbol.'
report['artifact_sha256']={name:sha(OUT/name) for name in ['compare-disassembly.txt','compare-relocations.txt']}
(OUT/'entry-path-audit.json').write_text(json.dumps(report,indent=2)+'\n')
assert sha(binary)==verification['benchmark_binary_sha256']
print(json.dumps({'report_sha256':sha(OUT/'entry-path-audit.json'),'kernel_equalities':{k:v['normalized_equal_without_nop_padding'] for k,v in report['kernels'].items()},'entry_symbols':list(report['entry_and_driver_functions'])},indent=2))

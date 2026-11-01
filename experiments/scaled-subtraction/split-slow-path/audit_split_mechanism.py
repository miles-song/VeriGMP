from pathlib import Path
import hashlib,json,re,subprocess

STAGE=Path(__file__).resolve().parent;OUT=STAGE/'evidence';binary=OUT/'compare'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((OUT/'verification.json').read_text());assert v['status']=='pass'
assert sha(binary)==v['benchmark_binary_sha256']
assembly=subprocess.check_output(['objdump','-d','-C','--no-show-raw-insn',binary],text=True)
relocation_text=subprocess.check_output(['readelf','-Wr',binary],text=True)
(OUT/'compare-disassembly.txt').write_text(assembly)
(OUT/'compare-relocations.txt').write_text(relocation_text)
heads=list(re.finditer(r'(?m)^([0-9a-f]+) <(.+)>:\n',assembly))
names={int(m[1],16):m[2] for m in heads};relocations={}
for line in relocation_text.splitlines():
    fields=line.split()
    if len(fields)>3 and fields[2]=='R_X86_64_RELATIVE':relocations[int(fields[0],16)]=int(fields[3],16)
report={'status':'generated_control_flow_checked','benchmark_binary_sha256':sha(binary),
    'verification_report_sha256':sha(OUT/'verification.json'),
    'disassembly_sha256':sha(OUT/'compare-disassembly.txt'),
    'relocation_sha256':sha(OUT/'compare-relocations.txt'),
    'static_inspection_not_a_new_formal_cost_theorem':True,'dispatch':{}}
for kind in ['baseline','candidate']:
    name=kind+'::square_low::low';a=assembly.index('<'+name+'>:');b=assembly.find('\n\n',a);lines=assembly[a:b].splitlines()
    targets=[]
    for index,line in enumerate(lines):
        m=re.search(r'call\s+.*#\s*([0-9a-f]+)',line)
        if not m:continue
        target=names.get(relocations.get(int(m[1],16),0),'external')
        if 'square::' not in target:continue
        targets.append({'target':target,'surrounding_instructions':lines[max(0,index-16):index+5]})
    report['dispatch'][kind]={'full_square_call_sites':targets,
        'entry_stack_reservation':next(line.strip() for line in lines[:15] if 'sub ' in line and '%rsp' in line)}
actual={item['target'] for item in report['dispatch']['candidate']['full_square_call_sites']}
assert actual=={'candidate::toom_square::full_toom','candidate::square::full'}
assert 'candidate::toom_square::full' not in names.values()
report['n256_n257']={'k_values':[178,179],'threshold':192,
    'inspected_path':'The inlined wrapper compares k with threshold in square_low::low and branches directly to square::full for k<=192. The full_toom stack frame is not entered on these valid inputs.',
    'slow_path_stack_reservation_bytes':136,
    'caller_owned_workspace':'Unchanged 10*n limbs; this is not a claim of a reduced public scratch API or globally reduced peak stack.',
    'performance_conclusion':'None until the separate declared complete benchmark runs; all earlier negative observations remain retained.'}
target=OUT/'split-mechanism-audit.json';target.write_text(json.dumps(report,indent=2)+'\n')
assert sha(binary)==v['benchmark_binary_sha256']
print(json.dumps({'path':str(target),'sha256':sha(target),'status':report['status']},indent=2))

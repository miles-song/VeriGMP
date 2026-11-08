#!/usr/bin/env python3
"""Reproduce the complete-section comparison into a fresh external directory."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--objects',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();out=a.output.resolve();out.mkdir()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
r=dict(scope='all complete native function sections from the exact matched release objects',
       inputs={},functions={},changed=[],added=[],removed=[])
for label in ('baseline','candidate'):
    obj=a.objects.resolve()/(label+'.o');r['inputs'][label]=dict(path=str(obj),sha256=sha(obj))
    table=subprocess.check_output(['objdump','-t','-C',obj]).decode()
    (out/(label+'-symbols.log')).write_text(table)
    (out/(label+'-complete.asm')).write_bytes(subprocess.check_output(['objdump','-d','-r','-C',obj]))
    reloc=subprocess.check_output(['objdump','-r','-C',obj]).decode()
    (out/(label+'-complete.reloc')).write_text(reloc)
    funcs={}
    for line in table.splitlines():
        f=line.split(None,5)
        if len(f)==6 and f[2]=='F' and f[3].startswith('.text'):
            funcs[f[5]]=dict(section=f[3],size=int(f[4],16))
    by_section={row['section']:name for name,row in funcs.items()}
    rows={};section=None
    for line in reloc.splitlines():
        header=re.fullmatch(r'RELOCATION RECORDS FOR \[(.+)\]:',line)
        if header:section=header[1];rows[section]=[]
        row=re.fullmatch(r'([0-9a-f]+)\s+(R_\S+)\s+(.+)',line)
        if row and section in rows:rows[section].append(list(row.groups()))
    folder=out/label;folder.mkdir();cmd=['objcopy']
    for index,(name,row) in enumerate(funcs.items()):
        row['file']=str(folder/(str(index)+'.bin'))
        cmd+=['--dump-section',row['section']+'='+row['file']]
    # Explicit output prevents objcopy from rewriting the ar-extracted input ELF.
    subprocess.run(cmd+[str(obj),str(out/(label+'-dump-output.o'))],check=True,capture_output=True)
    assert sha(obj)==r['inputs'][label]['sha256']
    for name,row in funcs.items():
        path=Path(row['file']);assert path.stat().st_size==row['size']
        row['sha256']=sha(path);row['relocations']=rows.get(row['section'],[]);normalized=[]
        for offset,kind,target in row['relocations']:
            target=re.sub(r'\.Lanon\.[0-9a-f]+\.\d+','.Lanon',target)
            match=re.fullmatch(r'(\.text[^+ ]+?)([+-]0x[0-9a-f]+)?',target)
            if match and match[1] in by_section:target=by_section[match[1]]+(match[2] or '')
            normalized.append([offset,kind,target])
        row['normalized_relocations']=normalized
    r['functions'][label]=funcs
old=r['functions']['baseline'];new=r['functions']['candidate']
for name in sorted(set(old)|set(new)):
    if name not in old:r['added'].append(name)
    elif name not in new:r['removed'].append(name)
    elif old[name]['sha256']!=new[name]['sha256'] or old[name]['normalized_relocations']!=new[name]['normalized_relocations']:
        r['changed'].append(dict(function=name,baseline_bytes=old[name]['size'],candidate_bytes=new[name]['size'],
            body_equal=old[name]['sha256']==new[name]['sha256'],relocations_equal=old[name]['normalized_relocations']==new[name]['normalized_relocations']))
r['complete_assembly_sha256']={label:sha(out/(label+'-complete.asm')) for label in ('baseline','candidate')}
(out/'comparison.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(added=r['added'],removed=r['removed'],changed=r['changed']),indent=2))

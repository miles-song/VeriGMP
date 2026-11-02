"""Inspect the actual linked comparison; normalized text is not a machine-code proof."""
from pathlib import Path
import argparse
import difflib
import json
import re
import shutil
import subprocess
from common import check_hashes, check_prepared, now, sha, write


def audit(stage, phase):
    check_prepared(stage)
    directory = stage / (phase + '-build')
    binding = json.loads((directory / 'binding.json').read_text())
    binary = directory / 'compare'
    if sha(binary) != binding['binary_sha256']:
        raise RuntimeError('Comparison binary changed')
    check_hashes(binding['paired_library_sha256'])
    assembly = subprocess.check_output(['objdump', '-d', '-C', '--no-show-raw-insn', binary], text=True)
    relocations_text = subprocess.check_output(['readelf', '-Wr', binary], text=True)
    (directory / 'disassembly.txt').write_text(assembly)
    (directory / 'relocations.txt').write_text(relocations_text)
    headers = list(re.finditer(r'(?m)^([0-9a-f]+) <(.+)>:\n', assembly))
    functions, symbols = {}, {}
    for index, match in enumerate(headers):
        start, name = int(match[1], 16), match[2]
        body = assembly[match.end():headers[index+1].start() if index+1<len(headers) else len(assembly)]
        instructions = [(int(address,16),mnemonic,operand.strip())
            for address,mnemonic,operand in re.findall(r'(?m)^\s*([0-9a-f]+):\s+(\S+)[ \t]*(.*)$',body)
            if mnemonic != 'int3' and not re.search(r'\bnop[wql]?\b',mnemonic+' '+operand)]
        functions[name] = {'address': start, 'instructions': instructions}
        symbols[start] = name
    relocations = {}
    for line in relocations_text.splitlines():
        fields = line.split()
        if len(fields)<4 or not re.fullmatch('[0-9a-f]+',fields[0]):
            continue
        if fields[2] == 'R_X86_64_RELATIVE':
            relocations[int(fields[0],16)] = int(fields[3],16)
        elif fields[2] in ['R_X86_64_GLOB_DAT','R_X86_64_JUMP_SLOT'] and len(fields)>4:
            relocations[int(fields[0],16)] = fields[4]
    names = binding['modes'][:-1]

    def canonical(name):
        return re.sub(r'\b('+'|'.join(map(re.escape,names))+r')::','crate::',name)

    def normalize(name):
        rows = functions[name]['instructions']
        indices = {address:i for i,(address,_,_) in enumerate(rows)}
        result, calls = [], []
        for address,mnemonic,operand in rows:
            comment = re.search(r'#\s*([0-9a-f]+)',operand)
            raw = operand.split('#',1)[0].strip()
            if comment and '(%rip)' in raw:
                target = int(comment[1],16)
                resolved = relocations.get(target)
                if isinstance(resolved,int):
                    resolved = symbols.get(resolved,'data')
                destination = canonical(resolved or 'data')
                raw = re.sub(r'\*?-?0x[0-9a-f]+\(%rip\)',('*' if raw.startswith('*') else '')+'@'+destination,raw)
                if mnemonic in ['call','jmp']:
                    calls.append(destination)
            else:
                direct = re.match(r'([0-9a-f]+) <(.+)>$',raw)
                if direct:
                    target = int(direct[1],16)
                    if target in indices:
                        raw = '@instruction_'+str(indices[target])
                    elif mnemonic.startswith('j') and rows and functions[name]['address']<=target<=rows[-1][0]:
                        raw = '@instruction_'+str(next((i for i,(a,_,_) in enumerate(rows) if a>=target),len(rows)))
                    else:
                        raw = '@'+canonical(direct[2])
                        if mnemonic in ['call','jmp']:
                            calls.append(canonical(direct[2]))
            result.append((mnemonic+' '+raw).strip())
        return result, sorted(set(calls))

    report = {'status': 'inspection_complete', 'created_utc': now(), 'phase': phase,
        'binary_sha256': sha(binary), 'binding_sha256': sha(directory / 'binding.json'),
        'script_sha256': sha(Path(__file__)), 'tools': {}, 'shared_kernels': {}, 'actual_default_entries': {},
        'scope': 'The exact linked comparison that is measured; ordinary instruction inventory and source identity, not formal machine-code equivalence or runtime causality',
        'normalization': 'Remove alignment, addresses and crate names; resolve GOT calls; data references normalize to data, without asserting equal referenced data bytes'}
    for tool in ['objdump','readelf']:
        path = Path(shutil.which(tool)).resolve()
        report['tools'][str(path)] = {'sha256': sha(path), 'version': subprocess.check_output([tool,'--version'],text=True).splitlines()[0]}
    suffixes = ['toom_words::add_shifted','square_low::low','toom_square::full','square::full',
        'square_base::full','square_base::low','toom_low::low','toom_multiply::full',
        'fast_multiply::full','fast_multiply::low','fast_multiply::base_full',
        'fast_words::combine_cross','fast_words::abs_difference']
    for suffix in suffixes:
        present = {kind:kind+'::'+suffix for kind in names if kind+'::'+suffix in functions}
        values = {kind:normalize(name)[0] for kind,name in present.items()}
        item = {'present': list(present), 'absent': [kind for kind in names if kind not in present],
            'instruction_counts': {kind:len(rows) for kind,rows in values.items()},
            'normalized_equal': len(values)==len(names) and len({tuple(rows) for rows in values.values()})==1,
            'diff_sha256': {}}
        for kind in names[1:]:
            if 'baseline' in values and kind in values:
                text = '\n'.join(difflib.unified_diff(values['baseline'],values[kind],fromfile='baseline::'+suffix,tofile=kind+'::'+suffix,lineterm=''))+'\n'
                path = directory / ('codegen-'+suffix.replace('::','-')+'-'+kind+'.diff')
                path.write_text(text)
                item['diff_sha256'][path.name] = sha(path)
        report['shared_kernels'][suffix] = item
    for name in functions:
        if any(name.startswith(kind+'::arithmetic::') for kind in names):
            rows,calls = normalize(name)
            report['actual_default_entries'][name] = {'instruction_count': len(rows), 'calls': calls,
                'normalized_instructions': rows, 'address_mod64': functions[name]['address']%64}
    for kind in names[1:]:
        old = stage / 'baseline/native/verified'
        new = stage / kind / 'native/verified'
        unchanged = [path.name for path in old.glob('*.rs') if path.name!='arithmetic.rs']
        if any((old/name).read_bytes()!=(new/name).read_bytes() for name in unchanged):
            raise RuntimeError('Unexpected shared production-source change: '+kind)
        report.setdefault('shared_verified_source_files',{})[kind] = unchanged
        if not any(name.startswith(kind+'::arithmetic::') for name in functions):
            raise RuntimeError('No actual default entry for '+kind)
    report['artifacts'] = {name:sha(directory/name) for name in ['disassembly.txt','relocations.txt']}
    if sha(binary)!=binding['binary_sha256']:
        raise RuntimeError('Comparison binary changed during inspection')
    check_hashes({path: item['sha256'] for path,item in report['tools'].items()})
    write(directory / 'codegen-audit.json', report)
    print(json.dumps({'status':report['status'],'shared_kernel_equalities':
        {key:item['normalized_equal'] for key,item in report['shared_kernels'].items()},
        'default_entries':list(report['actual_default_entries'])},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['exploration','confirmation'])
    parser.add_argument('--stage', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    audit(args.stage.resolve(),args.phase)

#!/usr/bin/env python3
"""Inspect retained assembly and the actual linked ELF; launches no processes."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import struct
import sys

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inspect(root):
    asm = (root/'codegen.s').read_text()
    wrappers = {}
    for n in (15,20,22,23):
        bodies = []
        for prefix in ('fixed','ordinary'):
            name = f'{prefix}_{n}'
            body = re.search(rf'(?ms)^{name}:\n(.*?)^\.Lfunc_end\d+:',asm)[1]
            positive = body.split('\tretq',1)[0]+'\tretq'
            normalized = re.sub(r'\.LBB\d+_', '.LBB_', positive)
            instructions = [s.strip() for s in normalized.splitlines() if s.startswith('\t') and not s.startswith('\t.')]
            assert not re.search(r'\b(?:i?div\w*|call\w*)\b', '\n'.join(instructions))
            calls = re.findall(r'(?m)^\s*callq\s+(.+)',body)
            assert len(calls)==1 and 'panicking5panic' in calls[0]
            muls = len(re.findall(r'(?m)^\s*mulq\s',body))
            assert muls==2*n
            bodies.append(instructions)
            wrappers[name] = dict(static_mulq_count=muls,nonpanic_calls=0,divide_instructions=0,
                instruction_count=len(instructions),positive_path_sha256=hashlib.sha256(('\n'.join(instructions)+'\n').encode()).hexdigest())
        assert bodies[0]==bodies[1], f'positive assembly differs at{n}'

    data = (root/'runner-new').read_bytes()
    assert data[:6]==b'\x7fELF\x02\x01'
    shoff = struct.unpack_from('<Q',data,40)[0]
    shsize,shnum,shstr = struct.unpack_from('<HHH',data,58)
    sections = [struct.unpack_from('<IIQQQQIIQQ',data,shoff+i*shsize) for i in range(shnum)]
    names = sections[shstr]
    strings = data[names[4]:names[4]+names[5]]
    name = lambda offset: strings[offset:strings.index(b'\0',offset)].decode()
    sections = {name(s[0]):s for s in sections}
    rela = sections['.rela.dyn']
    got = {}
    external = {}
    dyn = sections['.dynsym']; text = sections['.dynstr']
    dynamic_strings = data[text[4]:text[4]+text[5]]
    for i in range(rela[4],rela[4]+rela[5],rela[9]):
        offset,info,addend = struct.unpack_from('<QQq',data,i)
        if info & 0xffffffff == 8: got[offset]=addend  # R_X86_64_RELATIVE
        elif info & 0xffffffff in (6,7):
            symbol = dyn[4]+(info>>32)*dyn[9]
            string = struct.unpack_from('<I',data,symbol)[0]
            external[offset]=dynamic_strings[string:dynamic_strings.index(b'\0',string)].decode()
    def memory(address,size):
        for s in sections.values():
            if s[3]<=address and address+size<=s[3]+s[5] and s[1]!=8:
                return data[s[4]+address-s[3]:s[4]+address-s[3]+size]
        raise AssertionError(f'ELF address absent: {address:x}')

    raw = (root/'native-objdump.stdout').read_text()
    headers = list(re.finditer(r'(?m)^([0-9a-f]+) <(.+)>:$',raw))
    functions = {int(h[1],16):(h[2],raw[h.end():headers[i+1].start()] if i+1<len(headers) else raw[h.end():]) for i,h in enumerate(headers)}
    names = {name:address for address,(name,_) in functions.items()}
    native = {address for address,(name,_) in functions.items() if name.startswith('verigmp::')}
    def instructions(body):
        for line in body.splitlines():
            match = re.match(r'\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+\s*([a-z][a-z0-9]*)\s*(.*)',line)
            if match: yield int(match[1],16),match[2],match[3],line
    def edges(body):
        for address,op,arg,line in instructions(body):
            if op not in ('call','callq','jmp','jmpq'): continue
            direct = re.match(r'([0-9a-f]+)\s+<',arg)
            rip = re.search(r'#\s*([0-9a-f]+)',arg)
            target = int(direct[1],16) if direct else got.get(int(rip[1],16)) if rip else None
            if target in native: yield target
    def callees(body):
        for address,op,arg,line in instructions(body):
            if op not in ('call','callq','jmp','jmpq'): continue
            direct = re.match(r'([0-9a-f]+)\s+<',arg)
            rip = re.search(r'#\s*([0-9a-f]+)',arg)
            if direct:
                target = int(direct[1],16)
                if target in functions: yield functions[target][0]
            elif rip:
                pointer = int(rip[1],16)
                if pointer in got and got[pointer] in functions: yield functions[got[pointer]][0]
                elif pointer in external: yield external[pointer]
                else: raise AssertionError(f'unresolved native GOT transfer: {line}')
            elif op in ('call','callq'):
                raise AssertionError(f'unresolved native indirect call: {line}')
    start = [names[f'verigmp::arithmetic::{n}'] for n in ('mul_mod','square_mod')]
    start += [names['verigmp::fast_multiply::full'],names['verigmp::toom_multiply::full']]
    reachable = set(start)
    pending = list(start)
    while pending:
        for target in edges(functions[pending.pop()][1]):
            if target not in reachable: reachable.add(target);pending.append(target)
    native_report = {}
    for address in sorted(reachable):
        name,body = functions[address]
        ops = list(instructions(body))
        called = sorted(set(callees(body)))
        assert not re.search(r'(__rust_alloc|__rust_realloc|malloc|calloc)', '\n'.join(called)), name
        native_report[name] = dict(address=hex(address),instructions=len(ops),callees=called,
            division_instructions=sum(op.startswith(('div','idiv')) for _,op,_,_ in ops),
            native_edges=sorted(functions[t][0] for t in set(edges(body))))
    assert len(reachable)>10, 'native closure unexpectedly small'

    full = functions[names['verigmp::fast_multiply::full']][1]
    table_pattern = re.search(r'(?m)^.*lea\s+[^\n]*#\s*([0-9a-f]+) [^\n]*\n.*movslq[^\n]*\n.*add[^\n]*\n.*jmp\s+\*%rax',full)
    assert table_pattern, 'actual native leaf jump table absent'
    table = int(table_pattern[1],16)
    targets = {n:table+struct.unpack_from('<i',memory(table+4*(n-15),4))[0] for n in range(15,24)}
    selected = (15,20,22,23)
    fallback = {targets[n] for n in targets if n not in selected}
    assert len(fallback)==1 and len({targets[n] for n in selected})==4
    assert not fallback.intersection(targets[n] for n in selected)
    ops = list(instructions(full))
    epilogues = [int(arg.split()[0],16) for _,op,arg,_ in ops if op=='jmp' and re.match(r'^[0-9a-f]+\s+<',arg)
                 and int(arg.split()[0],16)>max(targets[x] for x in selected)]
    epilogue = Counter(epilogues).most_common(1)[0][0]
    leaf_report = {}
    for n in selected:
        begin = targets[n]
        # Selected regions are contiguous and terminate at the common epilogue.
        jumps = [a for a,op,arg,_ in ops if a>=begin and op=='jmp' and re.match(r'^[0-9a-f]+\s+<',arg)
                 and int(arg.split()[0],16)==epilogue]
        # The final selected block falls through to the shared epilogue.
        end = min(jumps) if jumps else epilogue-1
        region = [item for item in ops if begin<=item[0]<=end]
        muls = sum(op in ('mul','mulq') for _,op,_,_ in region)
        assert muls==2*n and not any(op in ('call','callq','div','divq','idiv','idivq') for _,op,_,_ in region)
        leaf_report[str(n)] = dict(entry=hex(begin),last_instruction=hex(end),static_multiply_count=muls,calls=0,division_instructions=0)
    report = dict(status='pass',ordinary_control='Positive-path instructions identical after renaming local block numbers; only the cold panic location differs.',
        wrappers=wrappers,actual_native_dispatch=dict(table_address=hex(table),targets={str(n):hex(t) for n,t in targets.items()},selected_regions=leaf_report),
        actual_native_reachable_functions=native_report,
        scope='Four selected successful leaf paths contain no calls, carry helper, division or allocation. The existing native parent/fallback closure is enumerated separately, follows direct and ELF-relative GOT native edges, and contains no allocation entry. Existing generic carry helpers/division remain visible. Cold panic routines and unrelated runner/std/GMP code are excluded.',
        artifacts={p.name:sha(p) for p in [root/'codegen.s',root/'runner-new',root/'native-objdump.stdout']},inspector_sha256=sha(__file__),benchmark_samples=0)
    (root/'codegen-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='pass',wrapper_pairs=4,reachable_native_functions=len(reachable),selected_dispatch_leaves=4)))


if __name__=='__main__':
    inspect(Path(sys.argv[1]))

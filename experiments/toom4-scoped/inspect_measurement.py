"""Inspect the linked benchmark and proof rlib without executing either."""
import re


ROOTS = ('measure::call', 'verigmp::arithmetic::mul_mod', 'verigmp::arithmetic::square_mod',
         'verigmp::toom4_candidate::mul_mod', 'verigmp::toom4_candidate::square_large',
         'verigmp::toom4_low::low', 'verigmp::toom4_low::modular', 'verigmp::toom4_square_low::low')


def symbols(text):
    found = {}
    for line in text.splitlines():
        match = re.match(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+\w\s+(.+)$', line)
        if match:
            address, size, name = match.groups()
            found[name] = (int(address, 16), int(size, 16))
    return found


def inspect(binary_nm, rlib_nm, disassembly, relocations):
    binary, rlib = symbols(binary_nm), symbols(rlib_nm)
    for name in ROOTS:
        if name not in binary:
            raise RuntimeError('missing linked codegen symbol: ' + name)
        if name.startswith('verigmp::') and (name not in rlib or rlib[name][1] != binary[name][1]):
            raise RuntimeError('linked and proof-rlib symbol sizes differ: ' + name)
    bodies = {}
    current = None
    for line in disassembly.splitlines():
        match = re.match(r'^([0-9a-f]+) <(.+)>:$', line)
        if match:
            current = match.group(2)
            bodies[current] = []
        elif current is not None:
            bodies[current].append(line)
    for name, immediate in (('measure::call', '400'), ('verigmp::arithmetic::mul_mod', '200'),
                            ('verigmp::toom4_candidate::mul_mod', '200'),
                            ('verigmp::toom4_candidate::mul_mod', '800')):
        if not re.search(r'\bcmp\s+\$0x' + immediate + r'\b', '\n'.join(bodies[name])):
            raise RuntimeError('missing threshold comparison in ' + name + ': ' + immediate)
    by_address = {address: name for name, (address, _) in binary.items()}
    reloc = {}
    for line in relocations.splitlines():
        match = re.match(r'^([0-9a-f]+)\s+[0-9a-f]+\s+(R_\S+)\s+(.*)$', line)
        if not match:
            continue
        location, kind, tail = match.groups()
        if kind == 'R_X86_64_RELATIVE':
            try:
                reloc[int(location, 16)] = by_address.get(int(tail.strip(), 16), '<non-symbol relative>')
            except ValueError:
                raise RuntimeError('invalid relative relocation')
        elif kind in ('R_X86_64_GLOB_DAT', 'R_X86_64_JUMP_SLOT'):
            match = re.search(r'\s(\S+)\s+\+\s+0$', tail)
            if match:
                reloc[int(location, 16)] = match.group(1)
    seen, pending, edges, unresolved, hazards = set(), list(ROOTS), {}, [], []
    while pending:
        name = pending.pop()
        if name in seen or name not in bodies:
            continue
        seen.add(name)
        edges[name] = []
        for line in bodies[name]:
            instruction = re.search(r'\t(callq?|jmpq?|idiv\w*|div\w*)\s+(.+)$', line)
            if not instruction:
                continue
            operation, operand = instruction.groups()
            if operation.startswith(('idiv', 'div')):
                hazards.append([name, line.strip()])
                continue
            comment = re.search(r'#\s+([0-9a-f]+)', operand)
            direct = re.match(r'([0-9a-f]+)\s+<(.+)>', operand)
            if comment:
                target = reloc.get(int(comment.group(1), 16))
            elif direct:
                address = int(direct.group(1), 16)
                start, size = binary.get(name, (0, 0))
                if start <= address < start + size:
                    continue
                target = by_address.get(address, direct.group(2))
            else:
                target = None
            if target is None:
                unresolved.append([name, line.strip()])
                continue
            edges[name].append(target)
            if re.search(r'(^|::)(__rust_(alloc|realloc)|malloc|calloc)(@|$)', target):
                hazards.append([name, target])
            if target in bodies and not any(part in target for part in ('panicking', 'slice_index_fail')):
                pending.append(target)
    return {'scope': 'linked benchmark roots and statically resolved direct/GOT call targets; '
                     'register-indirect jumps and unclassified targets are listed, not assumed safe; '
                     'hazards cover allocation and general division only, with panic targets in edges',
            'thresholds': {'baseline_product': 512, 'candidate_product': 2048,
                           'inlined_candidate_square': 1024},
            'root_symbol_sizes': {name: binary[name][1] for name in ROOTS},
            'reachable_symbols': sorted(seen), 'edges': edges, 'unresolved': unresolved, 'hazards': hazards}

"""Read-only comparison of normalized functions around the ghost-only patch."""
from pathlib import Path
import difflib
import hashlib
import json
import re

STAGE = Path(__file__).resolve().parent
OLD = STAGE / 'prior-original'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Image:
    def __init__(self, directory):
        self.directory = directory
        self.report = json.loads((directory/'verification.json').read_text())
        assert self.report['status'] == 'pass'
        assembly = (directory/'compare-disassembly.txt').read_text()
        headers = list(re.finditer(r'(?m)^([0-9a-f]+) <(.+)>:\n', assembly))
        self.functions = {}
        self.symbols = {}
        self.relocations = {}
        for i, header in enumerate(headers):
            start = int(header[1], 16)
            self.symbols[start] = header[2]
            body = assembly[header.end():headers[i+1].start() if i+1 < len(headers) else len(assembly)]
            rows = [(int(address, 16), op, operand.strip()) for address, op, operand
                    in re.findall(r'(?m)^\s*([0-9a-f]+):\s+(\S+)[ \t]*(.*)$', body)]
            self.functions[header[2]] = (start, [row for row in rows if row[1] != 'int3'
                and not re.search(r'\bnop[wql]?\b', row[1]+' '+row[2])])
        for line in (directory/'compare-relocations.txt').read_text().splitlines():
            fields = line.split()
            if len(fields) < 4 or not re.fullmatch('[0-9a-f]+', fields[0]):
                continue
            if fields[2] == 'R_X86_64_RELATIVE':
                self.relocations[int(fields[0], 16)] = int(fields[3], 16)
            elif fields[2] in ['R_X86_64_GLOB_DAT', 'R_X86_64_JUMP_SLOT'] and len(fields) > 4:
                self.relocations[int(fields[0], 16)] = fields[4]

    def normalize(self, name):
        if name not in self.functions:
            return None
        start, rows = self.functions[name]
        addresses = {row[0]: i for i, row in enumerate(rows)}
        result = []
        for _, op, operand in rows:
            comment = re.search(r'#\s*([0-9a-f]+)', operand)
            raw = operand.split('#', 1)[0].strip()
            if comment and '(%rip)' in raw:
                target = self.relocations.get(int(comment[1], 16))
                if isinstance(target, int):
                    target = self.symbols.get(target, 'data')
                target = re.sub(r'\b(baseline|previous|candidate)::', 'crate::', target or 'data')
                raw = re.sub(r'\*?-?0x[0-9a-f]+\(%rip\)', ('*' if raw.startswith('*') else '')+'@'+target, raw)
            else:
                direct = re.match(r'([0-9a-f]+) <(.+)>$', raw)
                if direct:
                    target = int(direct[1], 16)
                    if target in addresses:
                        raw = '@instruction_'+str(addresses[target])
                    elif op.startswith('j') and start <= target <= rows[-1][0]:
                        raw = '@instruction_'+str(next((i for i, (a, _, _) in enumerate(rows) if a >= target), len(rows)))
                    else:
                        raw = '@'+re.sub(r'\b(baseline|previous|candidate)::', 'crate::', direct[2])
            result.append((op+' '+raw).strip())
        return result


def audit_codegen():
    old=Image(OLD); new=Image(STAGE/'evidence')
    recorded=json.loads((STAGE/'evidence/ghost-patch-codegen-audit.json').read_text())
    if recorded['original_binary_sha256'] != old.report['benchmark_binary_sha256'] or recorded['new_binary_sha256'] != new.report['benchmark_binary_sha256']:
        raise ValueError('Recorded binary identity mismatch')
    count=0
    for entry in recorded['functions']:
        name=entry['function']
        a=old.normalize('candidate::'+name);b=new.normalize('previous::'+name);c=new.normalize('candidate::'+name)
        if entry['present'] != [x is not None for x in [a,b,c]]:
            raise ValueError('Recorded symbol availability mismatch')
        ab=None if a is None or b is None else a==b
        bc=None if b is None or c is None else b==c
        if ab != entry['old_archived_algorithm_vs_proof_stable_control'] or bc != entry['proof_stable_control_vs_entry_candidate']:
            raise ValueError('Normalized function comparison mismatch')
        if ab is True and bc is True:count+=1
    if count!=6:raise ValueError('Missing compared functions')
    return count

if __name__=='__main__':
    print(json.dumps({'scope':'Archived disassembly comparison, not a fresh compilation or formal machine proof','equal_functions':audit_codegen()}))

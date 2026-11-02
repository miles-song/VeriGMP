"""Read-only comparison of normalized functions around the ghost-only patch."""
from pathlib import Path
import difflib
import hashlib
import json
import re

STAGE = Path(__file__).resolve().parent
OLD = STAGE.parent / 'toom4-stage-e22a4dd'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Image:
    def __init__(self, directory):
        self.directory = directory
        self.report = json.loads((directory/'verification.json').read_text())
        assert self.report['status'] == 'pass'
        assert sha(directory/'compare') == self.report['benchmark_binary_sha256']
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


old = Image(OLD/'evidence')
new = Image(STAGE/'evidence')
records = []
for suffix in ['toom_words::add_shifted', 'toom_multiply::full', 'toom_square::full',
               'toom4_multiply::full', 'toom4_square::full',
               'toom4_interpolate::interpolate', 'toom4_interpolate::assemble']:
    a = old.normalize('candidate::'+suffix)
    b = new.normalize('previous::'+suffix)
    c = new.normalize('candidate::'+suffix)
    entry = {'function': suffix, 'present': [x is not None for x in (a, b, c)],
             'old_archived_algorithm_vs_proof_stable_control': None if a is None or b is None else a == b,
             'proof_stable_control_vs_entry_candidate': None if b is None or c is None else b == c,
             'instruction_counts': [None if x is None else len(x) for x in (a, b, c)]}
    if a is not None and b is not None:
        path = STAGE/'evidence'/('ghost-patch-'+suffix.replace('::', '-')+'.diff')
        path.write_text('\n'.join(difflib.unified_diff(a, b, fromfile='original-archive', tofile='proof-stable-control', lineterm=''))+'\n')
        entry['diff_sha256'] = sha(path)
    records.append(entry)
report = {'status': 'read_only_analysis', 'normalization_is_not_a_formal_equivalence_proof': True,
          'scope': 'Exact five-line insertion within proof; compare normalized machine functions containing interpolation/assembly. Missing standalone symbols are reported as missing, not equal.',
          'normalization': 'Instruction addresses, crate prefixes, local branch labels, relocated references and nop/int3 alignment padding normalized; generic data references are not a comparison of data bytes.',
          'original_verification_sha256': sha(OLD/'evidence/verification.json'),
          'new_verification_sha256': sha(STAGE/'evidence/verification.json'),
          'original_binary_sha256': old.report['benchmark_binary_sha256'],
          'new_binary_sha256': new.report['benchmark_binary_sha256'],
          'analysis_script_sha256': sha(Path(__file__)), 'functions': records}
(STAGE/'evidence/ghost-patch-codegen-audit.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(records, indent=2))

"""Static counts from the actual matched benchmark binary; never a speed claim."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

S = Path(__file__).resolve().parent
O = S / 'evidence'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
verification = json.loads((O / 'verification.json').read_text())
audit = json.loads((O / 'entry-path-audit.json').read_text())
assert verification['status'] == 'pass'
assert sha(O / 'compare') == audit['binary_sha256'] == verification['benchmark_binary_sha256']
assert sha(O / 'compare-disassembly.txt') == audit['artifact_sha256']['compare-disassembly.txt']
assembly = (O / 'compare-disassembly.txt').read_text()
headers = list(re.finditer(r'(?m)^([0-9a-f]+) <(.+)>:\n', assembly))
functions = {}
for i, header in enumerate(headers):
    body = assembly[header.end():headers[i+1].start() if i+1 < len(headers) else len(assembly)]
    rows = [(int(address, 16), opcode, operand.strip()) for address, opcode, operand in
        re.findall(r'(?m)^\s*([0-9a-f]+):\s+(\S+)[ \t]*(.*)$', body) if opcode != 'int3']
    functions[header[2]] = rows
result = {'status': 'read_only_static_inventory', 'binary_sha256': sha(O / 'compare'),
    'verification_sha256': sha(O / 'verification.json'), 'disassembly_sha256': sha(O / 'compare-disassembly.txt'),
    'script_sha256': sha(Path(__file__)), 'modes': {}}
for mode in ['previous', 'candidate']:
    rows = functions[mode + '::toom4_interpolate::interpolate']
    backwards = []
    for address, opcode, operand in rows:
        target = re.match(r'^([0-9a-f]+) <', operand)
        if opcode.startswith('j') and target and rows[0][0] <= int(target[1], 16) <= address:
            backwards.append({'address': hex(address), 'opcode': opcode, 'target': target[1]})
    source = (S / mode / 'native/verified/toom4_interpolate.rs').read_text().split('pub fn assemble', 1)[0]
    counts = {'sign_combination': 2, **{name: source.count('toom_words::' + name + '(') for name in ['divide_exact', 'sub_exact', 'copy_pad', 'scale_exact']},
              'sub_scaled_exact': source.count('crate::scaled_subtraction::sub_scaled_exact(')}
    result['modes'][mode] = {'instruction_count_excluding_int3': len(rows),
        'instruction_count_excluding_alignment': sum(not re.search(r'\bnop[wql]?\b', opcode + ' ' + operand) for _, opcode, operand in rows),
        'backward_branches': backwards, 'multiply_instruction_count': sum(opcode.startswith(('mul', 'imul')) for _, opcode, _ in rows),
        'source_selected_operations': counts, 'source_selected_total': sum(counts.values())}
entries = audit['entry_and_driver_functions']
result['entry_normalized_equal'] = {name: entries['previous::toom4_candidate::' + name]['normalized_instructions'] ==
    entries['candidate::toom4_candidate::' + name]['normalized_instructions'] for name in ['mul_mod', 'square_large']}
result['scope_limit'] = 'Static instructions, backward branches and source primitive visits are distinct counts. They do not prove timing equivalence, memory bottlenecks, execution frequencies or runtime improvement.'
assert result['modes']['previous']['source_selected_total'] == 40 and result['modes']['candidate']['source_selected_total'] == 32
(O / 'fusion-mechanism-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'report_sha256': sha(O / 'fusion-mechanism-audit.json'), 'entries': result['entry_normalized_equal'],
    'modes': {mode: {key: value for key, value in row.items() if key != 'backward_branches'} | {'backward_branch_count': len(row['backward_branches'])} for mode, row in result['modes'].items()}}, indent=2))

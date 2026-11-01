"""State the checked small-entry traces without inferring a timing result."""
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent / 'evidence'
audit = json.loads((OUT/'entry-path-audit.json').read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def small_product_trace(name):
    rows = audit['entry_and_driver_functions'][name]['normalized_instructions']
    i = 0
    result = []
    while i < len(rows):
        row = rows[i]
        result.append(row)
        if row == 'ret':
            return result
        if row.startswith('jmp @instruction_'):
            i = int(row.split('_')[-1])
            continue
        if row.startswith(('jae ', 'je ')):
            assert i > 0 and rows[i-1].startswith(('cmp $0x200,', 'cmp $0x40,', 'test ')), (name, i, row)
        elif row.startswith('j'):
            raise RuntimeError((name, i, row))
        i += 1
    raise RuntimeError('Small successful trace has no return')


baseline = small_product_trace('baseline::arithmetic::mul_mod')
candidate = small_product_trace('candidate::toom4_candidate::mul_mod')
assert baseline == candidate
record = {
    'status': 'read_only_analysis',
    'analysis_script_sha256': sha(Path(__file__)),
    'entry_audit_sha256': sha(OUT/'entry-path-audit.json'),
    'ghost_patch_audit_sha256': sha(OUT/'ghost-patch-codegen-audit.json'),
    'product_small_trace': {
        'domain': 'n<512 with all entry preconditions true; length/precision checks follow their successful branches',
        'normalized_instruction_trace_equal_to_e22': True,
        'instructions': baseline,
        'callee_scope': 'fast_multiply::low separately normalized equal across all three libraries'
    },
    'square_small_path': {
        'observation': 'Candidate square body is inlined into shared compare::run; it tests n<512, calls original square_low::low, restores the shared frame and tail-jumps to pow2::normalize_top. No square_small standalone function/call or additional saved-register wrapper frame is present.',
        'boundary': 'The size test remains and normalize_top is a separate tail target in this matched binary. This is not an instruction-identical baseline-square trace or a proof of zero dispatch time.',
        'shared_driver_initial_stack_bytes': 56,
        'shared_driver_saved_register_bytes': 48,
        'small_square_outgoing_argument_bytes': 32
    },
    'proof_context_patch': {
        'added_source_lines_inside_proof': 5,
        'runtime_statements_changed': False,
        'normalized_original_vs_repaired_functions_equal': 6,
        'missing_standalone_add_shifted': 'Inlined; containing Toom3/4 full and Toom4 assemble functions are compared'
    },
    'runtime_claim': 'None before two new complete registered measurements'
}
(OUT/'entry-path-review.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'entry_review_sha256': sha(OUT/'entry-path-review.json'),
                  'product_trace_instructions': len(baseline)}))

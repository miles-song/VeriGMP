"""Inspect optimized arithmetic paths; counts are not a timing/cost theorem."""
import re

def inspect_fusion(assembly):
    bodies = {m[1]: m[2] for m in re.finditer(r'(?m)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,', assembly, re.S)}
    roots = ['verified_sub_scaled', 'verified_sub_scaled4', 'verified_sub_scaled16', 'verified_sub_scaled64']
    paths = {}
    for root in roots:
        pending = [root]
        seen = set()
        external = set()
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            if name not in bodies:
                raise RuntimeError('Missing scaled-subtraction target ' + name)
            seen.add(name)
            body = bodies[name]
            if re.search(r'__rust_(alloc|realloc)|malloc|calloc|free@|__(u?div|u?mod)ti3|panic_bounds_check', body):
                raise RuntimeError('Allocator/division/element-bounds helper in ' + name)
            if re.search(r'(?m)^\s*i?div[bwlq]?\s', body):
                raise RuntimeError('General division in ' + name)
            for target in re.findall(r'(?m)^\s*(?:callq?|jmp)\s+([^\s]+)', body):
                if target.startswith('.LBB'):
                    continue
                if target in bodies:
                    pending.append(target)
                elif 'core' in target and ('panicking' in target or 'slice_index_fail' in target):
                    external.add(target)
                else:
                    raise RuntimeError('Uninspected scaled-subtraction call ' + target)
        paths[root] = {'reachable_functions': sorted(seen), 'length_precondition_panic_calls': sorted(external),
                       'root_instruction_lines': sum(bool(re.match(r'^\s+[a-z][a-z0-9]*(?:\s|$)', line)) for line in bodies[root].splitlines())}
    interpolation = [name for name in bodies if 'toom4_interpolate11interpolate' in name]
    if len(interpolation) != 1:
        raise RuntimeError('Missing actual Toom-4 interpolation body')
    body = bodies[interpolation[0]]
    return {'status': 'pass', 'scope': 'Generic full-u64 helper and constants 4/16/64 in freshly verified optimized output',
            'no_allocator_general_division_element_bounds_panic': True, 'paths': paths,
            'interpolation_symbol': interpolation[0],
            'interpolation_instruction_lines': sum(bool(re.match(r'^\s+[a-z][a-z0-9]*(?:\s|$)', line)) for line in body.splitlines()),
            'limitation': 'Textual reachable-code inspection; neither machine-code equivalence nor speed or machine-cost proof'}

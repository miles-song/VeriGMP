"""Inspect emitted fixed-divisor entry paths; this is not a machine-code proof."""
import re

def inspect_odd(assembly):
    bodies={m[1]:m[2] for m in re.finditer(r'(?m)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,',assembly,re.S)}
    roots=['verified_exact3','verified_exact9','verified_exact15']
    inspected={}
    for root in roots:
        pending=[root];seen=set();external=set()
        while pending:
            name=pending.pop()
            if name in seen:continue
            if name not in bodies:raise RuntimeError('Missing odd codegen root or target '+name)
            seen.add(name);body=bodies[name]
            if re.search(r'__rust_(alloc|realloc)|malloc|calloc|free@|__(u?div|u?mod)ti3|panic_bounds_check',body):
                raise RuntimeError('Allocation, division helper or element bounds panic in '+name)
            if re.search(r'(?m)^\s*i?div[bwlq]?\s',body):raise RuntimeError('General division in '+name)
            for target in re.findall(r'(?m)^\s*(?:callq?|jmp)\s+([^\s]+)',body):
                if target.startswith('.LBB'):continue
                if target in bodies:pending.append(target);continue
                if 'core' in target and ('panicking' in target or 'slice_index_fail' in target):external.add(target);continue
                raise RuntimeError('Uninspected odd path call '+target)
        inspected[root]={'reachable_functions':sorted(seen),'external_calls':sorted(external),
                         'root_body_lines':len(bodies[root].splitlines())}
    return {'status':'pass','scope':'Actual optimized existing divide_exact API specialized to divisors 3/9/15; arbitrary-divisor fallback excluded',
            'no_allocator_general_division_element_bounds_panic':True,'paths':inspected,
            'limitation':'Textual reachable-code inspection, not a verified machine-code equivalence or timing theorem'}

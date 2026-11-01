"""Reachable-code checks for signed carry evaluation; not a speed theorem."""
import re
def inspect_signed(assembly):
    bodies={m[1]:m[2] for m in re.finditer(r'(?m)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,',assembly,re.S)}
    aliases=dict(re.findall(r'(?m)^\s*\.set\s+(\w+),\s*(\w+)\s*$',assembly))
    roots=['verified_signed_limb','verified_negate_words','verified_signed_generic','verified_signed_plain','verified_signed_half']
    paths={}
    for root in roots:
        pending=[aliases.get(root,root)];seen=set();external=set()
        while pending:
            name=pending.pop()
            if name in seen:continue
            if name not in bodies:raise RuntimeError('Missing signed-evaluation symbol '+name)
            seen.add(name);body=bodies[name]
            if re.search(r'__rust_(alloc|realloc)|malloc|calloc|free@|__(u?div|u?mod)ti3|panic_bounds_check',body):
                raise RuntimeError('Allocator/division/element-bounds path in '+name)
            if re.search(r'(?m)^\s*i?div[bwlq]?\s',body):raise RuntimeError('General signed division in '+name)
            for target in re.findall(r'(?m)^\s*(?:callq?|jmp)\s+([^\s]+)',body):
                if target.startswith('.LBB'):continue
                if target in bodies:pending.append(target)
                elif 'core' in target and ('panicking' in target or 'slice_index_fail' in target):external.add(target)
                else:raise RuntimeError('Uninspected signed-evaluation call '+target)
        paths[root]={'reachable_functions':sorted(seen),'length_precondition_panic_calls':sorted(external),
            'root_instruction_lines':sum(bool(re.match(r'^\s+[a-z][a-z0-9]*(?:\s|$)',line)) for line in bodies[aliases.get(root,root)].splitlines())}
    return {'status':'pass','scope':'Actual generic signed-word carry, modular negation and both Toom-4 signed weight sets',
        'no_allocator_general_division_element_bounds_panic':True,'paths':paths,
        'limitation':'Textual optimized-code inspection; no machine-code proof, dynamic cost theorem or speed claim'}

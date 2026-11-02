"""Reachable text inspection of actual eight-block producer APIs."""
import re
def inspect(assembly):
    bodies={m[1]:m[2] for m in re.finditer(r'(?m)^([A-Za-z_][\w.$]*):\n(.*?)^\s*\.size\s+\1,',assembly,re.S)}
    result={}
    for root in ['verified_producer_generic','verified_producer_point_one','verified_producer_point_eight']:
        pending=[root];seen=set();external=set()
        while pending:
            name=pending.pop()
            if name in seen:continue
            if name not in bodies:raise RuntimeError('Missing codegen path: '+name)
            seen.add(name);body=bodies[name]
            if re.search(r'__rust_(alloc|realloc)|malloc|calloc|free@|__(u?div|u?mod)ti3|panic_bounds_check',body):
                raise RuntimeError('Allocation/division helper/element bounds panic: '+name)
            if re.search(r'(?m)^\s*i?div[bwlq]?\s',body):raise RuntimeError('General division instruction: '+name)
            for target in re.findall(r'(?m)^\s*(?:callq?|jmp)\s+([^\s]+)',body):
                if target.startswith('.LBB'):continue
                if target in bodies:pending.append(target);continue
                if target in ('*memcpy@GOTPCREL(%rip)','*memset@GOTPCREL(%rip)') or ('core' in target and ('panicking' in target or 'slice_index_fail' in target)):external.add(target);continue
                raise RuntimeError('Uninspected external call: '+target)
        result[root]={'reachable_functions':sorted(seen),'external_calls':sorted(external),'root_body_lines':len(bodies[root].splitlines())}
    return {'status':'pass','scope':'Actual eight-block evaluation/product/pair composition and child multiplication paths',
        'no_allocator_general_division_or_element_bounds_panic':True,'paths':result,
        'limitation':'Textual assembly inspection; no machine-code equivalence or performance claim'}

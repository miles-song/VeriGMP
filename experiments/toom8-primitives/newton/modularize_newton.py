"""Factor proof boundaries by Newton stage; preserve ordered arithmetic calls."""
from pathlib import Path
import json
S=Path(__file__).resolve().parent
certificate=json.loads((S/'newton-operations.json').read_text())
original=S.parent/'toom8-balanced-stage-e22a4dd/mathematics/toom8_newton_spec.rs'
model=original.read_text();assert model.endswith('}\n');model=model[:-2]
def expression(v):return '+'.join(f'{x}int*c[{i}]' for i,x in enumerate(v) if x) or '0int'
def arithmetic(op):
    opn=op['name'];i=op['slot'];j=op['rhs_slot'];factor=op['factor'];divisor=op['divisor']
    result=f'    proof {{ model::{opn}(c); }}\n    assert(value(a{i}@)==model::{opn}_before(c));\n    assert(value(a{j}@)==model::{opn}_rhs(c));\n'
    if op['kind']=='scaled_subtraction':result+=f'    scaled_subtraction::sub_scaled_exact(a{i},a{j},{factor}u64);\n'
    else:
        result+=f'    toom_words::sub_exact(a{i},a{j});\n    let ghost q=model::{opn}_after(c);\n'
        power=1;odd=divisor
        while odd%4==0:power*=4;odd//=4
        if power>1:
            result+=f'    proof {{ lemma_mod_multiples_basic({odd}int*q,{power}int); }}\n    toom_words::divide_exact(a{i},{power}u64);\n    assert(value(a{i}@)=={odd}int*q);\n'
        result+=f'    proof {{ lemma_mod_multiples_basic(q,{odd}int); }}\n    wide_odd_division::divide_toom8_odd(a{i},{odd}u64);\n'
    return result+f'    assert(value(a{i}@)==model::{opn}_after(c));\n'
parts=['//! Factored in-place Newton interpolation; stage boundaries inline away.\nuse vstd::prelude::*;\nuse vstd::arithmetic::div_mod::*;\nuse crate::radix::*;\nuse crate::{toom_words,scaled_subtraction,wide_odd_division,toom8_newton_spec as model};\nverus! {\n']
for plan in certificate['plans']:
    d=plan['degree'];name='even' if d==5 else 'odd';groups=[]
    for op in [op for op in certificate['operations'] if op['degree']==d]:
        key='_'.join(op['name'].split('_')[:-1])
        if not groups or groups[-1][0]!=key:groups.append((key,[]))
        groups[-1][1].append(op)
    states=[[v[:] for v in plan['input_evaluations']]]
    for _,ops in groups:
        state=[v[:] for v in states[-1]]
        for op in ops:
            assert state[op['slot']]==op['before'] and state[op['rhs_slot']]==op['rhs']
            state[op['slot']]=op['after'][:]
        states.append(state)
    states.append([[1 if i==j else 0 for i in range(d+1)] for j in range(d+1)])
    for phase,state in enumerate(states):
        for slot,weights in enumerate(state):
            model+=f'#[verifier::opaque]\npub open spec fn {name}_state_{phase}_{slot}(c:Seq<int>)->int recommends c.len()==7 {{{expression(weights)}}}\n'
    params=','.join(f'a{i}:&mut[u64]' for i in range(d+1))+',Ghost(c):Ghost<Seq<int>>'
    common=['model::nonnegative(c)']+[f'old(a{i})@.len()==old(a0)@.len()' for i in range(1,d+1)]
    length_post=[f'final(a{i})@.len()==old(a{i})@.len()' for i in range(d+1)]
    for phase in range(len(states)-1):
        pre=common+[f'value(old(a{i})@)==model::{name}_state_{phase}_{i}(c)' for i in range(d+1)]
        post=length_post+[f'value(final(a{i})@)==model::{name}_state_{phase+1}_{i}(c)' for i in range(d+1)]
        parts.append(f'#[inline(always)]\nfn {name}_phase_{phase}({params})\n    requires '+',\n        '.join(pre)+',\n    ensures '+',\n        '.join(post)+',\n{\n')
        parts.append('    proof {\n'+''.join(f'        reveal(model::{name}_state_{p}_{i});\n' for p in [phase,phase+1] for i in range(d+1))+'    }\n')
        if phase<len(groups):
            for op in groups[phase][1]:parts.append(arithmetic(op))
        else:
            for i in range(d):
                factor=64**(d-i)
                parts.append(f'    proof {{ lemma_mod_multiples_basic(c[{i}],{factor}int); }}\n    toom_words::divide_exact(a{i},{factor}u64);\n    assert(value(a{i}@)==c[{i}]);\n')
        parts.append('}\n')
    pre=common+[f'value(old(a{i})@)=={expression(v)}' for i,v in enumerate(plan['input_evaluations'])]
    post=length_post+[f'value(final(a{i})@)==c[{i}]' for i in range(d+1)]
    parts.append(f'pub fn {name}({params})\n    requires '+',\n        '.join(pre)+',\n    ensures '+',\n        '.join(post)+',\n{\n')
    parts.append('    assert!('+ ' && '.join(f'a{i}.len()==a0.len()' for i in range(1,d+1))+');\n')
    parts.append('    proof {\n'+''.join(f'        reveal(model::{name}_state_{p}_{i});\n' for p in [0,len(states)-1] for i in range(d+1))+'    }\n')
    for phase in range(len(states)-1):parts.append(f'    {name}_phase_{phase}('+','.join(f'a{i}' for i in range(d+1))+',Ghost(c));\n')
    parts.append('}\n')
parts.append('}\n');model+='}\n'
(S/'candidate/native/specs/toom8_newton.rs').write_text(model)
(S/'candidate/native/verified/toom8_newton.rs').write_text(''.join(parts))
print(json.dumps({'scope':'24 inline phase helpers; ordered arithmetic unchanged','runtime_matrix':False}))

"""Generate ghost-only finite-node algebra from independent homogeneous formulas."""
from pathlib import Path
S=Path(__file__).resolve().parent
points=[(1,8),(1,4),(1,2),(1,1),(2,1),(4,1)]
def branch(values):
    return ' '.join(('if' if i==0 else 'else if')+f' node=={i} {{{v}}}' for i,v in enumerate(values[:-1]))+f' else {{{values[-1]}}}'
def form(indices,weight):return '+'.join(f'{weight(j)}int*c[{index}]' for j,index in enumerate(indices))
header='''//! Endpoint removal and exact homogeneous normalization, independent of outputs.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::radix_add;
use crate::toom8_dyadic_producer_spec::{power,product_weights};
use crate::toom8_convolution as convolution;
use crate::toom8_newton_spec as newton;
verus! {
pub open spec fn nonnegative(c:Seq<int>)->bool {c.len()==15 && forall|j:int|0<=j<15 ==> #[trigger] c[j]>=0}
pub open spec fn bounded(c:Seq<int>,r:int)->bool {r>0 && c.len()==15 && forall|j:int|0<=j<15 ==> 0<=#[trigger] c[j]<8*r*r}
pub open spec fn exponent(node:u32)->u32 {if node==0 {3}else if node==1 {2}else if node==2 {1}else if node==3 {0}else if node==4 {1}else{2}}
pub open spec fn reciprocal(node:u32)->bool {node<3}
pub open spec fn point(node:u32)->int {if node==0 {1}else if node==1 {4}else if node==2 {16}else if node==3 {64}else if node==4 {256}else{1024}}
pub open spec fn even_coefficients(c:Seq<int>)->Seq<int> recommends c.len()==15 {seq![c[2],c[4],c[6],c[8],c[10],c[12],0]}
pub open spec fn odd_coefficients(c:Seq<int>)->Seq<int> recommends c.len()==15 {seq![c[1],c[3],c[5],c[7],c[9],c[11],c[13]]}
pub open spec fn raw_even(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {convolution::even_value(c,product_weights(exponent(node),reciprocal(node)))}
pub open spec fn raw_odd(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {convolution::odd_value(c,product_weights(exponent(node),reciprocal(node)))}
'''
text=header
for name,values,typ in [
    ('low_multiplier',[q**14 for p,q in points],'int'),('high_multiplier',[p**14 for p,q in points],'int'),
    ('even_divisor',[(p*q)**2 for p,q in points],'int'),('odd_divisor',[p*q for p,q in points],'int'),
    ('even_scale',[(64//(q*q))**5 for p,q in points],'int'),('odd_scale',[(64//(q*q))**6 for p,q in points],'int')]:
    text+=f'pub open spec fn {name}(node:u32)->{typ} {{{branch(values)}}}\n'
for name,indices,getweights in [
    ('even_quotient',range(2,14,2),lambda p,q:[p**(2*j)*q**(10-2*j) for j in range(6)]),
    ('odd_quotient',range(1,14,2),lambda p,q:[p**(2*j)*q**(12-2*j) for j in range(7)]),
    ('normalized_even',range(2,14,2),lambda p,q:[64**(5-j)*(64*p*p//(q*q))**j for j in range(6)]),
    ('normalized_odd',range(1,14,2),lambda p,q:[64**(6-j)*(64*p*p//(q*q))**j for j in range(7)])]:
    forms=[]
    for p,q in points:
        ws=getweights(p,q);forms.append(form(indices,lambda j:ws[j]))
    text+=f'pub open spec fn {name}(c:Seq<int>,node:u32)->int recommends c.len()==15,node<6 {{{branch(forms)}}}\n'
for i,(p,q) in enumerate(points):
    claims=[f'product_weights(exponent({i}),reciprocal({i}))[{d}]=={p**d*q**(14-d)}int' for d in range(15)]
    text+=f'pub proof fn node_{i}_constants()\n    ensures '+',\n        '.join(claims)+',\n{\n'
    for claim in claims:text+=f'    assert({claim}) by(compute);\n'
    text+='}\n'
text+='''
pub proof fn relations(c:Seq<int>,node:u32)
    requires nonnegative(c),node<6,
    ensures raw_even(c,node)==low_multiplier(node)*c[0]+high_multiplier(node)*c[14]+even_divisor(node)*even_quotient(c,node),
        raw_odd(c,node)==odd_divisor(node)*odd_quotient(c,node),
        normalized_even(c,node)==even_scale(node)*even_quotient(c,node),
        normalized_odd(c,node)==odd_scale(node)*odd_quotient(c,node),
        even_quotient(c,node)>=0,odd_quotient(c,node)>=0,
        low_multiplier(node)>0,high_multiplier(node)>0,even_divisor(node)>0,odd_divisor(node)>0,
        even_scale(node)>0,odd_scale(node)>0,
        newton::nonnegative(even_coefficients(c)),newton::nonnegative(odd_coefficients(c)),
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0 && c[7]>=0 && c[8]>=0 && c[9]>=0 && c[10]>=0 && c[11]>=0 && c[12]>=0 && c[13]>=0 && c[14]>=0);
    reveal_with_fuel(power,15);
    if node==0 {node_0_constants();}else if node==1 {node_1_constants();}else if node==2 {node_2_constants();}
    else if node==3 {node_3_constants();}else if node==4 {node_4_constants();}else {assert(node==5);node_5_constants();}
    assert forall|j:int|0<=j<7 implies #[trigger] even_coefficients(c)[j]>=0 by {if j==0 {}else if j==1 {}else if j==2 {}else if j==3 {}else if j==4 {}else if j==5 {}else {assert(j==6);}}
    assert forall|j:int|0<=j<7 implies #[trigger] odd_coefficients(c)[j]>=0 by {if j==0 {}else if j==1 {}else if j==2 {}else if j==3 {}else if j==4 {}else if j==5 {}else {assert(j==6);}}
}
pub proof fn normalization_capacity(c:Seq<int>,node:u32,k:nat)
    requires bounded(c,radix(k)),node<6,
    ensures normalized_even(c,node)<radix(2*(k+1)),normalized_odd(c,node)<radix(2*(k+1)),
{
    let r=radix(k);let bound=8*r*r;
    assert(c[0]<bound && c[1]<bound && c[2]<bound && c[3]<bound && c[4]<bound && c[5]<bound && c[6]<bound && c[7]<bound && c[8]<bound && c[9]<bound && c[10]<bound && c[11]<bound && c[12]<bound && c[13]<bound && c[14]<bound);
    if node==0 {}else if node==1 {}else if node==2 {}else if node==3 {}else if node==4 {}else {assert(node==5);}
    assert(normalized_even(c,node)<37778931862957161709568int*bound);
    assert(normalized_odd(c,node)<37778931862957161709568int*bound);
    radix_add(k+1,k+1);radix_positive(k);
    assert(radix(2*(k+1))==340282366920938463463374607431768211456int*r*r) by(nonlinear_arith)
        requires radix(k+1)==18446744073709551616int*r,radix(2*(k+1))==radix(k+1)*radix(k+1);
    assert(normalized_even(c,node)<radix(2*(k+1)) && normalized_odd(c,node)<radix(2*(k+1))) by(nonlinear_arith)
        requires r>0,bound==8*r*r,normalized_even(c,node)<37778931862957161709568int*bound,normalized_odd(c,node)<37778931862957161709568int*bound,
            radix(2*(k+1))==340282366920938463463374607431768211456int*r*r;
}
'''
for i in range(6):
    text+=f'''pub proof fn newton_node_{i}(c:Seq<int>)
    requires nonnegative(c),
    ensures normalized_even(c,{i})==newton::even_state_0_{i}(even_coefficients(c)),
        normalized_odd(c,{i})==newton::odd_state_0_{i}(odd_coefficients(c)),
{{
    reveal(newton::even_state_0_{i});reveal(newton::odd_state_0_{i});
}}
'''
text+='}\n'
(S/'candidate/native/specs/toom8_normalization.rs').write_text(text)
print('Generated independent finite-node normalization identities')

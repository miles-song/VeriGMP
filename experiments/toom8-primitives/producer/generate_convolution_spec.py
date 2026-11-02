"""Emit ghost-only finite convolution identities; no runtime matrix algorithm."""
from pathlib import Path
S=Path(__file__).resolve().parent
def sumof(terms):return '+'.join(terms) or '0'
coeff=[sumof([f'a[{i}]*b[{j}]' for i in range(8) for j in range(8) if i+j==d]) for d in range(15)]
lines=['//! Input convolution is defined independently of every executable output.',
 'use vstd::prelude::*;','use vstd::arithmetic::mul::*;',
 'use crate::toom8_producer_spec as pair;','use crate::toom4;','verus! {',
 'pub open spec fn coefficients(a:Seq<int>,b:Seq<int>)->Seq<int> recommends a.len()==8,b.len()==8 {',
 '    seq!['+',\n        '.join(coeff)+']','}',
 'pub open spec fn even_value(c:Seq<int>,v:Seq<int>)->int recommends c.len()==15,v.len()==15 {',
 '    '+sumof([f'v[{i}]*c[{i}]' for i in range(0,15,2)]),'}',
 'pub open spec fn odd_value(c:Seq<int>,v:Seq<int>)->int recommends c.len()==15,v.len()==15 {',
 '    '+sumof([f'v[{i}]*c[{i}]' for i in range(1,15,2)]),'}',
 'pub open spec fn multiplicative_weights(w:Seq<u64>,v:Seq<int>)->bool {',
 '    w.len()==8 && v.len()==15 && forall|i:int,j:int|0<=i<8 && 0<=j<8 ==> #[trigger] ((w[i] as int)*(w[j] as int))==v[i+j]',
 '}',
 'pub proof fn nonnegative_coefficients(a:Seq<int>,b:Seq<int>,r:int)',
 '    requires pair::bounded(a,r),pair::bounded(b,r),',
 '    ensures coefficients(a,b).len()==15,forall|d:int|0<=d<15 ==> 0<=#[trigger] coefficients(a,b)[d]<8*r*r,',
 '{',
 '    assert forall|i:int,j:int|0<=i<8 && 0<=j<8 implies 0<=#[trigger] (a[i]*b[j])<r*r by {',
 '        assert(0<=a[i]<r && 0<=b[j]<r);',
 '        assert(0<=a[i]*b[j]<r*r) by(nonlinear_arith) requires r>0,0<=a[i]<r,0<=b[j]<r;',
 '    }',
 '    lemma_mul_is_associative(8,r,r);',
 '    assert forall|d:int|0<=d<15 implies 0<=#[trigger] coefficients(a,b)[d]<8*r*r by {}',
 '}',
 'pub proof fn products_to_coefficients(a:Seq<int>,b:Seq<int>,w:Seq<u64>,v:Seq<int>)',
 '    requires a.len()==8,b.len()==8,multiplicative_weights(w,v),',
 '    ensures pair::even_product(a,b,w)==even_value(coefficients(a,b),v),',
 '        pair::odd_product(a,b,w)==odd_value(coefficients(a,b),v),','{']
for left,right in [(range(0,8,2),range(0,8,2)),(range(1,8,2),range(1,8,2)),(range(0,8,2),range(1,8,2)),(range(1,8,2),range(0,8,2))]:
    args=[f'(w[{i}] as int)*a[{i}]' for i in left]+[f'(w[{j}] as int)*b[{j}]' for j in right]
    lines.append('    toom4::quad_product('+','.join(args)+');')
for i in range(8):
 for j in range(8):
    lines += [f'    toom4::monomial_mul(a[{i}],b[{j}],w[{i}] as int,w[{j}] as int);',
              f'    assert((w[{i}] as int)*(w[{j}] as int)==v[{i+j}]);']
for d in range(15):
    terms=[f'a[{i}]*b[{j}]' for i in range(8) for j in range(8) if i+j==d]
    for end in range(2,len(terms)+1):
        lines.append(f'    lemma_mul_is_distributive_add(v[{d}],{sumof(terms[:end-1])},{terms[end-1]});')
lines+=['}','}']
(S/'candidate/native/specs/toom8_convolution.rs').write_text('\n'.join(lines)+'\n')
lib=S/'candidate/native/lib.rs';text=lib.read_text()
line='#[path="specs/toom8_convolution.rs"] pub mod toom8_convolution;\n'
if line not in text:lib.write_text(text+'\n'+line)

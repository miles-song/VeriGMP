//! Arbitrary-radix input decomposition and fifteen-coefficient reconstruction.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::product::radix_add;
use crate::fast_product::{part,split,segment_split};
use crate::toom8_convolution as convolution;
use crate::toom8_producer_spec as input;
use crate::toom4;
verus! {
pub open spec fn even(a:Seq<int>,w:Seq<int>)->int recommends a.len()==8,w.len()==8 {w[0]*a[0]+w[2]*a[2]+w[4]*a[4]+w[6]*a[6]}
pub open spec fn odd(a:Seq<int>,w:Seq<int>)->int recommends a.len()==8,w.len()==8 {w[1]*a[1]+w[3]*a[3]+w[5]*a[5]+w[7]*a[7]}
pub open spec fn even_product(a:Seq<int>,b:Seq<int>,w:Seq<int>)->int recommends a.len()==8,b.len()==8,w.len()==8 {even(a,w)*even(b,w)+odd(a,w)*odd(b,w)}
pub open spec fn odd_product(a:Seq<int>,b:Seq<int>,w:Seq<int>)->int recommends a.len()==8,b.len()==8,w.len()==8 {even(a,w)*odd(b,w)+odd(a,w)*even(b,w)}
pub open spec fn multiplicative_weights(w:Seq<int>,v:Seq<int>)->bool {
    w.len()==8 && v.len()==15 && forall|i:int,j:int|0<=i<8 && 0<=j<8 ==> #[trigger] (w[i]*w[j])==v[i+j]
}
pub proof fn arbitrary_weight_products(a:Seq<int>,b:Seq<int>,w:Seq<int>,v:Seq<int>)
    requires a.len()==8,b.len()==8,multiplicative_weights(w,v),
    ensures even_product(a,b,w)==convolution::even_value(convolution::coefficients(a,b),v),
        odd_product(a,b,w)==convolution::odd_value(convolution::coefficients(a,b),v),
{
    toom4::quad_product((w[0] as int)*a[0],(w[2] as int)*a[2],(w[4] as int)*a[4],(w[6] as int)*a[6],(w[0] as int)*b[0],(w[2] as int)*b[2],(w[4] as int)*b[4],(w[6] as int)*b[6]);
    toom4::quad_product((w[1] as int)*a[1],(w[3] as int)*a[3],(w[5] as int)*a[5],(w[7] as int)*a[7],(w[1] as int)*b[1],(w[3] as int)*b[3],(w[5] as int)*b[5],(w[7] as int)*b[7]);
    toom4::quad_product((w[0] as int)*a[0],(w[2] as int)*a[2],(w[4] as int)*a[4],(w[6] as int)*a[6],(w[1] as int)*b[1],(w[3] as int)*b[3],(w[5] as int)*b[5],(w[7] as int)*b[7]);
    toom4::quad_product((w[1] as int)*a[1],(w[3] as int)*a[3],(w[5] as int)*a[5],(w[7] as int)*a[7],(w[0] as int)*b[0],(w[2] as int)*b[2],(w[4] as int)*b[4],(w[6] as int)*b[6]);
    toom4::monomial_mul(a[0],b[0],w[0] as int,w[0] as int);
    assert((w[0] as int)*(w[0] as int)==v[0]);
    toom4::monomial_mul(a[0],b[1],w[0] as int,w[1] as int);
    assert((w[0] as int)*(w[1] as int)==v[1]);
    toom4::monomial_mul(a[0],b[2],w[0] as int,w[2] as int);
    assert((w[0] as int)*(w[2] as int)==v[2]);
    toom4::monomial_mul(a[0],b[3],w[0] as int,w[3] as int);
    assert((w[0] as int)*(w[3] as int)==v[3]);
    toom4::monomial_mul(a[0],b[4],w[0] as int,w[4] as int);
    assert((w[0] as int)*(w[4] as int)==v[4]);
    toom4::monomial_mul(a[0],b[5],w[0] as int,w[5] as int);
    assert((w[0] as int)*(w[5] as int)==v[5]);
    toom4::monomial_mul(a[0],b[6],w[0] as int,w[6] as int);
    assert((w[0] as int)*(w[6] as int)==v[6]);
    toom4::monomial_mul(a[0],b[7],w[0] as int,w[7] as int);
    assert((w[0] as int)*(w[7] as int)==v[7]);
    toom4::monomial_mul(a[1],b[0],w[1] as int,w[0] as int);
    assert((w[1] as int)*(w[0] as int)==v[1]);
    toom4::monomial_mul(a[1],b[1],w[1] as int,w[1] as int);
    assert((w[1] as int)*(w[1] as int)==v[2]);
    toom4::monomial_mul(a[1],b[2],w[1] as int,w[2] as int);
    assert((w[1] as int)*(w[2] as int)==v[3]);
    toom4::monomial_mul(a[1],b[3],w[1] as int,w[3] as int);
    assert((w[1] as int)*(w[3] as int)==v[4]);
    toom4::monomial_mul(a[1],b[4],w[1] as int,w[4] as int);
    assert((w[1] as int)*(w[4] as int)==v[5]);
    toom4::monomial_mul(a[1],b[5],w[1] as int,w[5] as int);
    assert((w[1] as int)*(w[5] as int)==v[6]);
    toom4::monomial_mul(a[1],b[6],w[1] as int,w[6] as int);
    assert((w[1] as int)*(w[6] as int)==v[7]);
    toom4::monomial_mul(a[1],b[7],w[1] as int,w[7] as int);
    assert((w[1] as int)*(w[7] as int)==v[8]);
    toom4::monomial_mul(a[2],b[0],w[2] as int,w[0] as int);
    assert((w[2] as int)*(w[0] as int)==v[2]);
    toom4::monomial_mul(a[2],b[1],w[2] as int,w[1] as int);
    assert((w[2] as int)*(w[1] as int)==v[3]);
    toom4::monomial_mul(a[2],b[2],w[2] as int,w[2] as int);
    assert((w[2] as int)*(w[2] as int)==v[4]);
    toom4::monomial_mul(a[2],b[3],w[2] as int,w[3] as int);
    assert((w[2] as int)*(w[3] as int)==v[5]);
    toom4::monomial_mul(a[2],b[4],w[2] as int,w[4] as int);
    assert((w[2] as int)*(w[4] as int)==v[6]);
    toom4::monomial_mul(a[2],b[5],w[2] as int,w[5] as int);
    assert((w[2] as int)*(w[5] as int)==v[7]);
    toom4::monomial_mul(a[2],b[6],w[2] as int,w[6] as int);
    assert((w[2] as int)*(w[6] as int)==v[8]);
    toom4::monomial_mul(a[2],b[7],w[2] as int,w[7] as int);
    assert((w[2] as int)*(w[7] as int)==v[9]);
    toom4::monomial_mul(a[3],b[0],w[3] as int,w[0] as int);
    assert((w[3] as int)*(w[0] as int)==v[3]);
    toom4::monomial_mul(a[3],b[1],w[3] as int,w[1] as int);
    assert((w[3] as int)*(w[1] as int)==v[4]);
    toom4::monomial_mul(a[3],b[2],w[3] as int,w[2] as int);
    assert((w[3] as int)*(w[2] as int)==v[5]);
    toom4::monomial_mul(a[3],b[3],w[3] as int,w[3] as int);
    assert((w[3] as int)*(w[3] as int)==v[6]);
    toom4::monomial_mul(a[3],b[4],w[3] as int,w[4] as int);
    assert((w[3] as int)*(w[4] as int)==v[7]);
    toom4::monomial_mul(a[3],b[5],w[3] as int,w[5] as int);
    assert((w[3] as int)*(w[5] as int)==v[8]);
    toom4::monomial_mul(a[3],b[6],w[3] as int,w[6] as int);
    assert((w[3] as int)*(w[6] as int)==v[9]);
    toom4::monomial_mul(a[3],b[7],w[3] as int,w[7] as int);
    assert((w[3] as int)*(w[7] as int)==v[10]);
    toom4::monomial_mul(a[4],b[0],w[4] as int,w[0] as int);
    assert((w[4] as int)*(w[0] as int)==v[4]);
    toom4::monomial_mul(a[4],b[1],w[4] as int,w[1] as int);
    assert((w[4] as int)*(w[1] as int)==v[5]);
    toom4::monomial_mul(a[4],b[2],w[4] as int,w[2] as int);
    assert((w[4] as int)*(w[2] as int)==v[6]);
    toom4::monomial_mul(a[4],b[3],w[4] as int,w[3] as int);
    assert((w[4] as int)*(w[3] as int)==v[7]);
    toom4::monomial_mul(a[4],b[4],w[4] as int,w[4] as int);
    assert((w[4] as int)*(w[4] as int)==v[8]);
    toom4::monomial_mul(a[4],b[5],w[4] as int,w[5] as int);
    assert((w[4] as int)*(w[5] as int)==v[9]);
    toom4::monomial_mul(a[4],b[6],w[4] as int,w[6] as int);
    assert((w[4] as int)*(w[6] as int)==v[10]);
    toom4::monomial_mul(a[4],b[7],w[4] as int,w[7] as int);
    assert((w[4] as int)*(w[7] as int)==v[11]);
    toom4::monomial_mul(a[5],b[0],w[5] as int,w[0] as int);
    assert((w[5] as int)*(w[0] as int)==v[5]);
    toom4::monomial_mul(a[5],b[1],w[5] as int,w[1] as int);
    assert((w[5] as int)*(w[1] as int)==v[6]);
    toom4::monomial_mul(a[5],b[2],w[5] as int,w[2] as int);
    assert((w[5] as int)*(w[2] as int)==v[7]);
    toom4::monomial_mul(a[5],b[3],w[5] as int,w[3] as int);
    assert((w[5] as int)*(w[3] as int)==v[8]);
    toom4::monomial_mul(a[5],b[4],w[5] as int,w[4] as int);
    assert((w[5] as int)*(w[4] as int)==v[9]);
    toom4::monomial_mul(a[5],b[5],w[5] as int,w[5] as int);
    assert((w[5] as int)*(w[5] as int)==v[10]);
    toom4::monomial_mul(a[5],b[6],w[5] as int,w[6] as int);
    assert((w[5] as int)*(w[6] as int)==v[11]);
    toom4::monomial_mul(a[5],b[7],w[5] as int,w[7] as int);
    assert((w[5] as int)*(w[7] as int)==v[12]);
    toom4::monomial_mul(a[6],b[0],w[6] as int,w[0] as int);
    assert((w[6] as int)*(w[0] as int)==v[6]);
    toom4::monomial_mul(a[6],b[1],w[6] as int,w[1] as int);
    assert((w[6] as int)*(w[1] as int)==v[7]);
    toom4::monomial_mul(a[6],b[2],w[6] as int,w[2] as int);
    assert((w[6] as int)*(w[2] as int)==v[8]);
    toom4::monomial_mul(a[6],b[3],w[6] as int,w[3] as int);
    assert((w[6] as int)*(w[3] as int)==v[9]);
    toom4::monomial_mul(a[6],b[4],w[6] as int,w[4] as int);
    assert((w[6] as int)*(w[4] as int)==v[10]);
    toom4::monomial_mul(a[6],b[5],w[6] as int,w[5] as int);
    assert((w[6] as int)*(w[5] as int)==v[11]);
    toom4::monomial_mul(a[6],b[6],w[6] as int,w[6] as int);
    assert((w[6] as int)*(w[6] as int)==v[12]);
    toom4::monomial_mul(a[6],b[7],w[6] as int,w[7] as int);
    assert((w[6] as int)*(w[7] as int)==v[13]);
    toom4::monomial_mul(a[7],b[0],w[7] as int,w[0] as int);
    assert((w[7] as int)*(w[0] as int)==v[7]);
    toom4::monomial_mul(a[7],b[1],w[7] as int,w[1] as int);
    assert((w[7] as int)*(w[1] as int)==v[8]);
    toom4::monomial_mul(a[7],b[2],w[7] as int,w[2] as int);
    assert((w[7] as int)*(w[2] as int)==v[9]);
    toom4::monomial_mul(a[7],b[3],w[7] as int,w[3] as int);
    assert((w[7] as int)*(w[3] as int)==v[10]);
    toom4::monomial_mul(a[7],b[4],w[7] as int,w[4] as int);
    assert((w[7] as int)*(w[4] as int)==v[11]);
    toom4::monomial_mul(a[7],b[5],w[7] as int,w[5] as int);
    assert((w[7] as int)*(w[5] as int)==v[12]);
    toom4::monomial_mul(a[7],b[6],w[7] as int,w[6] as int);
    assert((w[7] as int)*(w[6] as int)==v[13]);
    toom4::monomial_mul(a[7],b[7],w[7] as int,w[7] as int);
    assert((w[7] as int)*(w[7] as int)==v[14]);
    lemma_mul_is_distributive_add(v[1],a[0]*b[1],a[1]*b[0]);
    lemma_mul_is_distributive_add(v[2],a[0]*b[2],a[1]*b[1]);
    lemma_mul_is_distributive_add(v[2],a[0]*b[2]+a[1]*b[1],a[2]*b[0]);
    lemma_mul_is_distributive_add(v[3],a[0]*b[3],a[1]*b[2]);
    lemma_mul_is_distributive_add(v[3],a[0]*b[3]+a[1]*b[2],a[2]*b[1]);
    lemma_mul_is_distributive_add(v[3],a[0]*b[3]+a[1]*b[2]+a[2]*b[1],a[3]*b[0]);
    lemma_mul_is_distributive_add(v[4],a[0]*b[4],a[1]*b[3]);
    lemma_mul_is_distributive_add(v[4],a[0]*b[4]+a[1]*b[3],a[2]*b[2]);
    lemma_mul_is_distributive_add(v[4],a[0]*b[4]+a[1]*b[3]+a[2]*b[2],a[3]*b[1]);
    lemma_mul_is_distributive_add(v[4],a[0]*b[4]+a[1]*b[3]+a[2]*b[2]+a[3]*b[1],a[4]*b[0]);
    lemma_mul_is_distributive_add(v[5],a[0]*b[5],a[1]*b[4]);
    lemma_mul_is_distributive_add(v[5],a[0]*b[5]+a[1]*b[4],a[2]*b[3]);
    lemma_mul_is_distributive_add(v[5],a[0]*b[5]+a[1]*b[4]+a[2]*b[3],a[3]*b[2]);
    lemma_mul_is_distributive_add(v[5],a[0]*b[5]+a[1]*b[4]+a[2]*b[3]+a[3]*b[2],a[4]*b[1]);
    lemma_mul_is_distributive_add(v[5],a[0]*b[5]+a[1]*b[4]+a[2]*b[3]+a[3]*b[2]+a[4]*b[1],a[5]*b[0]);
    lemma_mul_is_distributive_add(v[6],a[0]*b[6],a[1]*b[5]);
    lemma_mul_is_distributive_add(v[6],a[0]*b[6]+a[1]*b[5],a[2]*b[4]);
    lemma_mul_is_distributive_add(v[6],a[0]*b[6]+a[1]*b[5]+a[2]*b[4],a[3]*b[3]);
    lemma_mul_is_distributive_add(v[6],a[0]*b[6]+a[1]*b[5]+a[2]*b[4]+a[3]*b[3],a[4]*b[2]);
    lemma_mul_is_distributive_add(v[6],a[0]*b[6]+a[1]*b[5]+a[2]*b[4]+a[3]*b[3]+a[4]*b[2],a[5]*b[1]);
    lemma_mul_is_distributive_add(v[6],a[0]*b[6]+a[1]*b[5]+a[2]*b[4]+a[3]*b[3]+a[4]*b[2]+a[5]*b[1],a[6]*b[0]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7],a[1]*b[6]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7]+a[1]*b[6],a[2]*b[5]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7]+a[1]*b[6]+a[2]*b[5],a[3]*b[4]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7]+a[1]*b[6]+a[2]*b[5]+a[3]*b[4],a[4]*b[3]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7]+a[1]*b[6]+a[2]*b[5]+a[3]*b[4]+a[4]*b[3],a[5]*b[2]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7]+a[1]*b[6]+a[2]*b[5]+a[3]*b[4]+a[4]*b[3]+a[5]*b[2],a[6]*b[1]);
    lemma_mul_is_distributive_add(v[7],a[0]*b[7]+a[1]*b[6]+a[2]*b[5]+a[3]*b[4]+a[4]*b[3]+a[5]*b[2]+a[6]*b[1],a[7]*b[0]);
    lemma_mul_is_distributive_add(v[8],a[1]*b[7],a[2]*b[6]);
    lemma_mul_is_distributive_add(v[8],a[1]*b[7]+a[2]*b[6],a[3]*b[5]);
    lemma_mul_is_distributive_add(v[8],a[1]*b[7]+a[2]*b[6]+a[3]*b[5],a[4]*b[4]);
    lemma_mul_is_distributive_add(v[8],a[1]*b[7]+a[2]*b[6]+a[3]*b[5]+a[4]*b[4],a[5]*b[3]);
    lemma_mul_is_distributive_add(v[8],a[1]*b[7]+a[2]*b[6]+a[3]*b[5]+a[4]*b[4]+a[5]*b[3],a[6]*b[2]);
    lemma_mul_is_distributive_add(v[8],a[1]*b[7]+a[2]*b[6]+a[3]*b[5]+a[4]*b[4]+a[5]*b[3]+a[6]*b[2],a[7]*b[1]);
    lemma_mul_is_distributive_add(v[9],a[2]*b[7],a[3]*b[6]);
    lemma_mul_is_distributive_add(v[9],a[2]*b[7]+a[3]*b[6],a[4]*b[5]);
    lemma_mul_is_distributive_add(v[9],a[2]*b[7]+a[3]*b[6]+a[4]*b[5],a[5]*b[4]);
    lemma_mul_is_distributive_add(v[9],a[2]*b[7]+a[3]*b[6]+a[4]*b[5]+a[5]*b[4],a[6]*b[3]);
    lemma_mul_is_distributive_add(v[9],a[2]*b[7]+a[3]*b[6]+a[4]*b[5]+a[5]*b[4]+a[6]*b[3],a[7]*b[2]);
    lemma_mul_is_distributive_add(v[10],a[3]*b[7],a[4]*b[6]);
    lemma_mul_is_distributive_add(v[10],a[3]*b[7]+a[4]*b[6],a[5]*b[5]);
    lemma_mul_is_distributive_add(v[10],a[3]*b[7]+a[4]*b[6]+a[5]*b[5],a[6]*b[4]);
    lemma_mul_is_distributive_add(v[10],a[3]*b[7]+a[4]*b[6]+a[5]*b[5]+a[6]*b[4],a[7]*b[3]);
    lemma_mul_is_distributive_add(v[11],a[4]*b[7],a[5]*b[6]);
    lemma_mul_is_distributive_add(v[11],a[4]*b[7]+a[5]*b[6],a[6]*b[5]);
    lemma_mul_is_distributive_add(v[11],a[4]*b[7]+a[5]*b[6]+a[6]*b[5],a[7]*b[4]);
    lemma_mul_is_distributive_add(v[12],a[5]*b[7],a[6]*b[6]);
    lemma_mul_is_distributive_add(v[12],a[5]*b[7]+a[6]*b[6],a[7]*b[5]);
    lemma_mul_is_distributive_add(v[13],a[6]*b[7],a[7]*b[6]);
}
pub open spec fn input_sum(a:Seq<int>,k:nat)->int recommends a.len()==8 {radix(0*k)*a[0]+radix(1*k)*a[1]+radix(2*k)*a[2]+radix(3*k)*a[3]+radix(4*k)*a[4]+radix(5*k)*a[5]+radix(6*k)*a[6]+radix(7*k)*a[7]}
pub open spec fn coefficient_sum(c:Seq<int>,k:nat)->int recommends c.len()==15 {radix(0*k)*c[0]+radix(1*k)*c[1]+radix(2*k)*c[2]+radix(3*k)*c[3]+radix(4*k)*c[4]+radix(5*k)*c[5]+radix(6*k)*c[6]+radix(7*k)*c[7]+radix(8*k)*c[8]+radix(9*k)*c[9]+radix(10*k)*c[10]+radix(11*k)*c[11]+radix(12*k)*c[12]+radix(13*k)*c[13]+radix(14*k)*c[14]}
pub proof fn input_representation(a:Seq<u64>,k:nat)
    requires 7*k<=a.len()<=8*k,
    ensures value(a)==input_sum(input::blocks(a,k),k),
{
    split(a,7*k);
    segment_split(a,0*k,1*k);
    segment_split(a,1*k,2*k);
    segment_split(a,2*k,3*k);
    segment_split(a,3*k,4*k);
    segment_split(a,4*k,5*k);
    segment_split(a,5*k,6*k);
    segment_split(a,6*k,7*k);
    assert(radix(0)==1);
}
pub proof fn convolution_identity(a:Seq<int>,b:Seq<int>,k:nat)
    requires a.len()==8,b.len()==8,
    ensures input_sum(a,k)*input_sum(b,k)==coefficient_sum(convolution::coefficients(a,b),k),
{
    let w=Seq::new(8,|i:int|radix((i*k) as nat));
    let v=Seq::new(15,|d:int|radix((d*k) as nat));
    assert forall|i:int,j:int|0<=i<8 && 0<=j<8 implies #[trigger] (w[i]*w[j])==v[i+j] by {
        radix_add((i*k) as nat,(j*k) as nat);
        assert(i*k+j*k==(i+j)*k) by(nonlinear_arith);
    }
    arbitrary_weight_products(a,b,w,v);
    let ea=even(a,w);let oa=odd(a,w);let eb=even(b,w);let ob=odd(b,w);
    lemma_mul_is_distributive_add(ea+oa,eb,ob);
    lemma_mul_is_distributive_add_other_way(eb,ea,oa);lemma_mul_is_distributive_add_other_way(ob,ea,oa);
}
pub proof fn recover_input_product(a:Seq<u64>,b:Seq<u64>,k:nat)
    requires a.len()==b.len(),7*k<=a.len()<=8*k,
    ensures coefficient_sum(convolution::coefficients(input::blocks(a,k),input::blocks(b,k)),k)==value(a)*value(b),
        0<=value(a)*value(b)<radix(2*a.len()),
{
    input_representation(a,k);input_representation(b,k);
    convolution_identity(input::blocks(a,k),input::blocks(b,k),k);
    prefix_range(a,a.len());prefix_range(b,b.len());radix_positive(a.len());radix_add(a.len(),a.len());
    assert(0<=value(a)*value(b)<radix(2*a.len())) by(nonlinear_arith)
        requires 0<=value(a)<radix(a.len()),0<=value(b)<radix(a.len()),radix(a.len())>0,radix(2*a.len())==radix(a.len())*radix(a.len());
}
}

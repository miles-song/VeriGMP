//! Input convolution is defined independently of every executable output.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
use crate::toom8_producer_spec as pair;
use crate::toom4;
verus! {
pub open spec fn coefficients(a:Seq<int>,b:Seq<int>)->Seq<int> recommends a.len()==8,b.len()==8 {
    seq![a[0]*b[0],
        a[0]*b[1]+a[1]*b[0],
        a[0]*b[2]+a[1]*b[1]+a[2]*b[0],
        a[0]*b[3]+a[1]*b[2]+a[2]*b[1]+a[3]*b[0],
        a[0]*b[4]+a[1]*b[3]+a[2]*b[2]+a[3]*b[1]+a[4]*b[0],
        a[0]*b[5]+a[1]*b[4]+a[2]*b[3]+a[3]*b[2]+a[4]*b[1]+a[5]*b[0],
        a[0]*b[6]+a[1]*b[5]+a[2]*b[4]+a[3]*b[3]+a[4]*b[2]+a[5]*b[1]+a[6]*b[0],
        a[0]*b[7]+a[1]*b[6]+a[2]*b[5]+a[3]*b[4]+a[4]*b[3]+a[5]*b[2]+a[6]*b[1]+a[7]*b[0],
        a[1]*b[7]+a[2]*b[6]+a[3]*b[5]+a[4]*b[4]+a[5]*b[3]+a[6]*b[2]+a[7]*b[1],
        a[2]*b[7]+a[3]*b[6]+a[4]*b[5]+a[5]*b[4]+a[6]*b[3]+a[7]*b[2],
        a[3]*b[7]+a[4]*b[6]+a[5]*b[5]+a[6]*b[4]+a[7]*b[3],
        a[4]*b[7]+a[5]*b[6]+a[6]*b[5]+a[7]*b[4],
        a[5]*b[7]+a[6]*b[6]+a[7]*b[5],
        a[6]*b[7]+a[7]*b[6],
        a[7]*b[7]]
}
pub open spec fn even_value(c:Seq<int>,v:Seq<int>)->int recommends c.len()==15,v.len()==15 {
    v[0]*c[0]+v[2]*c[2]+v[4]*c[4]+v[6]*c[6]+v[8]*c[8]+v[10]*c[10]+v[12]*c[12]+v[14]*c[14]
}
pub open spec fn odd_value(c:Seq<int>,v:Seq<int>)->int recommends c.len()==15,v.len()==15 {
    v[1]*c[1]+v[3]*c[3]+v[5]*c[5]+v[7]*c[7]+v[9]*c[9]+v[11]*c[11]+v[13]*c[13]
}
pub open spec fn multiplicative_weights(w:Seq<u64>,v:Seq<int>)->bool {
    w.len()==8 && v.len()==15 && forall|i:int,j:int|0<=i<8 && 0<=j<8 ==> #[trigger] ((w[i] as int)*(w[j] as int))==v[i+j]
}
pub proof fn nonnegative_coefficients(a:Seq<int>,b:Seq<int>,r:int)
    requires pair::bounded(a,r),pair::bounded(b,r),
    ensures coefficients(a,b).len()==15,forall|d:int|0<=d<15 ==> 0<=#[trigger] coefficients(a,b)[d]<8*r*r,
{
    assert forall|i:int,j:int|0<=i<8 && 0<=j<8 implies 0<=#[trigger] (a[i]*b[j])<r*r by {
        assert(0<=a[i]<r && 0<=b[j]<r);
        assert(0<=a[i]*b[j]<r*r) by(nonlinear_arith) requires r>0,0<=a[i]<r,0<=b[j]<r;
    }
    lemma_mul_is_associative(8,r,r);
    assert forall|d:int|0<=d<15 implies 0<=#[trigger] coefficients(a,b)[d]<8*r*r by {}
}
pub proof fn products_to_coefficients(a:Seq<int>,b:Seq<int>,w:Seq<u64>,v:Seq<int>)
    requires a.len()==8,b.len()==8,multiplicative_weights(w,v),
    ensures pair::even_product(a,b,w)==even_value(coefficients(a,b),v),
        pair::odd_product(a,b,w)==odd_value(coefficients(a,b),v),
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
}

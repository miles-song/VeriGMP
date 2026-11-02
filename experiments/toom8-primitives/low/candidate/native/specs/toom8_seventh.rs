//! Single positive-eight point and seventh odd Newton node, input-defined.
use vstd::prelude::*;
use crate::radix::*;
use crate::product::radix_add;
use crate::toom8_normalization_spec as normalization;
use crate::toom8_dyadic_producer_spec as dyadic;
use crate::toom8_convolution as convolution;
use crate::toom8_producer_spec as input;
use crate::toom8_evaluation_spec::{weights_valid,point_weight};
verus! {
pub open spec fn positive(c:Seq<int>)->int recommends c.len()==15 {1int*c[0]+8int*c[1]+64int*c[2]+512int*c[3]+4096int*c[4]+32768int*c[5]+262144int*c[6]+2097152int*c[7]+16777216int*c[8]+134217728int*c[9]+1073741824int*c[10]+8589934592int*c[11]+68719476736int*c[12]+549755813888int*c[13]+4398046511104int*c[14]}
pub open spec fn even_part(c:Seq<int>)->int recommends c.len()==15 {1int*c[0]+64int*c[2]+4096int*c[4]+262144int*c[6]+16777216int*c[8]+1073741824int*c[10]+68719476736int*c[12]+4398046511104int*c[14]}
pub open spec fn quotient(c:Seq<int>)->int recommends c.len()==15 {1int*c[1]+64int*c[3]+4096int*c[5]+262144int*c[7]+16777216int*c[9]+1073741824int*c[11]+68719476736int*c[13]}
pub open spec fn normalized(c:Seq<int>)->int recommends c.len()==15 {68719476736int*c[1]+4398046511104int*c[3]+281474976710656int*c[5]+18014398509481984int*c[7]+1152921504606846976int*c[9]+73786976294838206464int*c[11]+4722366482869645213696int*c[13]}
pub proof fn point_constants()
    ensures dyadic::product_weights(3,false)[0]==1int,
        dyadic::product_weights(3,false)[1]==8int,
        dyadic::product_weights(3,false)[2]==64int,
        dyadic::product_weights(3,false)[3]==512int,
        dyadic::product_weights(3,false)[4]==4096int,
        dyadic::product_weights(3,false)[5]==32768int,
        dyadic::product_weights(3,false)[6]==262144int,
        dyadic::product_weights(3,false)[7]==2097152int,
        dyadic::product_weights(3,false)[8]==16777216int,
        dyadic::product_weights(3,false)[9]==134217728int,
        dyadic::product_weights(3,false)[10]==1073741824int,
        dyadic::product_weights(3,false)[11]==8589934592int,
        dyadic::product_weights(3,false)[12]==68719476736int,
        dyadic::product_weights(3,false)[13]==549755813888int,
        dyadic::product_weights(3,false)[14]==4398046511104int,
{
    assert(dyadic::product_weights(3,false)[0]==1int) by(compute);
    assert(dyadic::product_weights(3,false)[1]==8int) by(compute);
    assert(dyadic::product_weights(3,false)[2]==64int) by(compute);
    assert(dyadic::product_weights(3,false)[3]==512int) by(compute);
    assert(dyadic::product_weights(3,false)[4]==4096int) by(compute);
    assert(dyadic::product_weights(3,false)[5]==32768int) by(compute);
    assert(dyadic::product_weights(3,false)[6]==262144int) by(compute);
    assert(dyadic::product_weights(3,false)[7]==2097152int) by(compute);
    assert(dyadic::product_weights(3,false)[8]==16777216int) by(compute);
    assert(dyadic::product_weights(3,false)[9]==134217728int) by(compute);
    assert(dyadic::product_weights(3,false)[10]==1073741824int) by(compute);
    assert(dyadic::product_weights(3,false)[11]==8589934592int) by(compute);
    assert(dyadic::product_weights(3,false)[12]==68719476736int) by(compute);
    assert(dyadic::product_weights(3,false)[13]==549755813888int) by(compute);
    assert(dyadic::product_weights(3,false)[14]==4398046511104int) by(compute);
}
pub proof fn positive_coefficients(a:Seq<int>,b:Seq<int>,w:Seq<u64>,r:int)
    requires input::bounded(a,r),input::bounded(b,r),weights_valid(w),
        forall|j:int|0<=j<8 ==> #[trigger] (w[j] as int)==point_weight(3,j,false),
    ensures input::evaluate(a,w,false)*input::evaluate(b,w,false)==positive(convolution::coefficients(a,b)),
{
    input::weighted_bounds(a,w,r);input::weighted_bounds(b,w,r);
    input::products(input::even(a,w),input::odd(a,w),input::even(b,w),input::odd(b,w));
    dyadic::selected_weights_are_multiplicative(w,3,false);
    convolution::products_to_coefficients(a,b,w,dyadic::product_weights(3,false));
    point_constants();
}
pub proof fn relations(c:Seq<int>)
    requires normalization::nonnegative(c),
    ensures positive(c)==even_part(c)+8*quotient(c),quotient(c)>=0,
        normalized(c)==68719476736int*quotient(c),
        normalized(c)==crate::toom8_newton_spec::odd_state_0_6(normalization::odd_coefficients(c)),
{
    assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0 && c[7]>=0 && c[8]>=0 && c[9]>=0 && c[10]>=0 && c[11]>=0 && c[12]>=0 && c[13]>=0 && c[14]>=0);
    reveal(crate::toom8_newton_spec::odd_state_0_6);
}
pub proof fn capacity(c:Seq<int>,k:nat)
    requires normalization::bounded(c,radix(k)),
    ensures normalized(c)<radix(2*(k+1)),
{
    let r=radix(k);let bound=8*r*r;
    assert(c[0]<bound && c[1]<bound && c[2]<bound && c[3]<bound && c[4]<bound && c[5]<bound && c[6]<bound && c[7]<bound && c[8]<bound && c[9]<bound && c[10]<bound && c[11]<bound && c[12]<bound && c[13]<bound && c[14]<bound);
    assert(normalized(c)<4797324681009342447616int*bound);
    radix_add(k+1,k+1);radix_positive(k);
    assert(radix(2*(k+1))==340282366920938463463374607431768211456int*r*r) by(nonlinear_arith)
        requires radix(k+1)==18446744073709551616int*r,radix(2*(k+1))==radix(k+1)*radix(k+1);
    assert(normalized(c)<radix(2*(k+1))) by(nonlinear_arith)
        requires r>0,bound==8*r*r,normalized(c)<4797324681009342447616int*bound,
            radix(2*(k+1))==340282366920938463463374607431768211456int*r*r;
}
}

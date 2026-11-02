//! Homogeneous product weights connect actual point pairs to input convolution.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
use crate::toom8_evaluation_spec::{small_power,point_base,point_weight};
use crate::toom8_convolution;
verus! {
pub open spec fn power(x:int,n:nat)->int
    decreases n,
{
    if n==0 {1}else{x*power(x,(n-1) as nat)}
}
pub proof fn power_add(x:int,a:nat,b:nat)
    ensures power(x,a)*power(x,b)==power(x,a+b),
    decreases a,
{
    if a==0 {} else {
        power_add(x,(a-1) as nat,b);
        lemma_mul_is_associative(x,power(x,(a-1) as nat),power(x,b));
    }
}
pub proof fn small_power_agrees(x:int,n:nat)
    requires n<=7,
    ensures small_power(x,n)==power(x,n),
{
    reveal_with_fuel(power,8);
    if n==0 {}else if n==1 {}else if n==2 {}else if n==3 {}
    else if n==4 {}else if n==5 {}else if n==6 {}else {assert(n==7);}
    lemma_mul_is_associative(x,x,x);
    lemma_mul_is_associative(x,x*x,x);
    lemma_mul_is_associative(x,x*x*x,x);
    lemma_mul_is_associative(x,x*x*x*x,x);
    lemma_mul_is_associative(x,x*x*x*x*x,x);
    lemma_mul_is_associative(x,x*x*x*x*x*x,x);
}
pub open spec fn numerator(exponent:u32,reciprocal:bool)->int {
    if reciprocal {1}else{point_base(exponent)}
}
pub open spec fn denominator(exponent:u32,reciprocal:bool)->int {
    if reciprocal {point_base(exponent)}else{1}
}
pub open spec fn product_weights(exponent:u32,reciprocal:bool)->Seq<int> {
    Seq::new(15,|d:int| power(numerator(exponent,reciprocal),d as nat)
        *power(denominator(exponent,reciprocal),(14-d) as nat))
}
pub proof fn homogeneous_weight_product(exponent:u32,reciprocal:bool,i:int,j:int)
    requires exponent<=3,0<=i<8,0<=j<8,
    ensures point_weight(exponent,i,reciprocal)*point_weight(exponent,j,reciprocal)
        ==product_weights(exponent,reciprocal)[i+j],
{
    let p=numerator(exponent,reciprocal);let q=denominator(exponent,reciprocal);
    small_power_agrees(p,i as nat);small_power_agrees(p,j as nat);
    small_power_agrees(q,(7-i) as nat);small_power_agrees(q,(7-j) as nat);
    power_add(p,i as nat,j as nat);power_add(q,(7-i) as nat,(7-j) as nat);
    crate::toom4::monomial_mul(power(p,i as nat),power(p,j as nat),power(q,(7-i) as nat),power(q,(7-j) as nat));
}
pub proof fn selected_weights_are_multiplicative(w:Seq<u64>,exponent:u32,reciprocal:bool)
    requires w.len()==8,exponent<=3,
        forall|j:int|0<=j<8 ==> #[trigger] (w[j] as int)==point_weight(exponent,j,reciprocal),
    ensures toom8_convolution::multiplicative_weights(w,product_weights(exponent,reciprocal)),
{
    assert forall|i:int,j:int|0<=i<8 && 0<=j<8 implies
        #[trigger] ((w[i] as int)*(w[j] as int))==product_weights(exponent,reciprocal)[i+j] by {
        homogeneous_weight_product(exponent,reciprocal,i,j);
    }
}
}

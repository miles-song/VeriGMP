use vstd::prelude::*;
use vstd::arithmetic::mul::*;
verus! {
pub proof fn square_range(x:int,r:int)
    requires 0<=x<r,
    ensures 0<=x*x<r*r,
{
    lemma_mul_nonnegative(x,x);lemma_mul_inequality(x,r,x);
    lemma_mul_strict_inequality(x,r,r);lemma_mul_is_commutative(x,r);
}
pub proof fn signed_square(x:int,magnitude:int,negative:bool)
    requires (if negative {-magnitude}else{magnitude})==x,
    ensures magnitude*magnitude==x*x,
{
    if negative {lemma_mul_cancels_negatives(magnitude,magnitude);}
}
pub proof fn cross(x:int,y:int,d:int,r:int)
    requires 0<=x<r,0<=y<r,d==(x-y)*(x-y),
    ensures x*x+y*y-d==2*x*y,0<=x*x+y*y-d<2*r*r,
{
    assert(x*x+y*y-(x-y)*(x-y)==2*x*y) by(nonlinear_arith);
    lemma_mul_nonnegative(x,y);lemma_mul_inequality(x,r,y);
    lemma_mul_strict_inequality(y,r,r);lemma_mul_is_commutative(y,r);
    lemma_mul_is_associative(2,r,r);lemma_mul_is_associative(2,x,y);
}
pub proof fn recompose(x:int,y:int,r:int)
    ensures (x+r*y)*(x+r*y)==x*x+r*(2*x*y)+(r*r)*(y*y),
{
    crate::fast_product::karatsuba_identity(x,y,x,y,r);
    lemma_mul_is_associative(2,x,y);lemma_mul_is_commutative(x,y);
}
}

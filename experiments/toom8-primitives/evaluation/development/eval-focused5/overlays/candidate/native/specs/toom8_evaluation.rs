//! Independent weighted integer meanings for eight-block homogeneous evaluation.
use vstd::prelude::*;
use crate::radix::*;
use vstd::arithmetic::mul::*;
use crate::fast_product::*;
verus! {
pub open spec fn weights_valid(w:Seq<u64>)->bool {w.len()==8 && (w[0] as int)+(w[1] as int)+(w[2] as int)+(w[3] as int)+(w[4] as int)+(w[5] as int)+(w[6] as int)+(w[7] as int)<4194304 && (forall|j:int| 0<=j<8 ==> w[j]<=2097152)}
pub open spec fn weighted(x0:int,x1:int,x2:int,x3:int,x4:int,x5:int,x6:int,x7:int,w:Seq<u64>,negative:bool)->int { (w[0] as int)*x0+(w[2] as int)*x2+(w[4] as int)*x4+(w[6] as int)*x6+(if negative {-((w[1] as int)*x1+(w[3] as int)*x3+(w[5] as int)*x5+(w[7] as int)*x7)} else {(w[1] as int)*x1+(w[3] as int)*x3+(w[5] as int)*x5+(w[7] as int)*x7}) }
pub open spec fn input_prefix(a0:Seq<u64>,a1:Seq<u64>,a2:Seq<u64>,a3:Seq<u64>,a4:Seq<u64>,a5:Seq<u64>,a6:Seq<u64>,a7:Seq<u64>,i:nat,w:Seq<u64>,negative:bool)->int { weighted(extended(a0,i),extended(a1,i),extended(a2,i),extended(a3,i),extended(a4,i),extended(a5,i),extended(a6,i),extended(a7,i),w,negative) }
pub open spec fn evaluation(a0:Seq<u64>,a1:Seq<u64>,a2:Seq<u64>,a3:Seq<u64>,a4:Seq<u64>,a5:Seq<u64>,a6:Seq<u64>,a7:Seq<u64>,w:Seq<u64>,negative:bool)->int { weighted(value(a0),value(a1),value(a2),value(a3),value(a4),value(a5),value(a6),value(a7),w,negative) }
pub proof fn prefix_step(a0:Seq<u64>,a1:Seq<u64>,a2:Seq<u64>,a3:Seq<u64>,a4:Seq<u64>,a5:Seq<u64>,a6:Seq<u64>,a7:Seq<u64>,i:nat,w:Seq<u64>,negative:bool)
    requires w.len()==8,
    ensures input_prefix(a0,a1,a2,a3,a4,a5,a6,a7,i+1,w,negative)==input_prefix(a0,a1,a2,a3,a4,a5,a6,a7,i,w,negative)
        +radix(i)*weighted(digit(a0,i),digit(a1,i),digit(a2,i),digit(a3,i),digit(a4,i),digit(a5,i),digit(a6,i),digit(a7,i),w,negative),
{
    extended_step(a0,i);
    assert((w[0] as int)*extended(a0,i+1)==(w[0] as int)*extended(a0,i)+radix(i)*((w[0] as int)*digit(a0,i))) by(nonlinear_arith)
        requires extended(a0,i+1)==extended(a0,i)+digit(a0,i)*radix(i);
    extended_step(a1,i);
    assert((w[1] as int)*extended(a1,i+1)==(w[1] as int)*extended(a1,i)+radix(i)*((w[1] as int)*digit(a1,i))) by(nonlinear_arith)
        requires extended(a1,i+1)==extended(a1,i)+digit(a1,i)*radix(i);
    extended_step(a2,i);
    assert((w[2] as int)*extended(a2,i+1)==(w[2] as int)*extended(a2,i)+radix(i)*((w[2] as int)*digit(a2,i))) by(nonlinear_arith)
        requires extended(a2,i+1)==extended(a2,i)+digit(a2,i)*radix(i);
    extended_step(a3,i);
    assert((w[3] as int)*extended(a3,i+1)==(w[3] as int)*extended(a3,i)+radix(i)*((w[3] as int)*digit(a3,i))) by(nonlinear_arith)
        requires extended(a3,i+1)==extended(a3,i)+digit(a3,i)*radix(i);
    extended_step(a4,i);
    assert((w[4] as int)*extended(a4,i+1)==(w[4] as int)*extended(a4,i)+radix(i)*((w[4] as int)*digit(a4,i))) by(nonlinear_arith)
        requires extended(a4,i+1)==extended(a4,i)+digit(a4,i)*radix(i);
    extended_step(a5,i);
    assert((w[5] as int)*extended(a5,i+1)==(w[5] as int)*extended(a5,i)+radix(i)*((w[5] as int)*digit(a5,i))) by(nonlinear_arith)
        requires extended(a5,i+1)==extended(a5,i)+digit(a5,i)*radix(i);
    extended_step(a6,i);
    assert((w[6] as int)*extended(a6,i+1)==(w[6] as int)*extended(a6,i)+radix(i)*((w[6] as int)*digit(a6,i))) by(nonlinear_arith)
        requires extended(a6,i+1)==extended(a6,i)+digit(a6,i)*radix(i);
    extended_step(a7,i);
    assert((w[7] as int)*extended(a7,i+1)==(w[7] as int)*extended(a7,i)+radix(i)*((w[7] as int)*digit(a7,i))) by(nonlinear_arith)
        requires extended(a7,i+1)==extended(a7,i)+digit(a7,i)*radix(i);
    let d0=(w[0] as int)*digit(a0,i);
    let d1=(w[1] as int)*digit(a1,i);
    let d2=(w[2] as int)*digit(a2,i);
    let d3=(w[3] as int)*digit(a3,i);
    let d4=(w[4] as int)*digit(a4,i);
    let d5=(w[5] as int)*digit(a5,i);
    let d6=(w[6] as int)*digit(a6,i);
    let d7=(w[7] as int)*digit(a7,i);
    lemma_mul_is_distributive_add(radix(i),d0,d2);
    lemma_mul_is_distributive_add(radix(i),d0+d2,d4);
    lemma_mul_is_distributive_add(radix(i),d0+d2+d4,d6);
    lemma_mul_is_distributive_add(radix(i),d1,d3);
    lemma_mul_is_distributive_add(radix(i),d1+d3,d5);
    lemma_mul_is_distributive_add(radix(i),d1+d3+d5,d7);
    if negative {lemma_mul_is_distributive_sub(radix(i),d0+d2+d4+d6,d1+d3+d5+d7);}
    else {lemma_mul_is_distributive_add(radix(i),d0+d2+d4+d6,d1+d3+d5+d7);}
}

pub open spec fn small_power(x:int,n:nat)->int
    recommends n<=7,
{
    if n==0 {1} else if n==1 {x} else if n==2 {x*x} else if n==3 {x*x*x}
    else if n==4 {x*x*x*x} else if n==5 {x*x*x*x*x}
    else if n==6 {x*x*x*x*x*x} else {x*x*x*x*x*x*x}
}
pub open spec fn point_base(exponent:u32)->int {
    if exponent==0 {1} else if exponent==1 {2} else if exponent==2 {4} else {8}
}
pub open spec fn point_weight(exponent:u32,j:int,reciprocal:bool)->int
    recommends exponent<=3,0<=j<8,
{
    let p=if reciprocal {1} else {point_base(exponent)};
    let q=if reciprocal {point_base(exponent)} else {1};
    small_power(p,j as nat)*small_power(q,(7-j) as nat)
}
pub open spec fn homogeneous(a:Seq<int>,exponent:u32,reciprocal:bool,negative:bool)->int
    recommends a.len()==8,exponent<=3,
{
    point_weight(exponent,0,reciprocal)*a[0]+point_weight(exponent,2,reciprocal)*a[2]
        +point_weight(exponent,4,reciprocal)*a[4]+point_weight(exponent,6,reciprocal)*a[6]
        +(if negative {-(point_weight(exponent,1,reciprocal)*a[1]+point_weight(exponent,3,reciprocal)*a[3]
            +point_weight(exponent,5,reciprocal)*a[5]+point_weight(exponent,7,reciprocal)*a[7])}
        else {point_weight(exponent,1,reciprocal)*a[1]+point_weight(exponent,3,reciprocal)*a[3]
            +point_weight(exponent,5,reciprocal)*a[5]+point_weight(exponent,7,reciprocal)*a[7]})
}
}

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

pub proof fn point_constants()
    ensures point_weight(0,0,false)==1,
        point_weight(0,1,false)==1,
        point_weight(0,2,false)==1,
        point_weight(0,3,false)==1,
        point_weight(0,4,false)==1,
        point_weight(0,5,false)==1,
        point_weight(0,6,false)==1,
        point_weight(0,7,false)==1,
        point_weight(0,0,true)==1,
        point_weight(0,1,true)==1,
        point_weight(0,2,true)==1,
        point_weight(0,3,true)==1,
        point_weight(0,4,true)==1,
        point_weight(0,5,true)==1,
        point_weight(0,6,true)==1,
        point_weight(0,7,true)==1,
        point_weight(1,0,false)==1,
        point_weight(1,1,false)==2,
        point_weight(1,2,false)==4,
        point_weight(1,3,false)==8,
        point_weight(1,4,false)==16,
        point_weight(1,5,false)==32,
        point_weight(1,6,false)==64,
        point_weight(1,7,false)==128,
        point_weight(1,0,true)==128,
        point_weight(1,1,true)==64,
        point_weight(1,2,true)==32,
        point_weight(1,3,true)==16,
        point_weight(1,4,true)==8,
        point_weight(1,5,true)==4,
        point_weight(1,6,true)==2,
        point_weight(1,7,true)==1,
        point_weight(2,0,false)==1,
        point_weight(2,1,false)==4,
        point_weight(2,2,false)==16,
        point_weight(2,3,false)==64,
        point_weight(2,4,false)==256,
        point_weight(2,5,false)==1024,
        point_weight(2,6,false)==4096,
        point_weight(2,7,false)==16384,
        point_weight(2,0,true)==16384,
        point_weight(2,1,true)==4096,
        point_weight(2,2,true)==1024,
        point_weight(2,3,true)==256,
        point_weight(2,4,true)==64,
        point_weight(2,5,true)==16,
        point_weight(2,6,true)==4,
        point_weight(2,7,true)==1,
        point_weight(3,0,false)==1,
        point_weight(3,1,false)==8,
        point_weight(3,2,false)==64,
        point_weight(3,3,false)==512,
        point_weight(3,4,false)==4096,
        point_weight(3,5,false)==32768,
        point_weight(3,6,false)==262144,
        point_weight(3,7,false)==2097152,
        point_weight(3,0,true)==2097152,
        point_weight(3,1,true)==262144,
        point_weight(3,2,true)==32768,
        point_weight(3,3,true)==4096,
        point_weight(3,4,true)==512,
        point_weight(3,5,true)==64,
        point_weight(3,6,true)==8,
        point_weight(3,7,true)==1,
{
    assert(point_weight(0,0,false)==1) by(compute);
    assert(point_weight(0,1,false)==1) by(compute);
    assert(point_weight(0,2,false)==1) by(compute);
    assert(point_weight(0,3,false)==1) by(compute);
    assert(point_weight(0,4,false)==1) by(compute);
    assert(point_weight(0,5,false)==1) by(compute);
    assert(point_weight(0,6,false)==1) by(compute);
    assert(point_weight(0,7,false)==1) by(compute);
    assert(point_weight(0,0,true)==1) by(compute);
    assert(point_weight(0,1,true)==1) by(compute);
    assert(point_weight(0,2,true)==1) by(compute);
    assert(point_weight(0,3,true)==1) by(compute);
    assert(point_weight(0,4,true)==1) by(compute);
    assert(point_weight(0,5,true)==1) by(compute);
    assert(point_weight(0,6,true)==1) by(compute);
    assert(point_weight(0,7,true)==1) by(compute);
    assert(point_weight(1,0,false)==1) by(compute);
    assert(point_weight(1,1,false)==2) by(compute);
    assert(point_weight(1,2,false)==4) by(compute);
    assert(point_weight(1,3,false)==8) by(compute);
    assert(point_weight(1,4,false)==16) by(compute);
    assert(point_weight(1,5,false)==32) by(compute);
    assert(point_weight(1,6,false)==64) by(compute);
    assert(point_weight(1,7,false)==128) by(compute);
    assert(point_weight(1,0,true)==128) by(compute);
    assert(point_weight(1,1,true)==64) by(compute);
    assert(point_weight(1,2,true)==32) by(compute);
    assert(point_weight(1,3,true)==16) by(compute);
    assert(point_weight(1,4,true)==8) by(compute);
    assert(point_weight(1,5,true)==4) by(compute);
    assert(point_weight(1,6,true)==2) by(compute);
    assert(point_weight(1,7,true)==1) by(compute);
    assert(point_weight(2,0,false)==1) by(compute);
    assert(point_weight(2,1,false)==4) by(compute);
    assert(point_weight(2,2,false)==16) by(compute);
    assert(point_weight(2,3,false)==64) by(compute);
    assert(point_weight(2,4,false)==256) by(compute);
    assert(point_weight(2,5,false)==1024) by(compute);
    assert(point_weight(2,6,false)==4096) by(compute);
    assert(point_weight(2,7,false)==16384) by(compute);
    assert(point_weight(2,0,true)==16384) by(compute);
    assert(point_weight(2,1,true)==4096) by(compute);
    assert(point_weight(2,2,true)==1024) by(compute);
    assert(point_weight(2,3,true)==256) by(compute);
    assert(point_weight(2,4,true)==64) by(compute);
    assert(point_weight(2,5,true)==16) by(compute);
    assert(point_weight(2,6,true)==4) by(compute);
    assert(point_weight(2,7,true)==1) by(compute);
    assert(point_weight(3,0,false)==1) by(compute);
    assert(point_weight(3,1,false)==8) by(compute);
    assert(point_weight(3,2,false)==64) by(compute);
    assert(point_weight(3,3,false)==512) by(compute);
    assert(point_weight(3,4,false)==4096) by(compute);
    assert(point_weight(3,5,false)==32768) by(compute);
    assert(point_weight(3,6,false)==262144) by(compute);
    assert(point_weight(3,7,false)==2097152) by(compute);
    assert(point_weight(3,0,true)==2097152) by(compute);
    assert(point_weight(3,1,true)==262144) by(compute);
    assert(point_weight(3,2,true)==32768) by(compute);
    assert(point_weight(3,3,true)==4096) by(compute);
    assert(point_weight(3,4,true)==512) by(compute);
    assert(point_weight(3,5,true)==64) by(compute);
    assert(point_weight(3,6,true)==8) by(compute);
    assert(point_weight(3,7,true)==1) by(compute);
}
}

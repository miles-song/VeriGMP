//! Input-defined eight-block product-pair meanings and capacity obligations.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::product::*;
use crate::toom8_evaluation_spec::{weights_valid,weighted};
verus! {
pub open spec fn blocks(a:Seq<u64>,k:nat)->Seq<int>
    recommends 7*k<=a.len()<=8*k,
{
    seq![value(a.subrange(0,k as int)),value(a.subrange(k as int,(2*k) as int)),
        value(a.subrange((2*k) as int,(3*k) as int)),value(a.subrange((3*k) as int,(4*k) as int)),
        value(a.subrange((4*k) as int,(5*k) as int)),value(a.subrange((5*k) as int,(6*k) as int)),
        value(a.subrange((6*k) as int,(7*k) as int)),value(a.subrange((7*k) as int,a.len() as int))]
}
pub open spec fn bounded(a:Seq<int>,r:int)->bool {
    a.len()==8 && r>0 && forall|j:int|0<=j<8 ==> 0<=#[trigger] a[j]<r
}
pub open spec fn even(a:Seq<int>,w:Seq<u64>)->int recommends a.len()==8,w.len()==8 {
    (w[0] as int)*a[0]+(w[2] as int)*a[2]+(w[4] as int)*a[4]+(w[6] as int)*a[6]
}
pub open spec fn odd(a:Seq<int>,w:Seq<u64>)->int recommends a.len()==8,w.len()==8 {
    (w[1] as int)*a[1]+(w[3] as int)*a[3]+(w[5] as int)*a[5]+(w[7] as int)*a[7]
}
pub open spec fn evaluate(a:Seq<int>,w:Seq<u64>,negative:bool)->int recommends a.len()==8,w.len()==8 {
    even(a,w)+(if negative {-odd(a,w)}else{odd(a,w)})
}
pub open spec fn even_product(a:Seq<int>,b:Seq<int>,w:Seq<u64>)->int recommends a.len()==8,b.len()==8,w.len()==8 {
    even(a,w)*even(b,w)+odd(a,w)*odd(b,w)
}
pub open spec fn odd_product(a:Seq<int>,b:Seq<int>,w:Seq<u64>)->int recommends a.len()==8,b.len()==8,w.len()==8 {
    even(a,w)*odd(b,w)+odd(a,w)*even(b,w)
}
pub open spec fn absolute(x:int)->int {if x<0 {-x}else{x}}
pub proof fn radix_monotone(a:nat,b:nat)
    requires a<=b,
    ensures radix(a)<=radix(b),
{
    radix_add(a,(b-a) as nat);radix_positive(a);radix_positive((b-a) as nat);
    assert(radix(a)<=radix(b)) by(nonlinear_arith)
        requires radix(a)>0,radix((b-a) as nat)>=1,radix(b)==radix(a)*radix((b-a) as nat);
}
pub proof fn input_bounds(a:Seq<u64>,k:nat)
    requires 7*k<=a.len()<=8*k,
    ensures bounded(blocks(a,k),radix(k)),
{
    radix_positive(k);
    prefix_range(a.subrange(0,k as int),k);
    prefix_range(a.subrange(k as int,(2*k) as int),k);
    prefix_range(a.subrange((2*k) as int,(3*k) as int),k);
    prefix_range(a.subrange((3*k) as int,(4*k) as int),k);
    prefix_range(a.subrange((4*k) as int,(5*k) as int),k);
    prefix_range(a.subrange((5*k) as int,(6*k) as int),k);
    prefix_range(a.subrange((6*k) as int,(7*k) as int),k);
    let h=(a.len()-7*k) as nat;
    prefix_range(a.subrange((7*k) as int,a.len() as int),h);radix_monotone(h,k);
    assert forall|j:int|0<=j<8 implies 0<=#[trigger] blocks(a,k)[j]<radix(k) by {
        if j==0 {}else if j==1 {}else if j==2 {}else if j==3 {}
        else if j==4 {}else if j==5 {}else if j==6 {}else {assert(j==7);}
    }
}
pub proof fn term_bound(x:int,w:u64,r:int)
    requires 0<=x<r,
    ensures 0<=(w as int)*x<=(w as int)*r,
{
    assert(0<=(w as int)*x<=(w as int)*r) by(nonlinear_arith)
        requires 0<=x<r,0<=w;
}
pub proof fn weighted_bounds(a:Seq<int>,w:Seq<u64>,r:int)
    requires bounded(a,r),weights_valid(w),
    ensures even(a,w)>=0,odd(a,w)>=0,0<=evaluate(a,w,false)<4194304*r,
        -evaluate(a,w,false)<=evaluate(a,w,true)<=evaluate(a,w,false),
        weighted(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],w,false)==evaluate(a,w,false),
        weighted(a[0],a[1],a[2],a[3],a[4],a[5],a[6],a[7],w,true)==evaluate(a,w,true),
{
    term_bound(a[0],w[0],r);term_bound(a[1],w[1],r);term_bound(a[2],w[2],r);term_bound(a[3],w[3],r);
    term_bound(a[4],w[4],r);term_bound(a[5],w[5],r);term_bound(a[6],w[6],r);term_bound(a[7],w[7],r);
    let sum=(w[0] as int)+(w[1] as int)+(w[2] as int)+(w[3] as int)+(w[4] as int)+(w[5] as int)+(w[6] as int)+(w[7] as int);
    assert((w[0] as int)*r+(w[1] as int)*r+(w[2] as int)*r+(w[3] as int)*r+(w[4] as int)*r+(w[5] as int)*r+(w[6] as int)*r+(w[7] as int)*r==sum*r) by(nonlinear_arith);
    assert(sum*r<4194304*r) by(nonlinear_arith) requires sum<4194304,r>0;
}
pub proof fn products(ea:int,oa:int,eb:int,ob:int)
    requires ea>=0,oa>=0,eb>=0,ob>=0,
    ensures ea*eb+oa*ob>=0,ea*ob+oa*eb>=0,
        (ea+oa)*(eb+ob)==(ea*eb+oa*ob)+(ea*ob+oa*eb),
        (ea-oa)*(eb-ob)==(ea*eb+oa*ob)-(ea*ob+oa*eb),
        absolute((ea-oa)*(eb-ob))<=(ea+oa)*(eb+ob),
        ((ea+oa)*(eb+ob))%2==absolute((ea-oa)*(eb-ob))%2,
{
    let e=ea*eb+oa*ob;let o=ea*ob+oa*eb;
    assert(e>=0 && o>=0) by(nonlinear_arith) requires ea>=0,oa>=0,eb>=0,ob>=0;
    assert((ea+oa)*(eb+ob)==e+o && (ea-oa)*(eb-ob)==e-o) by(nonlinear_arith);
    let d=absolute(e-o);
    lemma_mod_bound(d,2);
    if e>=o {
        assert(e+o==d+2*o);lemma_mod_multiples_basic(o,2);lemma_mod_adds(d,2*o,2);
    } else {
        assert(e+o==d+2*e);lemma_mod_multiples_basic(e,2);lemma_mod_adds(d,2*e,2);
    }
}
pub proof fn product_capacity(ap:int,bp:int,p:int,d:int,k:nat)
    requires 0<=ap<4194304*radix(k),0<=bp<4194304*radix(k),p==ap*bp,0<=d<=p,
    ensures p+d<radix(2*(k+1)),
{
    let r=radix(k);radix_positive(k);radix_add(k+1,k+1);
    assert(p<17592186044416int*r*r) by(nonlinear_arith)
        requires 0<=ap<4194304*r,0<=bp<4194304*r,p==ap*bp,r>0;
    assert(radix(2*(k+1))==340282366920938463463374607431768211456int*r*r) by(nonlinear_arith)
        requires radix(k+1)==18446744073709551616int*r,radix(2*(k+1))==radix(k+1)*radix(k+1);
    assert(p+d<radix(2*(k+1))) by(nonlinear_arith)
        requires r>0,p<17592186044416int*r*r,0<=d<=p,
            radix(2*(k+1))==340282366920938463463374607431768211456int*r*r;
}
}

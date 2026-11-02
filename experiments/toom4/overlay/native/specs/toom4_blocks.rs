//! Four input blocks and seven coefficient slots in base 2^64.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::toom4;
verus! {
pub open spec fn blocks(a:Seq<u64>,k:nat)->Seq<int>
    recommends 3*k<=a.len()<=4*k,
{
    seq![part(a,0,k),part(a,k,2*k),part(a,2*k,3*k),part(a,3*k,a.len())]
}
pub proof fn four_blocks(a:Seq<u64>,k:nat)
    requires 3*k<=a.len()<=4*k,
    ensures blocks(a,k).len()==4,value(a)==toom4::eval(blocks(a,k),radix(k)),
        forall|i:int|0<=i<4 ==> 0<=#[trigger] blocks(a,k)[i]<radix(k),
{
    split(a,3*k);segment_split(a,2*k,3*k);segment_split(a,k,2*k);split(a,k);
    radix_add(k,k);radix_add(2*k,k);
    prefix_range(a.subrange(0,k as int),k);
    prefix_range(a.subrange(k as int,(2*k) as int),k);
    prefix_range(a.subrange((2*k) as int,(3*k) as int),k);
    prefix_range(a.subrange((3*k) as int,a.len() as int),(a.len()-3*k) as nat);
    radix_add((a.len()-3*k) as nat,(4*k-a.len()) as nat);
    radix_positive((4*k-a.len()) as nat);
    assert(radix((a.len()-3*k) as nat)<=radix(k)) by(nonlinear_arith)
        requires radix(k)==radix((a.len()-3*k) as nat)*radix((4*k-a.len()) as nat),
            radix((a.len()-3*k) as nat)>0,radix((4*k-a.len()) as nat)>=1;
    let c=blocks(a,k);assert(c.len()==4);
    assert forall|i:int|0<=i<4 implies 0<=#[trigger] c[i]<radix(k) by {}
}

pub proof fn product_capacity(k:nat,c:Seq<int>)
    requires c.len()==7,0<=toom4::one(c)<16*radix(k)*radix(k),
    ensures 128*toom4::one(c)<radix(2*(k+1)),
{
    radix_add(k,k);radix_add(2*k,2);radix_positive(k);
    reveal_with_fuel(radix,3);
    assert(radix(2)==base()*base());
    assert(128*toom4::one(c)<radix(2*(k+1))) by(nonlinear_arith)
        requires 0<=toom4::one(c)<16*radix(k)*radix(k),
            radix(2*(k+1))==radix(k)*radix(k)*radix(2),radix(2)==base()*base(),radix(k)>0;
}

pub proof fn coefficient_radices(c:Seq<int>,k:nat)
    requires c.len()==7,
    ensures toom4::polynomial(c,radix(k))==c[0]+radix(k)*c[1]+radix(2*k)*c[2]
        +radix(3*k)*c[3]+radix(4*k)*c[4]+radix(5*k)*c[5]+radix(6*k)*c[6],
{
    radix_add(k,k);radix_add(2*k,k);radix_add(3*k,k);radix_add(4*k,k);radix_add(5*k,k);
}

pub proof fn input_model(a:Seq<u64>,b:Seq<u64>,k:nat)
    requires a.len()>0,a.len()==b.len(),3*k<a.len()<=4*k,
    ensures coefficients_for(a,b,k).len()==7,
        forall|i:int|0<=i<7 ==> 0<=#[trigger] coefficients_for(a,b,k)[i],
        128*toom4::one(coefficients_for(a,b,k))<radix(2*(k+1)),
        value(a)*value(b)==toom4::polynomial(coefficients_for(a,b,k),radix(k)),
{
    four_blocks(a,k);four_blocks(b,k);radix_positive(k);
    let aa=blocks(a,k);let bb=blocks(b,k);let c=toom4::coefficients(aa,bb);
    toom4::coefficient_bounds(aa,bb,radix(k));product_capacity(k,c);
    toom4::recompose(aa,bb,radix(k));
}
pub open spec fn coefficients_for(a:Seq<u64>,b:Seq<u64>,k:nat)->Seq<int> {
    toom4::coefficients(blocks(a,k),blocks(b,k))
}
pub proof fn recover_product(dst:Seq<u64>,a:Seq<u64>,b:Seq<u64>,k:nat)
    requires a.len()>0,a.len()==b.len(),dst.len()==2*a.len(),3*k<a.len()<=4*k,
        value(dst)==toom4::polynomial(coefficients_for(a,b,k),radix(k))%radix(dst.len()),
    ensures value(dst)==value(a)*value(b),
{
    input_model(a,b,k);
    prefix_range(a,a.len());prefix_range(b,b.len());radix_add(a.len(),a.len());
    assert(0<=value(a)*value(b)<radix(dst.len())) by(nonlinear_arith)
        requires 0<=value(a)<radix(a.len()),0<=value(b)<radix(a.len()),
            radix(dst.len())==radix(a.len())*radix(a.len());
    lemma_small_mod((value(a)*value(b)) as nat,radix(dst.len()) as nat);
}
}

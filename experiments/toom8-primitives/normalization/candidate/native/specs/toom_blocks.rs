//! Representation and capacity bounds for Toom-3 chunks.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::toom;
verus! {
pub proof fn three_blocks(a:Seq<u64>,k:nat)
    requires 2*k<=a.len()<=3*k,
    ensures value(a)==toom::eval(part(a,0,k),part(a,k,2*k),part(a,2*k,a.len()),radix(k)),
        0<=part(a,0,k)<radix(k),0<=part(a,k,2*k)<radix(k),0<=part(a,2*k,a.len())<radix(k),
{
    split(a,2*k);split(a,k);segment_split(a,k,2*k);radix_add(k,k);
    prefix_range(a.subrange(0,k as int),k);prefix_range(a.subrange(k as int,(2*k) as int),k);
    prefix_range(a.subrange((2*k) as int,a.len() as int),(a.len()-2*k) as nat);
    radix_add((a.len()-2*k) as nat,(3*k-a.len()) as nat);radix_positive((3*k-a.len()) as nat);
    assert(radix((a.len()-2*k) as nat)<=radix(k)) by(nonlinear_arith)
        requires radix(k)==radix((a.len()-2*k) as nat)*radix((3*k-a.len()) as nat),
            radix((a.len()-2*k) as nat)>0,radix((3*k-a.len()) as nat)>=1;
    assert(value(a)==toom::eval(part(a,0,k),part(a,k,2*k),part(a,2*k,a.len()),radix(k))) by(nonlinear_arith)
        requires value(a)==prefix(a,2*k)+radix(2*k)*part(a,2*k,a.len()),
            prefix(a,2*k)==part(a,0,k)+radix(k)*part(a,k,2*k),radix(2*k)==radix(k)*radix(k),
            toom::eval(part(a,0,k),part(a,k,2*k),part(a,2*k,a.len()),radix(k))
                ==part(a,0,k)+radix(k)*part(a,k,2*k)+radix(k)*radix(k)*part(a,2*k,a.len());
}

pub proof fn product_capacity(k:nat,c:Seq<int>)
    requires c.len()==5,0<=c[0]<radix(k)*radix(k),0<=c[4]<radix(k)*radix(k),
        0<=c[1]<2*radix(k)*radix(k),0<=c[2]<3*radix(k)*radix(k),0<=c[3]<2*radix(k)*radix(k),
    ensures 64*(c[0]+c[1]+c[2]+c[3]+c[4])<radix(2*(k+1)),
{
    radix_add(k,k);radix_add(2*k,2);radix_positive(k);
    reveal_with_fuel(radix,3);
    assert(radix(2)==base()*base());
    assert(64*(c[0]+c[1]+c[2]+c[3]+c[4])<radix(2*(k+1))) by(nonlinear_arith)
        requires 0<=c[0]<radix(k)*radix(k),0<=c[4]<radix(k)*radix(k),
            0<=c[1]<2*radix(k)*radix(k),0<=c[2]<3*radix(k)*radix(k),0<=c[3]<2*radix(k)*radix(k),
            radix(2*(k+1))==radix(k)*radix(k)*radix(2),radix(2)==base()*base(),radix(k)>0;
}
}

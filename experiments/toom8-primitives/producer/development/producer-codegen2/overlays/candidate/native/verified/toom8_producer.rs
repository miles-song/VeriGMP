//! Actual eight-block evaluations and products establish pair normalization premises.
use vstd::prelude::*;
use crate::radix::*;
use crate::toom8_evaluation_spec::weights_valid;
use crate::toom8_producer_spec as model;
use crate::{toom8_evaluation,toom8_pair,toom4_multiply,toom4};
verus! {
pub fn weighted_pair(even:&mut[u64],odd:&mut[u64],a:&[u64],b:&[u64],k:usize,weights:[u64;8],scratch:&mut[u64],threshold:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,weights_valid(weights@),threshold>=24,
        old(even)@.len()==2*(k+1),old(odd)@.len()==old(even)@.len(),old(scratch)@.len()>=14*(k+1),
    ensures final(even)@.len()==old(even)@.len(),final(odd)@.len()==old(odd)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(even)@)==model::even_product(model::blocks(a@,k as nat),model::blocks(b@,k as nat),weights@),
        value(final(odd)@)==model::odd_product(model::blocks(a@,k as nat),model::blocks(b@,k as nat),weights@),
{
    let _capacity=scratch.len();
    assert!(k<usize::MAX/14 && scratch.len()>=14*(k+1));
    assert!(a.len()==b.len() && a.len()>=7*k && a.len()<=8*k);
    assert!(even.len()==2*(k+1) && odd.len()==even.len() && threshold>=24);
    let m=k+1;
    let (ax,rest)=scratch.split_at_mut(m);let (bx,work)=rest.split_at_mut(m);
    let a0=&a[..k];let a1=&a[k..2*k];let a2=&a[2*k..3*k];let a3=&a[3*k..4*k];
    let a4=&a[4*k..5*k];let a5=&a[5*k..6*k];let a6=&a[6*k..7*k];let a7=&a[7*k..];
    let b0=&b[..k];let b1=&b[k..2*k];let b2=&b[2*k..3*k];let b3=&b[3*k..4*k];
    let b4=&b[4*k..5*k];let b5=&b[5*k..6*k];let b6=&b[6*k..7*k];let b7=&b[7*k..];
    let ghost aa=model::blocks(a@,k as nat);let ghost bb=model::blocks(b@,k as nat);
    proof {
        model::input_bounds(a@,k as nat);model::input_bounds(b@,k as nat);
        model::weighted_bounds(aa,weights@,radix(k as nat));model::weighted_bounds(bb,weights@,radix(k as nat));
        model::products(model::even(aa,weights@),model::odd(aa,weights@),model::even(bb,weights@),model::odd(bb,weights@));
    }
    let _positive_a=toom8_evaluation::evaluate(ax,&mut work[..m],a0,a1,a2,a3,a4,a5,a6,a7,weights,false);
    let _positive_b=toom8_evaluation::evaluate(bx,&mut work[..m],b0,b1,b2,b3,b4,b5,b6,b7,weights,false);
    toom4_multiply::full(even,ax,bx,work,threshold);
    let na=toom8_evaluation::evaluate(ax,&mut work[..m],a0,a1,a2,a3,a4,a5,a6,a7,weights,true);
    let nb=toom8_evaluation::evaluate(bx,&mut work[..m],b0,b1,b2,b3,b4,b5,b6,b7,weights,true);
    let ghost av=value(ax@);let ghost bv=value(bx@);
    toom4_multiply::full(odd,ax,bx,work,threshold);
    let negative=na!=nb;
    proof {
        toom4::signed_product(av,bv,model::evaluate(aa,weights@,true),model::evaluate(bb,weights@,true),na,nb);
        prefix_range(odd@,odd@.len());
        assert(value(odd@)==model::absolute(model::evaluate(aa,weights@,true)*model::evaluate(bb,weights@,true)));
        model::product_capacity(model::evaluate(aa,weights@,false),model::evaluate(bb,weights@,false),value(even@),value(odd@),k as nat);
    }
    toom8_pair::half_pair(&mut even[..2*m],&mut odd[..2*m],negative);
}
}

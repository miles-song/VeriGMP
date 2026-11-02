//! Actual eight-block evaluations and products establish pair normalization premises.
use vstd::prelude::*;
use crate::radix::*;
use crate::toom8_evaluation_spec::weights_valid;
use crate::toom8_producer_spec as model;
use crate::{toom8_evaluation,toom8_pair,toom8_recursive_square,toom4};
verus! {
#[inline(never)]
fn normalize_pair(plus:&mut[u64],minus:&mut[u64],negative:bool)
    requires old(plus)@.len()==old(minus)@.len(),value(old(minus)@)<=value(old(plus)@),
        value(old(plus)@)+value(old(minus)@)<radix(old(plus)@.len()),
        value(old(plus)@)%2==value(old(minus)@)%2,
    ensures final(plus)@.len()==old(plus)@.len(),final(minus)@.len()==old(minus)@.len(),
        2*value(final(plus)@)==value(old(plus)@)+crate::toom8_pair_spec::signed_magnitude(value(old(minus)@),negative),
        2*value(final(minus)@)==value(old(plus)@)-crate::toom8_pair_spec::signed_magnitude(value(old(minus)@),negative),
{
    toom8_pair::half_pair(plus,minus,negative);
}
pub fn weighted_pair(even:&mut[u64],odd:&mut[u64],a:&[u64],k:usize,weights:[u64;8],scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,7*k<=a@.len()<=8*k,weights_valid(weights@),threshold>=56,
        old(even)@.len()==2*(k+1),old(odd)@.len()==old(even)@.len(),old(scratch)@.len()>=11*(k+1),
    ensures final(even)@.len()==old(even)@.len(),final(odd)@.len()==old(odd)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(even)@)==model::even_product(model::blocks(a@,k as nat),model::blocks(a@,k as nat),weights@),
        value(final(odd)@)==model::odd_product(model::blocks(a@,k as nat),model::blocks(a@,k as nat),weights@),
    decreases a.len(),1nat,

{
    let _capacity=scratch.len();
    assert!(k<usize::MAX/11 && scratch.len()>=11*(k+1));
    assert!(a.len()>=7*k && a.len()<=8*k);
    assert!(even.len()==2*(k+1) && odd.len()==even.len() && threshold>=56);
    let m=k+1;
    let (ax,work)=scratch.split_at_mut(m);
    let a0=&a[..k];let a1=&a[k..2*k];let a2=&a[2*k..3*k];let a3=&a[3*k..4*k];
    let a4=&a[4*k..5*k];let a5=&a[5*k..6*k];let a6=&a[6*k..7*k];let a7=&a[7*k..];
    let ghost aa=model::blocks(a@,k as nat);let ghost bb=model::blocks(a@,k as nat);
    proof {
        model::input_bounds(a@,k as nat);model::input_bounds(a@,k as nat);
        model::weighted_bounds(aa,weights@,radix(k as nat));model::weighted_bounds(bb,weights@,radix(k as nat));
        model::products(model::even(aa,weights@),model::odd(aa,weights@),model::even(bb,weights@),model::odd(bb,weights@));
    }
    let _positive_a=toom8_evaluation::evaluate(ax,&mut work[..m],a0,a1,a2,a3,a4,a5,a6,a7,weights,false);
    toom8_recursive_square::full(even,ax,work,threshold);
    let na=toom8_evaluation::evaluate(ax,&mut work[..m],a0,a1,a2,a3,a4,a5,a6,a7,weights,true);
    let nb=na;
    let ghost av=value(ax@);let ghost bv=av;
    toom8_recursive_square::full(odd,ax,work,threshold);
    let negative=na!=nb;
    proof {
        toom4::signed_product(av,bv,model::evaluate(aa,weights@,true),model::evaluate(bb,weights@,true),na,nb);
        prefix_range(odd@,odd@.len());
        assert(value(odd@)==model::absolute(model::evaluate(aa,weights@,true)*model::evaluate(bb,weights@,true)));
        model::product_capacity(model::evaluate(aa,weights@,false),model::evaluate(bb,weights@,false),value(even@),value(odd@),k as nat);
    }
    normalize_pair(even,odd,negative);
}
}

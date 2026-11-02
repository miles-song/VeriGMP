//! One additional product at +8; no product at -8 is introduced.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::toom8_normalization_spec as normalization;
use crate::toom8_seventh_spec as model;
use crate::{toom8_evaluation,toom8_recursive_square,scaled_subtraction,toom_words};
verus! {
pub fn positive_product(dst:&mut[u64],a:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,7*k<=a@.len()<=8*k,threshold>=56,
        old(dst)@.len()==2*(k+1),old(scratch)@.len()>=11*(k+1),
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==model::positive(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))),
    decreases a.len(),3nat,

{
    let _capacity=scratch.len();
    assert!(k<usize::MAX/11 && scratch.len()>=11*(k+1));
    assert!(a.len()>=7*k && a.len()<=8*k && threshold>=56 && dst.len()==2*(k+1));
    let m=k+1;let (ax,work)=scratch.split_at_mut(m);
    let weights=toom8_evaluation::dyadic_weights(3,false);
    let a0=&a[..1*k];let a1=&a[1*k..2*k];let a2=&a[2*k..3*k];let a3=&a[3*k..4*k];let a4=&a[4*k..5*k];let a5=&a[5*k..6*k];let a6=&a[6*k..7*k];let a7=&a[7*k..];
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(a@,k as nat);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(a@,k as nat);
        input::weighted_bounds(aa,weights@,radix(k as nat));input::weighted_bounds(bb,weights@,radix(k as nat));
    }
    let _na=toom8_evaluation::evaluate(ax,&mut work[..m],a0,a1,a2,a3,a4,a5,a6,a7,weights,false);
    toom8_recursive_square::full(dst,ax,work,threshold);
    proof {model::positive_coefficients(aa,bb,weights@,radix(k as nat));}
}
pub fn prepare_seventh(dst:&mut[u64],a:&[u64],low:&[u64],e0:&[u64],e1:&[u64],e2:&[u64],e3:&[u64],e4:&[u64],e5:&[u64],high:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,7*k<=a@.len()<=8*k,threshold>=56,
        old(dst)@.len()==2*(k+1),old(scratch)@.len()>=11*(k+1),
        low@.len()<=old(dst)@.len(),value(low@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[0],
        e0@.len()<=old(dst)@.len(),value(e0@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[2],
        e1@.len()<=old(dst)@.len(),value(e1@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[4],
        e2@.len()<=old(dst)@.len(),value(e2@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[6],
        e3@.len()<=old(dst)@.len(),value(e3@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[8],
        e4@.len()<=old(dst)@.len(),value(e4@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[10],
        e5@.len()<=old(dst)@.len(),value(e5@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[12],
        high@.len()<=old(dst)@.len(),value(high@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[14],
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==model::normalized(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))),
    decreases a.len(),4nat,

{
    positive_product(dst,a,k,scratch,threshold);
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(a@,k as nat);
    let ghost c=convolution::coefficients(aa,bb);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(a@,k as nat);
        convolution::nonnegative_coefficients(aa,bb,radix(k as nat));
    }
    crate::toom8_seventh::normalize(dst,low,e0,e1,e2,e3,e4,e5,high,k,Ghost(c));
}
}

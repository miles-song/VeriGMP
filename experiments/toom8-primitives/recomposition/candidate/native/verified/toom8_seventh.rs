//! One additional product at +8; no product at -8 is introduced.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::toom8_normalization_spec as normalization;
use crate::toom8_seventh_spec as model;
use crate::{toom8_evaluation,toom4_multiply,scaled_subtraction,toom_words};
verus! {
pub fn positive_product(dst:&mut[u64],a:&[u64],b:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,threshold>=24,
        old(dst)@.len()==2*(k+1),old(scratch)@.len()>=14*(k+1),
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==model::positive(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))),
{
    let _capacity=scratch.len();
    assert!(k<usize::MAX/14 && scratch.len()>=14*(k+1));
    assert!(a.len()==b.len() && a.len()>=7*k && a.len()<=8*k && threshold>=24 && dst.len()==2*(k+1));
    let m=k+1;let (ax,rest)=scratch.split_at_mut(m);let (bx,work)=rest.split_at_mut(m);
    let weights=toom8_evaluation::dyadic_weights(3,false);
    let a0=&a[..1*k];let a1=&a[1*k..2*k];let a2=&a[2*k..3*k];let a3=&a[3*k..4*k];let a4=&a[4*k..5*k];let a5=&a[5*k..6*k];let a6=&a[6*k..7*k];let a7=&a[7*k..];
    let b0=&b[..1*k];let b1=&b[1*k..2*k];let b2=&b[2*k..3*k];let b3=&b[3*k..4*k];let b4=&b[4*k..5*k];let b5=&b[5*k..6*k];let b6=&b[6*k..7*k];let b7=&b[7*k..];
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(b@,k as nat);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(b@,k as nat);
        input::weighted_bounds(aa,weights@,radix(k as nat));input::weighted_bounds(bb,weights@,radix(k as nat));
    }
    let _na=toom8_evaluation::evaluate(ax,&mut work[..m],a0,a1,a2,a3,a4,a5,a6,a7,weights,false);
    let _nb=toom8_evaluation::evaluate(bx,&mut work[..m],b0,b1,b2,b3,b4,b5,b6,b7,weights,false);
    toom4_multiply::full(dst,ax,bx,work,threshold);
    proof {model::positive_coefficients(aa,bb,weights@,radix(k as nat));}
}
#[inline(always)]
pub fn normalize(dst:&mut[u64],low:&[u64],e0:&[u64],e1:&[u64],e2:&[u64],e3:&[u64],e4:&[u64],e5:&[u64],high:&[u64],k:usize,Ghost(c):Ghost<Seq<int>>)
    requires normalization::bounded(c,radix(k as nat)),old(dst)@.len()==2*(k+1),
        value(old(dst)@)==model::positive(c),
        low@.len()<=old(dst)@.len(),value(low@)==c[0],
        e0@.len()<=old(dst)@.len(),value(e0@)==c[2],
        e1@.len()<=old(dst)@.len(),value(e1@)==c[4],
        e2@.len()<=old(dst)@.len(),value(e2@)==c[6],
        e3@.len()<=old(dst)@.len(),value(e3@)==c[8],
        e4@.len()<=old(dst)@.len(),value(e4@)==c[10],
        e5@.len()<=old(dst)@.len(),value(e5@)==c[12],
        high@.len()<=old(dst)@.len(),value(high@)==c[14],
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==model::normalized(c),
{
    proof {model::relations(c);model::capacity(c,k as nat);}
    proof {assert(c[0]>=0 && c[1]>=0 && c[2]>=0 && c[3]>=0 && c[4]>=0 && c[5]>=0 && c[6]>=0 && c[7]>=0 && c[8]>=0 && c[9]>=0 && c[10]>=0 && c[11]>=0 && c[12]>=0 && c[13]>=0 && c[14]>=0);}
    scaled_subtraction::sub_scaled_exact(dst,low,1u64);
    scaled_subtraction::sub_scaled_exact(dst,e0,64u64);
    scaled_subtraction::sub_scaled_exact(dst,e1,4096u64);
    scaled_subtraction::sub_scaled_exact(dst,e2,262144u64);
    scaled_subtraction::sub_scaled_exact(dst,e3,16777216u64);
    scaled_subtraction::sub_scaled_exact(dst,e4,1073741824u64);
    scaled_subtraction::sub_scaled_exact(dst,e5,68719476736u64);
    scaled_subtraction::sub_scaled_exact(dst,high,4398046511104u64);
    let ghost q=model::quotient(c);
    proof {lemma_mod_multiples_basic(q,8int);}
    toom_words::divide_exact(dst,8u64);
    assert(value(dst@)==q);
    toom_words::scale_exact(dst,68719476736u64);
}
pub fn prepare_seventh(dst:&mut[u64],a:&[u64],b:&[u64],low:&[u64],e0:&[u64],e1:&[u64],e2:&[u64],e3:&[u64],e4:&[u64],e5:&[u64],high:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,threshold>=24,
        old(dst)@.len()==2*(k+1),old(scratch)@.len()>=14*(k+1),
        low@.len()<=old(dst)@.len(),value(low@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[0],
        e0@.len()<=old(dst)@.len(),value(e0@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[2],
        e1@.len()<=old(dst)@.len(),value(e1@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[4],
        e2@.len()<=old(dst)@.len(),value(e2@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[6],
        e3@.len()<=old(dst)@.len(),value(e3@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[8],
        e4@.len()<=old(dst)@.len(),value(e4@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[10],
        e5@.len()<=old(dst)@.len(),value(e5@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[12],
        high@.len()<=old(dst)@.len(),value(high@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[14],
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==model::normalized(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))),
{
    positive_product(dst,a,b,k,scratch,threshold);
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(b@,k as nat);
    let ghost c=convolution::coefficients(aa,bb);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(b@,k as nat);
        convolution::nonnegative_coefficients(aa,bb,radix(k as nat));
    }
    normalize(dst,low,e0,e1,e2,e3,e4,e5,high,k,Ghost(c));
}
}

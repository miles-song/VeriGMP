//! Actual endpoint removal and exact scaling for six paired Newton nodes.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::toom8_normalization_spec as model;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::{scaled_subtraction,toom_words,toom8_recursive_product,toom8_recursive_dyadic_producer};
verus! {
pub fn with_endpoints(even:&mut[u64],odd:&mut[u64],a:&[u64],b:&[u64],low:&[u64],high:&[u64],k:usize,node:u32,scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,node<6,a@.len()==b@.len(),7*k<=a@.len()<=8*k,threshold>=56,
        old(even)@.len()==2*(k+1),old(odd)@.len()==old(even)@.len(),old(scratch)@.len()>=14*(k+1),
        low@.len()<=old(even)@.len(),high@.len()<=old(even)@.len(),
        value(low@)==value(a@.subrange(0,k as int))*value(b@.subrange(0,k as int)),
        value(high@)==value(a@.subrange((7*k) as int,a@.len() as int))*value(b@.subrange((7*k) as int,b@.len() as int)),
    ensures final(even)@.len()==old(even)@.len(),final(odd)@.len()==old(odd)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(even)@)==model::normalized_even(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat)),node),
        value(final(odd)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat)),node),
    decreases a.len(),3nat,

{
    let (exponent,reciprocal,_,_,_,_,_,_)=crate::toom8_normalization::parameters(node);
    toom8_recursive_dyadic_producer::dyadic_pair(even,odd,a,b,k,exponent,reciprocal,scratch,threshold);
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(b@,k as nat);
    let ghost c=convolution::coefficients(aa,bb);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(b@,k as nat);
        convolution::nonnegative_coefficients(aa,bb,radix(k as nat));
    }
    crate::toom8_normalization::normalize(even,odd,low,high,node,k,Ghost(c));
}
}

//! Actual selected dyadic weights establish the input-convolution contract.
use vstd::prelude::*;
use crate::radix::*;
use crate::toom8_convolution as convolution;
use crate::toom8_producer_spec as input;
use crate::toom8_dyadic_producer_spec as model;
verus! {
pub fn dyadic_pair(even:&mut[u64],odd:&mut[u64],a:&[u64],k:usize,exponent:u32,reciprocal:bool,scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,7*k<=a@.len()<=8*k,exponent<=3,threshold>=56,
        old(even)@.len()==2*(k+1),old(odd)@.len()==old(even)@.len(),old(scratch)@.len()>=11*(k+1),
    ensures final(even)@.len()==old(even)@.len(),final(odd)@.len()==old(odd)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(even)@)==convolution::even_value(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),model::product_weights(exponent,reciprocal)),
        value(final(odd)@)==convolution::odd_value(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),model::product_weights(exponent,reciprocal)),
    decreases a.len(),2nat,

{
    let weights=crate::toom8_evaluation::dyadic_weights(exponent,reciprocal);
    crate::toom8_square_producer::weighted_pair(even,odd,a,k,weights,scratch,threshold);
    proof {
        model::selected_weights_are_multiplicative(weights@,exponent,reciprocal);
        convolution::products_to_coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat),weights@,model::product_weights(exponent,reciprocal));
    }
}
}

//! Proof calls must disappear from a real client, leaving its control's body.
extern crate packed_model;
use vstd::prelude::*;
use packed_model::packed_convolution::*;

verus! {
#[inline(never)]
#[unsafe(no_mangle)]
pub fn packed_model_identity(x:u64) -> (out:u64)
    ensures out==x,
{
    proof {
        convolution_product(seq![x as int,3int],seq![5int,7int],17);
        slots_integer(seq![x],1,1);
    }
    x
}

#[inline(never)]
#[unsafe(no_mangle)]
pub fn ordinary_identity(x:u64) -> (out:u64)
    ensures out==x,
{
    x
}
}

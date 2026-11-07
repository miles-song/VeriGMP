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

fn main() {
    let x=std::hint::black_box(0xfedc_ba98_7654_3210u64);
    assert_eq!(packed_model_identity(x),ordinary_identity(x));
}

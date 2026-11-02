//! Six actual paired nodes establish and consume the existing Newton contract.
use vstd::prelude::*;
use crate::radix::*;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::toom8_normalization_spec as model;
use crate::{toom8_square_normalization,toom8_newton,toom8_recursive_square};
verus! {
pub fn with_endpoints(e0:&mut[u64],e1:&mut[u64],e2:&mut[u64],e3:&mut[u64],e4:&mut[u64],e5:&mut[u64],o0:&mut[u64],o1:&mut[u64],o2:&mut[u64],o3:&mut[u64],o4:&mut[u64],o5:&mut[u64],a:&[u64],low:&[u64],high:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,7*k<=a@.len()<=8*k,threshold>=56,
        old(e0)@.len()==2*(k+1),
        old(e1)@.len()==2*(k+1),
        old(e2)@.len()==2*(k+1),
        old(e3)@.len()==2*(k+1),
        old(e4)@.len()==2*(k+1),
        old(e5)@.len()==2*(k+1),
        old(o0)@.len()==2*(k+1),
        old(o1)@.len()==2*(k+1),
        old(o2)@.len()==2*(k+1),
        old(o3)@.len()==2*(k+1),
        old(o4)@.len()==2*(k+1),
        old(o5)@.len()==2*(k+1),
        old(scratch)@.len()>=11*(k+1),low@.len()<=2*(k+1),high@.len()<=2*(k+1),
        value(low@)==value(a@.subrange(0,k as int))*value(a@.subrange(0,k as int)),
        value(high@)==value(a@.subrange((7*k) as int,a@.len() as int))*value(a@.subrange((7*k) as int,a@.len() as int)),
    ensures final(scratch)@.len()==old(scratch)@.len(),
        final(e0)@.len()==old(e0)@.len(),
        final(e1)@.len()==old(e1)@.len(),
        final(e2)@.len()==old(e2)@.len(),
        final(e3)@.len()==old(e3)@.len(),
        final(e4)@.len()==old(e4)@.len(),
        final(e5)@.len()==old(e5)@.len(),
        final(o0)@.len()==old(o0)@.len(),
        final(o1)@.len()==old(o1)@.len(),
        final(o2)@.len()==old(o2)@.len(),
        final(o3)@.len()==old(o3)@.len(),
        final(o4)@.len()==old(o4)@.len(),
        final(o5)@.len()==old(o5)@.len(),
        value(final(e0)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[2],
        value(final(o0)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),0),
        value(final(e1)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[4],
        value(final(o1)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),1),
        value(final(e2)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[6],
        value(final(o2)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),2),
        value(final(e3)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[8],
        value(final(o3)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),3),
        value(final(e4)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[10],
        value(final(o4)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),4),
        value(final(e5)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat))[12],
        value(final(o5)@)==model::normalized_odd(convolution::coefficients(input::blocks(a@,k as nat),input::blocks(a@,k as nat)),5),
    decreases a.len(),4nat,

{
    toom8_square_normalization::with_endpoints(e0,o0,a,low,high,k,0,scratch,threshold);
    toom8_square_normalization::with_endpoints(e1,o1,a,low,high,k,1,scratch,threshold);
    toom8_square_normalization::with_endpoints(e2,o2,a,low,high,k,2,scratch,threshold);
    toom8_square_normalization::with_endpoints(e3,o3,a,low,high,k,3,scratch,threshold);
    toom8_square_normalization::with_endpoints(e4,o4,a,low,high,k,4,scratch,threshold);
    toom8_square_normalization::with_endpoints(e5,o5,a,low,high,k,5,scratch,threshold);
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(a@,k as nat);
    let ghost c=convolution::coefficients(aa,bb);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(a@,k as nat);
        convolution::nonnegative_coefficients(aa,bb,radix(k as nat));
        model::relations(c,0);
        reveal(crate::toom8_newton_spec::even_state_0_0);
        reveal(crate::toom8_newton_spec::even_state_0_1);
        reveal(crate::toom8_newton_spec::even_state_0_2);
        reveal(crate::toom8_newton_spec::even_state_0_3);
        reveal(crate::toom8_newton_spec::even_state_0_4);
        reveal(crate::toom8_newton_spec::even_state_0_5);

        model::newton_node_0(c);
        model::newton_node_1(c);
        model::newton_node_2(c);
        model::newton_node_3(c);
        model::newton_node_4(c);
        model::newton_node_5(c);
    }
    toom8_newton::even(e0,e1,e2,e3,e4,e5,Ghost(model::even_coefficients(c)));
}
}

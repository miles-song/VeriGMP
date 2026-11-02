//! Actual fifteen-product caller discharges all existing Newton premises.
use vstd::prelude::*;
use crate::radix::*;
use crate::toom8_producer_spec as input;
use crate::toom8_convolution as convolution;
use crate::toom8_normalization_spec as model;
use crate::{toom8_even,toom8_seventh,toom8_newton,toom4_multiply};
verus! {
// Exact required storage for coefficient slots plus shared child scratch.
pub proof fn required_storage(k:nat,h:nat)
    requires h<=k,
    ensures 26*(k+1)+2*k+2*h+14*(k+1)<=44*(k+1),
{}
#[inline(always)]
pub fn with_endpoints(e0:&mut[u64],e1:&mut[u64],e2:&mut[u64],e3:&mut[u64],e4:&mut[u64],e5:&mut[u64],o0:&mut[u64],o1:&mut[u64],o2:&mut[u64],o3:&mut[u64],o4:&mut[u64],o5:&mut[u64],o6:&mut[u64],a:&[u64],b:&[u64],low:&[u64],high:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,threshold>=24,
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
        old(o6)@.len()==2*(k+1),
        old(scratch)@.len()>=14*(k+1),
        low@.len()<=2*(k+1),high@.len()<=2*(k+1),
        value(low@)==value(a@.subrange(0,k as int))*value(b@.subrange(0,k as int)),
        value(high@)==value(a@.subrange((7*k) as int,a@.len() as int))*value(b@.subrange((7*k) as int,b@.len() as int)),
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
        final(o6)@.len()==old(o6)@.len(),
        value(final(e0)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[2],
        value(final(e1)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[4],
        value(final(e2)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[6],
        value(final(e3)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[8],
        value(final(e4)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[10],
        value(final(e5)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[12],
        value(final(o0)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[1],
        value(final(o1)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[3],
        value(final(o2)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[5],
        value(final(o3)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[7],
        value(final(o4)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[9],
        value(final(o5)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[11],
        value(final(o6)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[13],
{
    toom8_even::with_endpoints(e0,e1,e2,e3,e4,e5,o0,o1,o2,o3,o4,o5,a,b,low,high,k,scratch,threshold);
    toom8_seventh::prepare_seventh(o6,a,b,low,e0,e1,e2,e3,e4,e5,high,k,scratch,threshold);
    let ghost aa=input::blocks(a@,k as nat);let ghost bb=input::blocks(b@,k as nat);
    let ghost c=convolution::coefficients(aa,bb);
    proof {
        input::input_bounds(a@,k as nat);input::input_bounds(b@,k as nat);
        convolution::nonnegative_coefficients(aa,bb,radix(k as nat));
        model::relations(c,0);
        model::newton_node_0(c);
        model::newton_node_1(c);
        model::newton_node_2(c);
        model::newton_node_3(c);
        model::newton_node_4(c);
        model::newton_node_5(c);
        crate::toom8_seventh_spec::relations(c);
        reveal(crate::toom8_newton_spec::odd_state_0_0);
        reveal(crate::toom8_newton_spec::odd_state_0_1);
        reveal(crate::toom8_newton_spec::odd_state_0_2);
        reveal(crate::toom8_newton_spec::odd_state_0_3);
        reveal(crate::toom8_newton_spec::odd_state_0_4);
        reveal(crate::toom8_newton_spec::odd_state_0_5);
        reveal(crate::toom8_newton_spec::odd_state_0_6);
    }
    toom8_newton::odd(o0,o1,o2,o3,o4,o5,o6,Ghost(model::odd_coefficients(c)));
}
pub fn interpolate(e0:&mut[u64],e1:&mut[u64],e2:&mut[u64],e3:&mut[u64],e4:&mut[u64],e5:&mut[u64],o0:&mut[u64],o1:&mut[u64],o2:&mut[u64],o3:&mut[u64],o4:&mut[u64],o5:&mut[u64],o6:&mut[u64],low:&mut[u64],high:&mut[u64],a:&[u64],b:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,threshold>=24,
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
        old(o6)@.len()==2*(k+1),
        old(scratch)@.len()>=14*(k+1),
        old(low)@.len()==2*k,old(high)@.len()==2*(a@.len()-7*k),
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
        final(o6)@.len()==old(o6)@.len(),
        value(final(e0)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[2],
        value(final(e1)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[4],
        value(final(e2)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[6],
        value(final(e3)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[8],
        value(final(e4)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[10],
        value(final(e5)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[12],
        value(final(o0)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[1],
        value(final(o1)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[3],
        value(final(o2)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[5],
        value(final(o3)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[7],
        value(final(o4)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[9],
        value(final(o5)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[11],
        value(final(o6)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[13],
        final(low)@.len()==old(low)@.len(),final(high)@.len()==old(high)@.len(),
        value(final(low)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[0],value(final(high)@)==convolution::coefficients(input::blocks(a@,k as nat),input::blocks(b@,k as nat))[14],
{
    let _capacity=scratch.len();
    assert!(k<usize::MAX/14 && scratch.len()>=14*(k+1));
    assert!(a.len()==b.len() && a.len()>=7*k && a.len()<=8*k && threshold>=24);
    assert!(e0.len()==2*(k+1));
    assert!(e1.len()==2*(k+1));
    assert!(e2.len()==2*(k+1));
    assert!(e3.len()==2*(k+1));
    assert!(e4.len()==2*(k+1));
    assert!(e5.len()==2*(k+1));
    assert!(o0.len()==2*(k+1));
    assert!(o1.len()==2*(k+1));
    assert!(o2.len()==2*(k+1));
    assert!(o3.len()==2*(k+1));
    assert!(o4.len()==2*(k+1));
    assert!(o5.len()==2*(k+1));
    assert!(o6.len()==2*(k+1));
    let h=a.len()-7*k;
    assert!(low.len()==2*k && high.len()==2*h);
    if k>0 {toom4_multiply::full(low,&a[..k],&b[..k],scratch,threshold);}
    if h>0 {toom4_multiply::full(high,&a[7*k..],&b[7*k..],scratch,threshold);}
    with_endpoints(e0,e1,e2,e3,e4,e5,o0,o1,o2,o3,o4,o5,o6,a,b,low,high,k,scratch,threshold);
}
}

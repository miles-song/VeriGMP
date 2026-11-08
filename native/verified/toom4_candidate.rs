//! Isolated measurement policy; the production arithmetic entry points are unchanged.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::power2::*;
use crate::radix::*;
use crate::precision::*;
use crate::{fast_multiply,toom_low,square_low,toom4_low,toom4_square_low,pow2};
verus! {
pub fn mul_mod(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=12*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    if a.len()<512{fast_multiply::mul_mod(dst,a,b,scratch,top);}
    else if a.len()<2048{toom_low::modular(dst,a,b,scratch,top,192,128,2);}
    else{toom4_low::modular(dst,a,b,scratch,top,256,128,2);}
}

#[inline(always)]
fn square_small(dst:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),old(scratch)@.len()>=10*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(a@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    assert!(1<=top && top<=64);
    square_low::low(dst,a,scratch,192,64,1);
    pow2::normalize_top(dst,top);
    proof {
        modulus_properties(a@.len(),top as nat);lemma_pow2_pos((64-top) as nat);
        lemma_mod_mod(value(a@)*value(a@),modulus(a@.len(),top as nat),pow2((64-top) as nat) as int);
    }
}

#[inline(never)]
fn square_large(dst:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),old(scratch)@.len()>=10*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(a@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    assert!(1<=top && top<=64);
    toom4_square_low::low(dst,a,scratch,256,64,1);
    pow2::normalize_top(dst,top);
    proof {
        modulus_properties(a@.len(),top as nat);lemma_pow2_pos((64-top) as nat);
        lemma_mod_mod(value(a@)*value(a@),modulus(a@.len(),top as nat),pow2((64-top) as nat) as int);
    }
}

#[inline(always)]
pub fn square_mod(dst:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),old(scratch)@.len()>=10*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(a@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    if a.len()<1024{square_small(dst,a,scratch,top);}
    else{square_large(dst,a,scratch,top);}
}
}

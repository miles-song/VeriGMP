//! Fixed production policy. Inputs and caller-owned scratch retain slice contracts.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::power2::*;
use crate::radix::*;
use crate::precision::*;
use crate::{fast_multiply,toom_low,square_low,pow2};
verus! {
pub fn workspace_len(n:usize)->(out:Option<usize>)
    ensures match out {
        Some(words)=>n>0 && n<=usize::MAX/12 && words as int==12*(n as int),
        None=>n==0 || n>usize::MAX/12,
    },
{ if n==0 || n>usize::MAX/12 {None}else{Some(12*n)} }

pub fn square_workspace_len(n:usize)->(out:Option<usize>)
    ensures match out {
        Some(words)=>n>0 && n<=usize::MAX/10 && words as int==10*(n as int),
        None=>n==0 || n>usize::MAX/10,
    },
{ if n==0 || n>usize::MAX/10 {None}else{Some(10*n)} }

pub fn mul_mod(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=12*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    if a.len()<512 { fast_multiply::mul_mod(dst,a,b,scratch,top); }
    else { toom_low::modular(dst,a,b,scratch,top,192,128,2); }
}

pub fn square_mod(dst:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),old(scratch)@.len()>=10*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(a@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    assert!(1<=top && top<=64);
    if a.len()>=25 && a.len()<=64 {
        square_low::base_low_square(dst,a,scratch);
    } else {
        square_low::low(dst,a,scratch,192,64,1);
    }
    pow2::normalize_top(dst,top);
    proof {
        modulus_properties(a@.len(),top as nat);lemma_pow2_pos((64-top) as nat);
        lemma_mod_mod(value(a@)*value(a@),modulus(a@.len(),top as nat),pow2((64-top) as nat) as int);
    }
}
}

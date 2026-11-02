//! Exact top-level fifteen-product composition; recursive children remain Toom4.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::{toom8_interpolation,toom8_recomposition,toom4_multiply};
verus! {
pub proof fn workspace(n:int,k:int,m:int)
    requires n>=57,k==n/8+if n%8==0{0int}else{1int},m==k+1,
    ensures 0<k,7*k<n<=8*k,m<n,44*m<=12*n,
{
    lemma_fundamental_div_mod(n,8);
    lemma_mod_division_less_than_divisor(n,8);
}
pub fn balanced(dst:&mut[u64],a:&[u64],b:&[u64],k:usize,scratch:&mut[u64],child_threshold:usize)
    requires a@.len()==b@.len(),7*k<=a@.len()<=8*k,
        old(dst)@.len()==2*a@.len(),old(scratch)@.len()>=44*(k+1),child_threshold>=24,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(b@),
{
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,44);}
    assert!(k<usize::MAX/44 && scratch.len()>=44*(k+1));
    assert!(a.len()==b.len() && 7*k<=a.len() && a.len()<=8*k && dst.len()==2*a.len() && child_threshold>=24);
    let m=k+1;let h=a.len()-7*k;
    let (low,rest)=scratch.split_at_mut(2*k);
    let (high,rest)=rest.split_at_mut(2*h);
    let (e0,rest)=rest.split_at_mut(2*m);
    let (e1,rest)=rest.split_at_mut(2*m);
    let (e2,rest)=rest.split_at_mut(2*m);
    let (e3,rest)=rest.split_at_mut(2*m);
    let (e4,rest)=rest.split_at_mut(2*m);
    let (e5,rest)=rest.split_at_mut(2*m);
    let (o0,rest)=rest.split_at_mut(2*m);
    let (o1,rest)=rest.split_at_mut(2*m);
    let (o2,rest)=rest.split_at_mut(2*m);
    let (o3,rest)=rest.split_at_mut(2*m);
    let (o4,rest)=rest.split_at_mut(2*m);
    let (o5,rest)=rest.split_at_mut(2*m);
    let (o6,rest)=rest.split_at_mut(2*m);
    toom8_interpolation::interpolate(e0,e1,e2,e3,e4,e5,o0,o1,o2,o3,o4,o5,o6,low,high,a,b,k,rest,child_threshold);
    toom8_recomposition::assemble_exact(dst,low,o0,e0,o1,e1,o2,e2,o3,e3,o4,e4,o5,e5,o6,high,a,b,k);
}
pub fn full(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize,child_threshold:usize)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==2*a@.len(),
        old(scratch)@.len()>=12*a@.len(),threshold>=56,child_threshold>=24,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(b@),
{
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,12);}
    assert!(a.len()>0 && a.len()==b.len() && a.len()<=usize::MAX/12);
    assert!(dst.len()==2*a.len() && scratch.len()>=12*a.len() && threshold>=56 && child_threshold>=24);
    let n=a.len();
    if n<=threshold {toom4_multiply::full(dst,a,b,scratch,child_threshold);return;}
    let k=n/8+if n%8==0{0}else{1};let m=k+1;
    proof {workspace(n as int,k as int,m as int);}
    balanced(dst,a,b,k,scratch,child_threshold);
}
}

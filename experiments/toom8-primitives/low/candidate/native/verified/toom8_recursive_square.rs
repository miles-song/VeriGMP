//! Actual recursive fifteen-square full kernel with one evaluation per point.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::{toom8_square_interpolation,toom8_recomposition,toom4_square};
verus! {
pub proof fn workspace(n:int,k:int,m:int)
    requires n>=57,k==n/8+if n%8==0{0int}else{1int},m==k+1,
    ensures 0<k,7*k<n<=8*k,m<n,41*m<=10*n,
{
    lemma_fundamental_div_mod(n,8);
    lemma_mod_division_less_than_divisor(n,8);
}
#[inline(never)]
pub fn balanced(dst:&mut[u64],a:&[u64],k:usize,scratch:&mut[u64],threshold:usize)
    requires a@.len()>56,7*k<=a@.len()<=8*k,
        old(dst)@.len()==2*a@.len(),old(scratch)@.len()>=41*(k+1),threshold>=56,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(a@),
    decreases a.len(),7nat,

{
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,41);}
    assert!(k<usize::MAX/41 && scratch.len()>=41*(k+1));
    assert!(7*k<=a.len() && a.len()<=8*k && dst.len()==2*a.len() && threshold>=56);
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
    toom8_square_interpolation::interpolate(e0,e1,e2,e3,e4,e5,o0,o1,o2,o3,o4,o5,o6,low,high,a,k,rest,threshold);
    toom8_recomposition::assemble_exact(dst,low,o0,e0,o1,e1,o2,e2,o3,e3,o4,e4,o5,e5,o6,high,a,a,k);
}
pub fn full(dst:&mut[u64],a:&[u64],scratch:&mut[u64],threshold:usize)
    requires a@.len()>0,old(dst)@.len()==2*a@.len(),
        old(scratch)@.len()>=10*a@.len(),threshold>=56,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(a@),
    decreases a.len(),8nat,

{
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,10);}
    assert!(a.len()>0 && a.len()<=usize::MAX/10);
    assert!(dst.len()==2*a.len() && scratch.len()>=10*a.len() && threshold>=56);
    let n=a.len();
    if n<=threshold {toom4_square::full(dst,a,scratch,24);return;}
    let k=n/8+if n%8==0{0}else{1};let m=k+1;
    proof {workspace(n as int,k as int,m as int);}
    balanced(dst,a,k,scratch,threshold);
}
}

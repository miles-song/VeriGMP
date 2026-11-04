//! Five-product Toom-3 with reusable, caller-owned linear workspace.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{toom,toom_blocks,toom_words,toom_evaluate,toom_interpolate,fast_multiply};
verus! {
#[verifier::spinoff_prover]
#[verifier::rlimit(30)]
pub fn full(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==2*a@.len(),
        old(scratch)@.len()>=12*a@.len(),threshold>=24,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(b@),
    decreases a.len(),
{
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,12);}
    assert!(a.len()>0 && a.len()==b.len() && a.len()<=usize::MAX/12);
    assert!(dst.len()==2*a.len() && scratch.len()>=12*a.len() && threshold>=24);
    let n=a.len();
    if n<=threshold {fast_multiply::full(dst,a,b,scratch,24);return;}
    let k=n/3+if n%3==0{0}else{1};let m=k+1;
    proof {lemma_fundamental_div_mod(n as int,3);lemma_mod_division_less_than_divisor(n as int,3);}
    let (p0,rest)=scratch.split_at_mut(2*m);
    let (p4,rest)=rest.split_at_mut(2*m);
    let (p1,rest)=rest.split_at_mut(2*m);
    let (pm,rest)=rest.split_at_mut(2*m);
    let (p2,rest)=rest.split_at_mut(2*m);
    let (ax,rest)=rest.split_at_mut(m);
    let (bx,work)=rest.split_at_mut(m);
    let a0=&a[..k];let a1=&a[k..2*k];let a2=&a[2*k..];
    let b0=&b[..k];let b1=&b[k..2*k];let b2=&b[2*k..];
    full(&mut p0[..2*k],a0,b0,work,threshold);
    let ghost low_block=p0@;
    toom_words::zero(&mut p0[2*k..]);
    proof {split(p0@,(2*k) as nat);equal_prefix(p0@,low_block,(2*k) as nat);}
    let h=n-2*k;
    full(&mut p4[..2*h],a2,b2,work,threshold);
    let ghost high_block=p4@;
    // high padding omitted
    proof {split(p4@,(2*h) as nat);equal_prefix(p4@,high_block,(2*h) as nat);}
    toom_evaluate::positive(ax,a0,a1,a2,1);toom_evaluate::positive(bx,b0,b1,b2,1);
    full(p1,ax,bx,work,threshold);
    let na=toom_evaluate::negative(ax,a0,a1,a2);let nb=toom_evaluate::negative(bx,b0,b1,b2);
    let negative=na!=nb;
    let ghost av=value(ax@);let ghost bv=value(bx@);
    full(pm,ax,bx,work,threshold);
    toom_evaluate::positive(ax,a0,a1,a2,2);toom_evaluate::positive(bx,b0,b1,b2,2);
    full(p2,ax,bx,work,threshold);
    let ghost c=seq![value(a0@)*value(b0@),toom::c1(value(a0@),value(a1@),value(b0@),value(b1@)),
        toom::c2(value(a0@),value(a1@),value(a2@),value(b0@),value(b1@),value(b2@)),
        toom::c3(value(a1@),value(a2@),value(b1@),value(b2@)),value(a2@)*value(b2@)];
    proof {
        let aa0=value(a0@);let aa1=value(a1@);let aa2=value(a2@);
        let bb0=value(b0@);let bb1=value(b1@);let bb2=value(b2@);
        assert((if negative {-value(pm@)}else{value(pm@)})==toom::eval(aa0,aa1,aa2,-1)*toom::eval(bb0,bb1,bb2,-1))
            by(nonlinear_arith)
            requires value(pm@)==av*bv,negative==(na!=nb),
                (if na {-av}else{av})==aa0-aa1+aa2,(if nb {-bv}else{bv})==bb0-bb1+bb2,
                toom::eval(aa0,aa1,aa2,-1)==aa0-aa1+aa2,toom::eval(bb0,bb1,bb2,-1)==bb0-bb1+bb2;
        toom_blocks::three_blocks(a@,k as nat);toom_blocks::three_blocks(b@,k as nat);
        toom::coefficient_bounds(aa0,aa1,aa2,bb0,bb1,bb2,radix(k as nat));
        toom_blocks::product_capacity(k as nat,c);
        toom::recompose(aa0,aa1,aa2,bb0,bb1,bb2,1);
        toom::recompose(aa0,aa1,aa2,bb0,bb1,bb2,-1);
        toom::recompose(aa0,aa1,aa2,bb0,bb1,bb2,2);
        lemma_mul_basics(c[1]);lemma_mul_basics(c[2]);lemma_mul_basics(c[3]);lemma_mul_basics(aa2);
        lemma_mul_is_distributive_sub_other_way(c[1],0,1);lemma_mul_is_distributive_sub_other_way(c[3],0,1);
        lemma_mul_is_associative(16,aa2,bb2);
        assert forall|i:int| 0<=i<5 implies #[trigger] c[i]>=0 by {}
    }
    toom_interpolate::interpolate(p1,pm,p2,p0,p4,negative,&mut work[..2*m],Ghost(c));
    toom_words::zero(dst);
    toom_words::add_shifted(dst,p0,0);
    let ghost s0=dst@;
    toom_words::add_shifted(dst,p1,k);
    let ghost s1=dst@;
    toom_words::add_shifted(dst,pm,2*k);
    let ghost s2=dst@;
    toom_words::add_shifted(dst,p2,3*k);
    let ghost s3=dst@;
    toom_words::add_shifted(dst,p4,4*k);
    proof {
        let q=radix((2*n) as nat);let r=radix(k as nat);
        radix_positive((2*n) as nat);assert(radix(0)==1);
        lemma_add_mod_noop_right(radix(k as nat)*c[1],c[0],q);
        lemma_add_mod_noop_right(radix((2*k) as nat)*c[2],c[0]+r*c[1],q);
        lemma_add_mod_noop_right(radix((3*k) as nat)*c[3],c[0]+r*c[1]+radix((2*k) as nat)*c[2],q);
        lemma_add_mod_noop_right(radix((4*k) as nat)*c[4],c[0]+r*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3],q);
        radix_add(k as nat,k as nat);radix_add((2*k) as nat,k as nat);radix_add((3*k) as nat,k as nat);
        toom::recompose(value(a0@),value(a1@),value(a2@),value(b0@),value(b1@),value(b2@),r);
        lemma_mul_is_associative(r*r*r*r,value(a2@),value(b2@));
        assert(value(a@)*value(b@)==c[0]+r*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]);
        prefix_range(a@,a@.len());prefix_range(b@,b@.len());radix_add(n as nat,n as nat);
        assert(0<=value(a@)*value(b@)<q) by(nonlinear_arith)
            requires 0<=value(a@)<radix(n as nat),0<=value(b@)<radix(n as nat),q==radix(n as nat)*radix(n as nat);
        lemma_small_mod((value(a@)*value(b@)) as nat,q as nat);
    }
}
}

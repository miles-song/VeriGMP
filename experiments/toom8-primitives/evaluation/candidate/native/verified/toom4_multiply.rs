//! Forced seven-product Toom-4; default dispatch does not select this module.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{toom4,toom4_blocks,toom4_evaluate,toom4_interpolate,toom_words,toom_multiply};
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
    if n<=threshold{toom_multiply::full(dst,a,b,scratch,192);return;}
    let k=n/4+if n%4==0{0}else{1};let m=k+1;
    proof {toom4::workspace(n as int,k as int,m as int);}
    let (p0,rest)=scratch.split_at_mut(2*m);
    let (p6,rest)=rest.split_at_mut(2*m);
    let (p1,rest)=rest.split_at_mut(2*m);
    let (pm,rest)=rest.split_at_mut(2*m);
    let (p2,rest)=rest.split_at_mut(2*m);
    let (ph,rest)=rest.split_at_mut(2*m);
    let (pmh,rest)=rest.split_at_mut(2*m);
    let (ax,rest)=rest.split_at_mut(m);let (bx,work)=rest.split_at_mut(m);
    let a0=&a[..k];let a1=&a[k..2*k];let a2=&a[2*k..3*k];let a3=&a[3*k..];
    let b0=&b[..k];let b1=&b[k..2*k];let b2=&b[2*k..3*k];let b3=&b[3*k..];
    let ghost aa=seq![value(a0@),value(a1@),value(a2@),value(a3@)];
    let ghost bb=seq![value(b0@),value(b1@),value(b2@),value(b3@)];
    let ghost c=toom4::coefficients(aa,bb);
    proof {toom4::evaluation_forms(aa);toom4::evaluation_forms(bb);}
    full(&mut p0[..2*k],a0,b0,work,threshold);
    let ghost low_block=p0@;toom_words::zero(&mut p0[2*k..]);
    proof {split(p0@,(2*k) as nat);equal_prefix(p0@,low_block,(2*k) as nat);}
    let h=n-3*k;
    full(&mut p6[..2*h],a3,b3,work,threshold);
    let ghost high_block=p6@;toom_words::zero(&mut p6[2*h..]);
    proof {split(p6@,(2*h) as nat);equal_prefix(p6@,high_block,(2*h) as nat);}
    toom4_evaluate::weighted(ax,a0,a1,a2,a3,1,1,1,1);
    toom4_evaluate::weighted(bx,b0,b1,b2,b3,1,1,1,1);
    full(p1,ax,bx,work,threshold);
    let na=toom4_evaluate::signed(ax,&mut work[..m],a0,a1,a2,a3,false);
    let nb=toom4_evaluate::signed(bx,&mut work[..m],b0,b1,b2,b3,false);let negative=na!=nb;
    let ghost av=value(ax@);let ghost bv=value(bx@);
    full(pm,ax,bx,work,threshold);
    toom4_evaluate::weighted(ax,a0,a1,a2,a3,1,2,4,8);
    toom4_evaluate::weighted(bx,b0,b1,b2,b3,1,2,4,8);
    full(p2,ax,bx,work,threshold);
    toom4_evaluate::weighted(ax,a0,a1,a2,a3,8,4,2,1);
    toom4_evaluate::weighted(bx,b0,b1,b2,b3,8,4,2,1);
    full(ph,ax,bx,work,threshold);
    let nha=toom4_evaluate::signed(ax,&mut work[..m],a0,a1,a2,a3,true);
    let nhb=toom4_evaluate::signed(bx,&mut work[..m],b0,b1,b2,b3,true);let negative_half=nha!=nhb;
    let ghost ah=value(ax@);let ghost bh=value(bx@);
    full(pmh,ax,bx,work,threshold);
    proof {
        assert(aa==toom4_blocks::blocks(a@,k as nat));assert(bb==toom4_blocks::blocks(b@,k as nat));
        toom4_blocks::input_model(a@,b@,k as nat);
        toom4::evaluation_products(aa,bb);
        toom4::signed_product(av,bv,toom4::eval(aa,-1),toom4::eval(bb,-1),na,nb);
        toom4::signed_product(ah,bh,toom4::negative_half(aa),toom4::negative_half(bb),nha,nhb);
    }
    toom4_interpolate::interpolate(p1,pm,p2,ph,pmh,p0,p6,negative,negative_half,&mut work[..2*m],Ghost(c));
    toom4_interpolate::assemble(dst,p0,ph,pmh,&work[..2*m],pm,p1,p6,k,Ghost(c));
    proof {
        toom4_blocks::recover_product(dst@,a@,b@,k as nat);
    }
}
}

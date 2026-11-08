//! Forced seven-square Toom-4 with one operand evaluation per point.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{toom4,toom4_blocks,toom4_evaluate,toom4_interpolate,toom_words,toom_square};
verus! {
#[verifier::spinoff_prover]
#[verifier::rlimit(30)]
pub fn full(dst:&mut[u64],a:&[u64],scratch:&mut[u64],threshold:usize)
    requires a@.len()>0,old(dst)@.len()==2*a@.len(),
        old(scratch)@.len()>=10*a@.len(),threshold>=24,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(a@),
    decreases a.len(),
{
    let b=a;
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,10);}
    assert!(a.len()>0 && a.len()==b.len() && a.len()<=usize::MAX/10);
    assert!(dst.len()==2*a.len() && scratch.len()>=10*a.len() && threshold>=24);
    let n=a.len();
    if n<=threshold{toom_square::full(dst,a,scratch,192);return;}
    let k=n/4+if n%4==0{0}else{1};let m=k+1;
    proof {toom4::workspace(n as int,k as int,m as int);}
    let (p0,rest)=scratch.split_at_mut(2*m);
    let (p6,rest)=rest.split_at_mut(2*m);
    let (p1,rest)=rest.split_at_mut(2*m);
    let (pm,rest)=rest.split_at_mut(2*m);
    let (p2,rest)=rest.split_at_mut(2*m);
    let (ph,rest)=rest.split_at_mut(2*m);
    let (pmh,rest)=rest.split_at_mut(2*m);
    let (ax,work)=rest.split_at_mut(m);
    let a0=&a[..k];let a1=&a[k..2*k];let a2=&a[2*k..3*k];let a3=&a[3*k..];
    let b0=&b[..k];let b1=&b[k..2*k];let b2=&b[2*k..3*k];let b3=&b[3*k..];
    let ghost aa=seq![value(a0@),value(a1@),value(a2@),value(a3@)];
    let ghost bb=seq![value(b0@),value(b1@),value(b2@),value(b3@)];
    let ghost c=toom4::coefficients(aa,bb);
    proof {toom4::evaluation_forms(aa);toom4::evaluation_forms(bb);}
    full(&mut p0[..2*k],a0,work,threshold);
    let ghost low_block=p0@;toom_words::zero(&mut p0[2*k..]);
    proof {split(p0@,(2*k) as nat);equal_prefix(p0@,low_block,(2*k) as nat);}
    let h=n-3*k;
    full(&mut p6[..2*h],a3,work,threshold);
    let ghost high_block=p6@;toom_words::zero(&mut p6[2*h..]);
    proof {split(p6@,(2*h) as nat);equal_prefix(p6@,high_block,(2*h) as nat);}
    toom4_evaluate::weighted(ax,a0,a1,a2,a3,1,1,1,1);
    full(p1,ax,work,threshold);
    let na=toom4_evaluate::signed(ax,&mut work[..m],a0,a1,a2,a3,false);
    let nb=na;let negative=na!=nb;
    let ghost av=value(ax@);let ghost bv=av;
    full(pm,ax,work,threshold);
    toom4_evaluate::weighted(ax,a0,a1,a2,a3,1,2,4,8);
    full(p2,ax,work,threshold);
    toom4_evaluate::weighted(ax,a0,a1,a2,a3,8,4,2,1);
    full(ph,ax,work,threshold);
    let nha=toom4_evaluate::signed(ax,&mut work[..m],a0,a1,a2,a3,true);
    let nhb=nha;let negative_half=nha!=nhb;
    let ghost ah=value(ax@);let ghost bh=ah;
    full(pmh,ax,work,threshold);
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

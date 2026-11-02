//! In-place recovery of the three middle coefficients from five point products.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::{toom_words,fast_words};
verus! {
pub fn interpolate(p1:&mut[u64],pm:&mut[u64],p2:&mut[u64],z0:&[u64],z4:&[u64],negative:bool,
    scratch:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires c.len()==5,forall|i:int| 0<=i<5 ==> #[trigger] c[i]>=0,
        old(p1)@.len()==old(pm)@.len(),old(p1)@.len()==old(p2)@.len(),old(scratch)@.len()==old(p1)@.len(),
        z0@.len()<=old(p1)@.len(),z4@.len()<=old(p1)@.len(),
        64*(c[0]+c[1]+c[2]+c[3]+c[4])<radix(old(p1)@.len()),
        value(z0@)==c[0],value(z4@)==c[4],value(old(p1)@)==c[0]+c[1]+c[2]+c[3]+c[4],
        (if negative {-value(old(pm)@)}else{value(old(pm)@)})==c[0]-c[1]+c[2]-c[3]+c[4],
        value(old(p2)@)==c[0]+2*c[1]+4*c[2]+8*c[3]+16*c[4],
    ensures final(p1)@.len()==old(p1)@.len(),final(pm)@.len()==old(pm)@.len(),final(p2)@.len()==old(p2)@.len(),
        final(scratch)@.len()==old(scratch)@.len(),
        value(final(p1)@)==c[1],value(final(pm)@)==c[2],value(final(p2)@)==c[3],
{
    assert!(p1.len()==pm.len() && p1.len()==p2.len() && scratch.len()==p1.len());
    assert!(z0.len()<=p1.len() && z4.len()<=p1.len());
    if negative {
        let borrow=fast_words::reverse_subtract(pm,p1);
        proof {prefix_range(pm@,pm@.len());if borrow!=0{assert(borrow==1);}}
    } else {toom_words::add_exact(pm,p1);}
    assert(value(pm@)==2*(c[0]+c[2]+c[4]));
    proof {lemma_mod_multiples_basic(c[0]+c[2]+c[4],2);}
    toom_words::divide_exact(pm,2);
    toom_words::sub_exact(p1,pm);
    assert(value(p1@)==c[1]+c[3]);
    toom_words::sub_exact(pm,z0);toom_words::sub_exact(pm,z4);
    assert(value(pm@)==c[2]);
    toom_words::copy_pad(scratch,z4);toom_words::scale_exact(scratch,16);
    toom_words::sub_exact(p2,z0);toom_words::sub_exact(p2,scratch);
    assert(value(p2@)==2*(c[1]+2*c[2]+4*c[3]));
    proof {lemma_mod_multiples_basic(c[1]+2*c[2]+4*c[3],2);}
    toom_words::divide_exact(p2,2);
    toom_words::sub_exact(p2,p1);
    toom_words::copy_pad(scratch,pm);toom_words::scale_exact(scratch,2);
    toom_words::sub_exact(p2,scratch);
    assert(value(p2@)==3*c[3]);
    proof {lemma_mod_multiples_basic(c[3],3);}
    toom_words::divide_exact(p2,3);
    toom_words::sub_exact(p1,p2);
}
}

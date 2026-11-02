//! Exact seven-point interpolation using caller-owned buffers.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::{toom4,toom_words,fast_words};
verus! {
pub fn interpolate(p1:&mut[u64],pm:&mut[u64],p2:&mut[u64],ph:&mut[u64],pmh:&mut[u64],
    z0:&[u64],z6:&[u64],negative:bool,negative_half:bool,scratch:&mut[u64],Ghost(c):Ghost<Seq<int>>)
    requires c.len()==7,forall|i:int|0<=i<7 ==> 0<=#[trigger] c[i],
        old(p1)@.len()==old(pm)@.len(),old(p1)@.len()==old(p2)@.len(),
        old(p1)@.len()==old(ph)@.len(),old(p1)@.len()==old(pmh)@.len(),old(p1)@.len()==old(scratch)@.len(),
        z0@.len()<=old(p1)@.len(),z6@.len()<=old(p1)@.len(),
        128*toom4::one(c)<radix(old(p1)@.len()),
        value(z0@)==c[0],value(z6@)==c[6],value(old(p1)@)==toom4::one(c),
        (if negative{-value(old(pm)@)}else{value(old(pm)@)})==toom4::negative(c),
        value(old(p2)@)==toom4::two(c),value(old(ph)@)==toom4::scaled_half(c),
        (if negative_half{-value(old(pmh)@)}else{value(old(pmh)@)})==toom4::scaled_negative_half(c),
    ensures final(p1)@.len()==old(p1)@.len(),final(pm)@.len()==old(pm)@.len(),final(p2)@.len()==old(p2)@.len(),
        final(ph)@.len()==old(ph)@.len(),final(pmh)@.len()==old(pmh)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(ph)@)==c[1],value(final(pmh)@)==c[2],value(final(scratch)@)==c[3],
        value(final(pm)@)==c[4],value(final(p1)@)==c[5],value(final(p2)@)==3*c[3],
{
    assert!(p1.len()==pm.len() && p1.len()==p2.len() && p1.len()==ph.len());
    assert!(p1.len()==pmh.len() && p1.len()==scratch.len());
    assert!(z0.len()<=p1.len() && z6.len()<=p1.len());
    proof {toom4::interpolation(c);}
    if negative {
        let borrow=fast_words::reverse_subtract(pm,p1);
        proof {prefix_range(pm@,pm@.len());if borrow!=0{assert(borrow==1);}}
    }else{toom_words::add_exact(pm,p1);}
    assert(value(pm@)==2*(c[0]+c[2]+c[4]+c[6]));
    proof {toom4::exact_division(c[0]+c[2]+c[4]+c[6],2);}
    toom_words::divide_exact(pm,2);
    toom_words::sub_exact(p1,pm);
    assert(value(p1@)==c[1]+c[3]+c[5]);
    if negative_half {
        let borrow=fast_words::reverse_subtract(pmh,ph);
        proof {prefix_range(pmh@,pmh@.len());if borrow!=0{assert(borrow==1);}}
    }else{toom_words::add_exact(pmh,ph);}
    assert(value(pmh@)==2*(64*c[0]+16*c[2]+4*c[4]+c[6]));
    proof {toom4::exact_division(64*c[0]+16*c[2]+4*c[4]+c[6],2);}
    toom_words::divide_exact(pmh,2);
    toom_words::sub_exact(ph,pmh);
    assert(value(ph@)==2*(16*c[1]+4*c[3]+c[5]));
    proof {toom4::exact_division(16*c[1]+4*c[3]+c[5],2);}
    toom_words::divide_exact(ph,2);
    toom_words::sub_exact(pm,z0);toom_words::sub_exact(pm,z6);
    assert(value(pm@)==c[2]+c[4]);
    crate::scaled_subtraction::sub_scaled_exact(pmh,z0,64);toom_words::sub_exact(pmh,z6);
    assert(value(pmh@)==4*(4*c[2]+c[4]));
    proof {toom4::exact_division(4*c[2]+c[4],4);}
    toom_words::divide_exact(pmh,4);toom_words::sub_exact(pmh,pm);
    assert(value(pmh@)==3*c[2]);
    proof {toom4::exact_division(c[2],3);}
    toom_words::divide_exact(pmh,3);toom_words::sub_exact(pm,pmh);
    toom_words::sub_exact(p2,z0);
    crate::scaled_subtraction::sub_scaled_exact(p2,pmh,4);
    crate::scaled_subtraction::sub_scaled_exact(p2,pm,16);
    crate::scaled_subtraction::sub_scaled_exact(p2,z6,64);
    assert(value(p2@)==2*(c[1]+4*c[3]+16*c[5]));
    proof {toom4::exact_division(c[1]+4*c[3]+16*c[5],2);}
    toom_words::divide_exact(p2,2);
    toom_words::copy_pad(scratch,p1);toom_words::scale_exact(scratch,17);
    toom_words::sub_exact(scratch,ph);toom_words::sub_exact(scratch,p2);
    assert(value(scratch@)==9*c[3]);
    proof {toom4::exact_division(c[3],9);}
    toom_words::divide_exact(scratch,9);
    toom_words::sub_exact(ph,p1);
    toom_words::copy_pad(p2,scratch);toom_words::scale_exact(p2,3);toom_words::sub_exact(ph,p2);
    assert(value(ph@)==15*c[1]);
    proof {toom4::exact_division(c[1],15);}
    toom_words::divide_exact(ph,15);
    toom_words::sub_exact(p1,ph);toom_words::sub_exact(p1,scratch);
}

pub fn assemble(dst:&mut[u64],z0:&[u64],z1:&[u64],z2:&[u64],z3:&[u64],z4:&[u64],z5:&[u64],z6:&[u64],
    k:usize,Ghost(c):Ghost<Seq<int>>)
    requires c.len()==7,old(dst)@.len()>0,6*(k as int)<=old(dst)@.len(),
        value(z0@)==c[0],value(z1@)==c[1],value(z2@)==c[2],value(z3@)==c[3],
        value(z4@)==c[4],value(z5@)==c[5],value(z6@)==c[6],
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==toom4::polynomial(c,radix(k as nat))%radix(old(dst)@.len()),
{
    let _capacity=dst.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,6);}
    assert!(dst.len()>0 && k<=usize::MAX/6 && 6*k<=dst.len());
    toom_words::zero(dst);
    toom_words::add_shifted(dst,z0,0);
    toom_words::add_shifted(dst,z1,k);
    toom_words::add_shifted(dst,z2,2*k);
    toom_words::add_shifted(dst,z3,3*k);
    toom_words::add_shifted(dst,z4,4*k);
    toom_words::add_shifted(dst,z5,5*k);
    toom_words::add_shifted(dst,z6,6*k);
    proof {
        let q=radix(dst@.len());let r=radix(k as nat);
        radix_positive(dst@.len());assert(radix(0)==1);
        lemma_add_mod_noop_right(r*c[1],c[0],q);
        lemma_add_mod_noop_right(radix((2*k) as nat)*c[2],c[0]+r*c[1],q);
        lemma_add_mod_noop_right(radix((3*k) as nat)*c[3],c[0]+r*c[1]+radix((2*k) as nat)*c[2],q);
        lemma_add_mod_noop_right(radix((4*k) as nat)*c[4],c[0]+r*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3],q);
        lemma_add_mod_noop_right(radix((5*k) as nat)*c[5],c[0]+r*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4],q);
        lemma_add_mod_noop_right(radix((6*k) as nat)*c[6],c[0]+r*c[1]+radix((2*k) as nat)*c[2]+radix((3*k) as nat)*c[3]+radix((4*k) as nat)*c[4]+radix((5*k) as nat)*c[5],q);
        crate::toom4_blocks::coefficient_radices(c,k as nat);
    }
}
}

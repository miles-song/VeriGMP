//! Low square uses one cross product, contributing twice by symmetry.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{fast_multiply,toom_square,toom_low,fast_words,limbs};
verus! {
#[verifier::spinoff_prover]
#[verifier::rlimit(20)]
pub fn low(dst:&mut[u64],a:&[u64],scratch:&mut[u64],threshold:usize,low_limit:usize,split_mode:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=10*a@.len(),threshold>=24,low_limit>=24,split_mode<=2,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(a@))%radix(a@.len()),
    decreases a.len(),
{
    let b=a;
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,10);}
    assert!(a.len()>0 && a.len()==b.len());assert!(a.len()<=usize::MAX/10);
    assert!(dst.len()==a.len() && scratch.len()>=10*a.len());assert!(threshold>=24 && low_limit>=24 && split_mode<=2);
    let n=a.len();
    if n<=low_limit {
        if n<9 {fast_multiply::base_low(dst,a,b);}
        else {crate::square_base::low(dst,a);}
        return;
    }
    // Quotient-first form avoids overflowing 11*n.
    let h=if split_mode==2 {(n/40)*9+((n%40)*9)/40}else if split_mode==1 {(n/36)*11+((n%36)*11)/36}else{n/2};
    proof {
        lemma_fundamental_div_mod(n as int,40);lemma_mod_division_less_than_divisor(n as int,40);
        lemma_fundamental_div_mod(((n%40)*9) as int,40);lemma_mod_division_less_than_divisor(((n%40)*9) as int,40);
        lemma_fundamental_div_mod(n as int,36);lemma_mod_division_less_than_divisor(n as int,36);
        lemma_fundamental_div_mod(((n%36)*11) as int,36);lemma_mod_division_less_than_divisor(((n%36)*11) as int,36);
        lemma_fundamental_div_mod(n as int,2);lemma_mod_division_less_than_divisor(n as int,2);
    }
    let k=n-h;
    {
        let (product,work)=scratch.split_at_mut(2*k);
        toom_square::full(product,&a[..k],work,threshold);
        proof {prefix_mod(product@,n as nat);}
        fast_words::copy_words(dst,&product[..n]);
    }
    let ghost initial=dst@;
    let ghost z0=part(a@,0,k as nat)*part(b@,0,k as nat);
    let (temp,work)=scratch.split_at_mut(h);
    toom_low::low(temp,&a[k..],&b[..h],work,threshold,low_limit,split_mode);
    let ghost c1=value(temp@);
    let _carry=limbs::add_assign(&mut dst[k..],temp);
    let ghost middle=dst@;
    proof {congruent_suffix(initial,middle,k as nat,c1);}

    let ghost c2=value(temp@);
    let _carry=limbs::add_assign(&mut dst[k..],temp);
    proof {
        congruent_suffix(middle,dst@,k as nat,c2);
        assert(part(a@,0,h as nat)*part(a@,k as nat,a@.len())
            ==part(a@,k as nat,a@.len())*part(a@,0,h as nat)) by(nonlinear_arith);
        low_identity(a@,b@,k as nat,h as nat,z0,c1,c2);
        radix_positive(k as nat);radix_positive(h as nat);radix_add(k as nat,h as nat);
        mod_add_scaled(z0,c1,radix(k as nat),radix(h as nat));
        mod_add_scaled(z0+radix(k as nat)*c1,c2,radix(k as nat),radix(h as nat));
        assert(z0+radix(k as nat)*c1+radix(k as nat)*c2==z0+radix(k as nat)*(c1+c2)) by(nonlinear_arith);
    }
}

}

//! Karatsuba squaring: one difference evaluation and three recursive squares.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{fast_words as words,fast_multiply};
verus! {
#[verifier::rlimit(20)]
#[verifier::spinoff_prover]
pub fn full(dst:&mut[u64],a:&[u64],scratch:&mut[u64],threshold:usize)
    requires a@.len()>0,old(dst)@.len()==2*a@.len(),
        old(scratch)@.len()>=3*a@.len(),threshold>=8,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(a@),
    decreases a.len(),
{
    let b=a;
    let _scratch_len=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,3);lemma_mod_division_less_than_divisor(usize::MAX as int,3);}
    assert!(a.len()>0 && a.len()==b.len());assert!(a.len()<=usize::MAX/3);
    assert!(dst.len()==2*a.len() && scratch.len()>=3*a.len());assert!(threshold>=8);
    let n=a.len();
    if n<=threshold {fast_multiply::base_full(dst,a,a);return;}
    let h=n/2;
    let k=n-h;
    proof {lemma_fundamental_div_mod(n as int,2);lemma_mod_division_less_than_divisor(n as int,2);}
    let neg_a=words::abs_difference(&mut dst[..k],&a[..k],&a[k..]);
    let neg_b=neg_a;
    let negative=neg_a!=neg_b;
    let ghost diffs=dst@;
    let (diff_product,child_scratch)=scratch.split_at_mut(2*k);
    full(diff_product,&dst[..k],child_scratch,threshold);
    let ghost difference=value(diff_product@);
    full(&mut dst[2*k..],&a[k..],child_scratch,threshold);
    full(&mut dst[..2*k],&a[..k],child_scratch,threshold);
    let ghost products=dst@;
    proof {
        split(a@,k as nat);split(b@,k as nat);split(products,(2*k) as nat);
        radix_add(k as nat,k as nat);
        let a0=part(a@,0,k as nat);let a1=part(a@,k as nat,a@.len());
        let b0=part(b@,0,k as nat);let b1=part(b@,k as nat,b@.len());
        crate::square_spec::signed_square(a0-a1,part(diffs,0,k as nat),neg_a);
        prefix_range(a@.subrange(0,k as int),k as nat);prefix_range(b@.subrange(0,k as int),k as nat);
        prefix_range(a@.subrange(k as int,n as int),h as nat);prefix_range(b@.subrange(k as int,n as int),h as nat);
        radix_add(h as nat,(k-h) as nat);radix_positive((k-h) as nat);
        assert(radix(h as nat)<=radix(k as nat)) by(nonlinear_arith)
            requires radix(k as nat)==radix(h as nat)*radix((k-h) as nat),radix((k-h) as nat)>=1,radix(h as nat)>0;
        crate::square_spec::cross(a0,a1,difference,radix(k as nat));
        vstd::arithmetic::mul::lemma_mul_is_associative(2,radix(k as nat),radix(k as nat));
    }
    let high=words::combine_cross(diff_product,&dst[..2*k],&dst[2*k..],negative);
    let ghost cross=value(diff_product@)+radix((2*k) as nat)*(high as int);
    words::add_cross(&mut dst[k..],diff_product,high);
    proof {
        congruent_suffix(products,dst@,k as nat,cross);
        let a0=part(a@,0,k as nat);let a1=part(a@,k as nat,a@.len());
        let b0=part(b@,0,k as nat);let b1=part(b@,k as nat,b@.len());
        crate::square_spec::cross(a0,a1,difference,radix(k as nat));
        crate::square_spec::recompose(a0,a1,radix(k as nat));
        assert(value(products)+radix(k as nat)*cross==value(a@)*value(a@));
        prefix_range(a@,n as nat);prefix_range(b@,n as nat);radix_add(n as nat,n as nat);
        crate::square_spec::square_range(value(a@),radix(n as nat));
        lemma_small_mod((value(a@)*value(a@)) as nat,radix((2*n) as nat) as nat);
    }
}

}

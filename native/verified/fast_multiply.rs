//! Difference-form Karatsuba and low-product divide-and-conquer.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{fast_words as words,multiply,limbs,pow2};
use crate::precision::*;
use vstd::arithmetic::power2::*;
verus! {

pub fn workspace_len(n:usize)->(out:Option<usize>)
    ensures match out {
        Some(words)=>n>0 && n<=usize::MAX/4 && words as int==4*(n as int),
        None=>n==0 || n>usize::MAX/4,
    },
{
    if n==0 || n>usize::MAX/4 {None}else{Some(4*n)}
}

pub fn base_full(dst:&mut[u64],a:&[u64],b:&[u64])
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==2*a@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(a@)*value(b@),
{
    let _output_len=dst.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,2);}
    assert!(a.len()>0);assert!(a.len()==b.len());assert!(a.len()<=usize::MAX/2);
    assert!(dst.len()==2*a.len());
    let n=a.len();
    let carry=words::mul_word(&mut dst[..n],b,a[0]);
    let ghost first=dst@;
    dst[n]=carry;
    proof {
        equal_prefix(dst@,first,n as nat);
        split(first,n as nat);
        assert(prefix(a@,0)==0);assert(radix(0)==1);
        assert(prefix(a@,1)==a@[0] as int);
        assert(prefix(dst@,(n+1) as nat)==prefix(a@,1)*value(b@)) by(nonlinear_arith)
            requires prefix(dst@,(n+1) as nat)==prefix(first,n as nat)+(carry as int)*radix(n as nat),
                prefix(first,n as nat)+radix(n as nat)*(carry as int)==(a@[0] as int)*value(b@),
                prefix(a@,1)==a@[0] as int;
    }
    let mut i=1usize;
    while i<n
        invariant dst@.len()==2*n,a@.len()==n,b@.len()==n,1<=i<=n,n<=usize::MAX/2,
            prefix(dst@,(n+i) as nat)==prefix(a@,i as nat)*value(b@),
        decreases n-i,
    {
        let ghost before=dst@;
        let carry=multiply::add_mul_word(&mut dst[i..i+n],b,a[i]);
        let ghost middle=dst@;
        dst[i+n]=carry;
        proof {
            equal_prefix(dst@,middle,(i+n) as nat);
            segment_split(before,i as nat,(i+n) as nat);
            segment_split(middle,i as nat,(i+n) as nat);
            equal_prefix(before,middle,i as nat);radix_add(i as nat,n as nat);
            assert(prefix(middle,(i+n) as nat)+radix((i+n) as nat)*(carry as int)
                ==prefix(before,(i+n) as nat)+radix(i as nat)*(a@[i as int] as int)*value(b@))
                by(nonlinear_arith)
                requires part(middle,i as nat,(i+n) as nat)+radix(n as nat)*(carry as int)
                        ==part(before,i as nat,(i+n) as nat)+(a@[i as int] as int)*value(b@),
                    prefix(before,(i+n) as nat)==prefix(before,i as nat)+radix(i as nat)*part(before,i as nat,(i+n) as nat),
                    prefix(middle,(i+n) as nat)==prefix(before,i as nat)+radix(i as nat)*part(middle,i as nat,(i+n) as nat),
                    radix((i+n) as nat)==radix(i as nat)*radix(n as nat);
            assert(prefix(dst@,(i+n+1) as nat)==prefix(a@,(i+1) as nat)*value(b@)) by(nonlinear_arith)
                requires prefix(dst@,(i+n+1) as nat)==prefix(middle,(i+n) as nat)+(carry as int)*radix((i+n) as nat),
                    prefix(middle,(i+n) as nat)+radix((i+n) as nat)*(carry as int)
                        ==prefix(before,(i+n) as nat)+radix(i as nat)*(a@[i as int] as int)*value(b@),
                    prefix(before,(i+n) as nat)==prefix(a@,i as nat)*value(b@),
                    prefix(a@,(i+1) as nat)==prefix(a@,i as nat)+(a@[i as int] as int)*radix(i as nat);
        }
        i+=1;
    }
}

#[verifier::rlimit(20)]
#[verifier::spinoff_prover]
pub fn full(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==2*a@.len(),
        old(scratch)@.len()>=3*a@.len(),threshold>=8,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==value(a@)*value(b@),
    decreases a.len(),
{
    let _scratch_len=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,3);lemma_mod_division_less_than_divisor(usize::MAX as int,3);}
    assert!(a.len()>0 && a.len()==b.len());assert!(a.len()<=usize::MAX/3);
    assert!(dst.len()==2*a.len() && scratch.len()>=3*a.len());assert!(threshold>=8);
    let n=a.len();
    if n<=threshold {
        match n {
            15=>crate::fixed_row::full::<15>(dst,a,b),
            20=>crate::fixed_row::full::<20>(dst,a,b),
            22=>crate::fixed_row::full::<22>(dst,a,b),
            23=>crate::fixed_row::full::<23>(dst,a,b),
            _=>base_full(dst,a,b),
        }
        return;
    }
    let h=n/2;
    let k=n-h;
    proof {lemma_fundamental_div_mod(n as int,2);lemma_mod_division_less_than_divisor(n as int,2);}
    let neg_a=words::abs_difference(&mut dst[..k],&a[..k],&a[k..]);
    let neg_b=words::abs_difference(&mut dst[k..2*k],&b[..k],&b[k..]);
    let negative=neg_a!=neg_b;
    let ghost diffs=dst@;
    let (diff_product,child_scratch)=scratch.split_at_mut(2*k);
    full(diff_product,&dst[..k],&dst[k..2*k],child_scratch,threshold);
    let ghost difference=value(diff_product@);
    full(&mut dst[2*k..],&a[k..],&b[k..],child_scratch,threshold);
    full(&mut dst[..2*k],&a[..k],&b[..k],child_scratch,threshold);
    let ghost products=dst@;
    proof {
        split(a@,k as nat);split(b@,k as nat);split(products,(2*k) as nat);
        radix_add(k as nat,k as nat);
        let a0=part(a@,0,k as nat);let a1=part(a@,k as nat,a@.len());
        let b0=part(b@,0,k as nat);let b1=part(b@,k as nat,b@.len());
        assert((if negative {-difference}else{difference})==(a0-a1)*(b0-b1)) by(nonlinear_arith)
            requires difference==part(diffs,0,k as nat)*part(diffs,k as nat,(2*k) as nat),
                part(diffs,0,k as nat)==if neg_a {a1-a0}else{a0-a1},
                part(diffs,k as nat,(2*k) as nat)==if neg_b {b1-b0}else{b0-b1},
                negative==(neg_a!=neg_b);
        prefix_range(a@.subrange(0,k as int),k as nat);prefix_range(b@.subrange(0,k as int),k as nat);
        prefix_range(a@.subrange(k as int,n as int),h as nat);prefix_range(b@.subrange(k as int,n as int),h as nat);
        radix_add(h as nat,(k-h) as nat);radix_positive((k-h) as nat);
        assert(radix(h as nat)<=radix(k as nat)) by(nonlinear_arith)
            requires radix(k as nat)==radix(h as nat)*radix((k-h) as nat),radix((k-h) as nat)>=1,radix(h as nat)>0;
        assert(0<=a0*b1+a1*b0<2*radix((2*k) as nat)) by(nonlinear_arith)
            requires 0<=a0<radix(k as nat),0<=b0<radix(k as nat),0<=a1<radix(k as nat),0<=b1<radix(k as nat),
                radix((2*k) as nat)==radix(k as nat)*radix(k as nat);
        assert(a0*b0+a1*b1+(if negative {difference}else{-difference})==a0*b1+a1*b0)
            by(nonlinear_arith) requires (if negative {-difference}else{difference})==(a0-a1)*(b0-b1);
    }
    let high=words::combine_cross(diff_product,&dst[..2*k],&dst[2*k..],negative);
    let ghost cross=value(diff_product@)+radix((2*k) as nat)*(high as int);
    words::add_cross(&mut dst[k..],diff_product,high);
    proof {
        congruent_suffix(products,dst@,k as nat,cross);
        let a0=part(a@,0,k as nat);let a1=part(a@,k as nat,a@.len());
        let b0=part(b@,0,k as nat);let b1=part(b@,k as nat,b@.len());
        karatsuba_identity(a0,a1,b0,b1,radix(k as nat));
        assert(value(products)+radix(k as nat)*cross==value(a@)*value(b@)) by(nonlinear_arith)
            requires value(products)==a0*b0+radix((2*k) as nat)*(a1*b1),
                cross==a0*b0+a1*b1-(a0-a1)*(b0-b1),
                value(a@)==a0+radix(k as nat)*a1,value(b@)==b0+radix(k as nat)*b1,
                radix((2*k) as nat)==radix(k as nat)*radix(k as nat),
                (a0+radix(k as nat)*a1)*(b0+radix(k as nat)*b1)
                    ==a0*b0+radix(k as nat)*(a0*b0+a1*b1-(a0-a1)*(b0-b1))+radix(k as nat)*radix(k as nat)*a1*b1;
        prefix_range(a@,n as nat);prefix_range(b@,n as nat);radix_add(n as nat,n as nat);
        assert(0<=value(a@)*value(b@)<radix((2*n) as nat)) by(nonlinear_arith)
            requires 0<=value(a@)<radix(n as nat),0<=value(b@)<radix(n as nat),radix((2*n) as nat)==radix(n as nat)*radix(n as nat);
        lemma_small_mod((value(a@)*value(b@)) as nat,radix((2*n) as nat) as nat);
    }
}

pub fn base_low(dst:&mut[u64],a:&[u64],b:&[u64])
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==(value(a@)*value(b@))%radix(a@.len()),
{
    assert!(a.len()>0 && a.len()==b.len() && dst.len()==a.len());
    let n=a.len();
    let carry=words::mul_word(dst,b,a[0]);
    proof {
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        assert((a@[0] as int)*value(b@)==(carry as int)*radix(n as nat)+value(dst@)) by(nonlinear_arith)
            requires value(dst@)+radix(n as nat)*(carry as int)==(a@[0] as int)*value(b@);
        lemma_fundamental_div_mod_converse((a@[0] as int)*value(b@),radix(n as nat),carry as int,value(dst@));
        assert(prefix(a@,0)==0);assert(radix(0)==1);assert(prefix(a@,1)==a@[0] as int);
    }
    let mut i=1usize;
    while i<n
        invariant dst@.len()==n,a@.len()==n,b@.len()==n,1<=i<=n,radix(n as nat)>0,
            value(dst@)==(prefix(a@,i as nat)*value(b@))%radix(n as nat),
        decreases n-i,
    {
        multiply::add_mul_at(dst,b,a[i],i);
        proof {
            let prev=prefix(a@,i as nat)*value(b@);
            let term=(a@[i as int] as int)*radix(i as nat)*value(b@);
            lemma_add_mod_noop_right(term,prev,radix(n as nat));
            assert(prefix(a@,(i+1) as nat)*value(b@)==prev+term) by(nonlinear_arith)
                requires prefix(a@,(i+1) as nat)==prefix(a@,i as nat)+(a@[i as int] as int)*radix(i as nat),
                    prev==prefix(a@,i as nat)*value(b@),term==(a@[i as int] as int)*radix(i as nat)*value(b@);
        }
        i+=1;
    }
}

/// GMP's mullo construction, with a measured choice of balanced or 11/36 split.
#[verifier::spinoff_prover]
#[verifier::rlimit(20)]
pub fn low(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],threshold:usize,low_limit:usize,unbalanced:bool)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=4*a@.len(),threshold>=8,low_limit>=8,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(b@))%radix(a@.len()),
    decreases a.len(),
{
    let _capacity=scratch.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,4);}
    assert!(a.len()>0 && a.len()==b.len());assert!(a.len()<=usize::MAX/4);
    assert!(dst.len()==a.len() && scratch.len()>=4*a.len());assert!(threshold>=8 && low_limit>=8);
    let n=a.len();
    if n<=low_limit {base_low(dst,a,b);return;}
    // Quotient-first form avoids overflowing 11*n.
    let h=if unbalanced {(n/36)*11+((n%36)*11)/36}else{n/2};
    proof {
        lemma_fundamental_div_mod(n as int,36);lemma_mod_division_less_than_divisor(n as int,36);
        lemma_fundamental_div_mod(((n%36)*11) as int,36);lemma_mod_division_less_than_divisor(((n%36)*11) as int,36);
        lemma_fundamental_div_mod(n as int,2);lemma_mod_division_less_than_divisor(n as int,2);
    }
    let k=n-h;
    {
        let (product,work)=scratch.split_at_mut(2*k);
        full(product,&a[..k],&b[..k],work,threshold);
        proof {prefix_mod(product@,n as nat);}
        words::copy_words(dst,&product[..n]);
    }
    let ghost initial=dst@;
    let ghost z0=part(a@,0,k as nat)*part(b@,0,k as nat);
    let (temp,work)=scratch.split_at_mut(h);
    low(temp,&a[k..],&b[..h],work,threshold,low_limit,unbalanced);
    let ghost c1=value(temp@);
    let _carry=limbs::add_assign(&mut dst[k..],temp);
    let ghost middle=dst@;
    proof {congruent_suffix(initial,middle,k as nat,c1);}
    low(temp,&a[..h],&b[k..],work,threshold,low_limit,unbalanced);
    let ghost c2=value(temp@);
    let _carry=limbs::add_assign(&mut dst[k..],temp);
    proof {
        congruent_suffix(middle,dst@,k as nat,c2);
        low_identity(a@,b@,k as nat,h as nat,z0,c1,c2);
        radix_positive(k as nat);radix_positive(h as nat);radix_add(k as nat,h as nat);
        mod_add_scaled(z0,c1,radix(k as nat),radix(h as nat));
        mod_add_scaled(z0+radix(k as nat)*c1,c2,radix(k as nat),radix(h as nat));
        assert(z0+radix(k as nat)*c1+radix(k as nat)*c2==z0+radix(k as nat)*(c1+c2)) by(nonlinear_arith);
    }
}

pub fn modular(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,threshold:usize,low_limit:usize,unbalanced:bool)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=4*a@.len(),threshold>=8,low_limit>=8,1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    assert!(1<=top && top<=64);
    low(dst,a,b,scratch,threshold,low_limit,unbalanced);
    pow2::normalize_top(dst,top);
    proof {
        modulus_properties(a@.len(),top as nat);lemma_pow2_pos((64-top) as nat);
        lemma_mod_mod(value(a@)*value(b@),modulus(a@.len(),top as nat),pow2((64-top) as nat) as int);
    }
}

/// Default policy is fixed, never an instance-dependent complexity escape.
pub fn mul_mod(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=4*a@.len(),1<=top<=64,
    ensures final(dst)@.len()==old(dst)@.len(),final(scratch)@.len()==old(scratch)@.len(),
        value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
        0<=value(final(dst)@)<modulus(a@.len(),top as nat),
{
    modular(dst,a,b,scratch,top,24,64,true);
}
} // verus!

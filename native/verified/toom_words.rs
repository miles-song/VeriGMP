//! Exact interpolation primitives, operating in place on caller-owned words.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{fast_words,multiply};
verus! {

pub fn zero(dst:&mut[u64])
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==0,
{
    let mut i=0usize;
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()==old(dst)@.len(),prefix(dst@,i as nat)==0,
        decreases dst.len()-i,
    {
        let ghost before=dst@;dst[i]=0;
        proof {equal_prefix(dst@,before,i as nat);}
        i+=1;
    }
}

pub fn copy_pad(dst:&mut[u64],src:&[u64])
    requires old(dst)@.len()>=src@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(src@),
{
    assert!(dst.len()>=src.len());
    let original = dst@;
    let copied = src.len();
    fast_words::copy_words(&mut dst[..copied], src);
    zero(&mut dst[copied..]);
    proof {
        assert(dst@.len() == original.len());
        assert(dst@.subrange(0, copied as int) =~= src@);
        assert(dst@.subrange(copied as int, dst@.len() as int) =~= Seq::new(
            (dst@.len() - copied) as int, |_i: int| 0u64,
        ));
        assert(value(dst@.subrange(copied as int, dst@.len() as int)) == 0);
        crate::product::subrange_value(dst@, 0, copied as nat);
        crate::product::subrange_value(dst@, copied as nat, (dst@.len() - copied) as nat);
        assert(prefix(dst@, copied as nat) == value(src@));
        assert(value(dst@) == prefix(dst@, copied as nat)
            + radix(copied as nat) * value(dst@.subrange(copied as int, dst@.len() as int)));
        assert(value(dst@) == value(src@));
    }
}

pub fn subtract_assign(dst:&mut[u64],rhs:&[u64])->(out:u64)
    requires old(dst)@.len()>=rhs@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),out<=1,
        value(final(dst)@)-radix(old(dst)@.len())*(out as int)==value(old(dst)@)-value(rhs@),
{
    assert!(dst.len()>=rhs.len());
    let ghost original=dst@;let mut i=0usize;let mut borrow=0u64;
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()==original.len(),dst@.len()>=rhs@.len(),borrow<=1,
            forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            prefix(dst@,i as nat)-radix(i as nat)*(borrow as int)==prefix(original,i as nat)-extended(rhs@,i as nat),
        decreases dst.len()-i,
    {
        let y=if i<rhs.len(){rhs[i]}else{0};let x=dst[i];
        let ghost before=dst@;let ghost incoming=borrow;
        let (low,next)=fast_words::sub_word(x,y,borrow);dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);extended_step(rhs@,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)
                ==prefix(original,(i+1) as nat)-extended(rhs@,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)==prefix(original,i as nat)-extended(rhs@,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(x as int)*radix(i as nat),
                    extended(rhs@,(i+1) as nat)==extended(rhs@,i as nat)+(y as int)*radix(i as nat),
                    (low as int)-base()*(next as int)==(x as int)-(y as int)-(incoming as int),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        borrow=next;i+=1;
    }
    borrow
}

pub fn scale(dst:&mut[u64],word:u64)->(out:u64)
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)+radix(old(dst)@.len())*(out as int)==(word as int)*value(old(dst)@),
{
    let ghost original=dst@;let mut i=0usize;let mut carry=0u64;
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()==original.len(),
            forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)==(word as int)*prefix(original,i as nat),
        decreases dst.len()-i,
    {
        let x=dst[i];let ghost before=dst@;let ghost incoming=carry;
        let (low,next)=multiply::mac(word,x,0,carry);dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)
                ==(word as int)*prefix(original,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)+radix(i as nat)*(incoming as int)==(word as int)*prefix(original,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(x as int)*radix(i as nat),
                    (low as int)+base()*(next as int)==(word as int)*(x as int)+(incoming as int),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        carry=next;i+=1;
    }
    carry
}

pub fn reverse_subtract_extended(dst:&mut[u64],rhs:&[u64])->(out:u64)
    requires old(dst)@.len()>=rhs@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),out<=1,
        value(final(dst)@)-radix(old(dst)@.len())*(out as int)==value(rhs@)-value(old(dst)@),
{
    assert!(dst.len()>=rhs.len());
    let ghost original=dst@;let mut i=0usize;let mut borrow=0u64;
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()==original.len(),dst@.len()>=rhs@.len(),borrow<=1,
            forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            prefix(dst@,i as nat)-radix(i as nat)*(borrow as int)==extended(rhs@,i as nat)-prefix(original,i as nat),
        decreases dst.len()-i,
    {
        let x=if i<rhs.len(){rhs[i]}else{0};let y=dst[i];
        let ghost before=dst@;let ghost incoming=borrow;
        let (low,next)=fast_words::sub_word(x,y,borrow);dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);extended_step(rhs@,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)
                ==extended(rhs@,(i+1) as nat)-prefix(original,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)==extended(rhs@,i as nat)-prefix(original,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(y as int)*radix(i as nat),
                    extended(rhs@,(i+1) as nat)==extended(rhs@,i as nat)+(x as int)*radix(i as nat),
                    (low as int)-base()*(next as int)==(x as int)-(y as int)-(incoming as int),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        borrow=next;i+=1;
    }
    borrow
}

/// Exact quotient/remainder; constant divisors are specialized at each call site.
#[inline(always)]
pub fn divide_word(dst:&mut[u64],divisor:u64)->(remainder:u64)
    requires divisor>0,
    ensures final(dst)@.len()==old(dst)@.len(),remainder<divisor,
        value(old(dst)@)==(divisor as int)*value(final(dst)@)+(remainder as int),
{
    assert!(divisor>0);
    let ghost original=dst@;let mut i=dst.len();let mut rem=0u64;
    proof {assert(value(dst@)-prefix(dst@,i as nat)==0);}
    while i>0
        invariant i<=dst@.len(),dst@.len()==original.len(),divisor>0,rem<divisor,
            forall|j:int| 0<=j<i ==> #[trigger] dst@[j]==original[j],
            value(original)==(divisor as int)*(value(dst@)-prefix(dst@,i as nat))
                +(rem as int)*radix(i as nat)+prefix(original,i as nat),
        decreases i,
    {
        let ghost before=dst@;let ghost previous=i;let ghost incoming=rem;
        i-=1;
        let x=dst[i];
        let total=(rem as u128)*18446744073709551616u128+(x as u128);
        let q=total/(divisor as u128);let r=total%(divisor as u128);
        proof {
            lemma_fundamental_div_mod(total as int,divisor as int);
            lemma_mod_division_less_than_divisor(total as int,divisor as int);
            assert(q<18446744073709551616u128) by(nonlinear_arith)
                requires total==(incoming as int)*base()+(x as int),incoming<divisor,x<=u64::MAX,
                    total==(divisor as int)*(q as int)+(r as int),r>=0,divisor>0;
        }
        dst[i]=q as u64;rem=r as u64;
        proof {
            equal_prefix(dst@,before,i as nat);prefix_frame(before,dst@,previous as nat);
            assert(value(original)==(divisor as int)*(value(dst@)-prefix(dst@,i as nat))
                +(rem as int)*radix(i as nat)+prefix(original,i as nat)) by(nonlinear_arith)
                requires value(original)==(divisor as int)*(value(before)-prefix(before,previous as nat))
                        +(incoming as int)*radix(previous as nat)+prefix(original,previous as nat),
                    value(dst@)-value(before)==prefix(dst@,previous as nat)-prefix(before,previous as nat),
                    prefix(dst@,previous as nat)==prefix(before,i as nat)+(q as int)*radix(i as nat),
                    prefix(original,previous as nat)==prefix(original,i as nat)+(x as int)*radix(i as nat),
                    prefix(dst@,i as nat)==prefix(before,i as nat),
                    radix(previous as nat)==base()*radix(i as nat),
                    (incoming as int)*base()+(x as int)==(divisor as int)*(q as int)+(rem as int);
        }
    }
    rem
}

pub fn add_exact(dst:&mut[u64],rhs:&[u64])
    requires old(dst)@.len()>=rhs@.len(),value(old(dst)@)+value(rhs@)<radix(old(dst)@.len()),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(old(dst)@)+value(rhs@),
{
    let ghost original=dst@;
    let carry=fast_words::add_extended(dst,rhs);
    proof {
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        assert(carry==0) by(nonlinear_arith)
            requires value(dst@)+radix(dst@.len())*(carry as int)==value(original)+value(rhs@),
                value(original)+value(rhs@)<radix(dst@.len()),0<=value(dst@),carry>=0,radix(dst@.len())>0;
    }
}

pub fn sub_exact(dst:&mut[u64],rhs:&[u64])
    requires old(dst)@.len()>=rhs@.len(),value(old(dst)@)>=value(rhs@),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(old(dst)@)-value(rhs@),
{
    let borrow=subtract_assign(dst,rhs);
    proof {
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        if borrow!=0 {assert(borrow==1);}
    }
}

pub fn scale_exact(dst:&mut[u64],word:u64)
    requires (word as int)*value(old(dst)@)<radix(old(dst)@.len()),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==(word as int)*value(old(dst)@),
{
    let ghost original=dst@;
    let carry=scale(dst,word);
    proof {
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        assert(carry==0) by(nonlinear_arith)
            requires value(dst@)+radix(dst@.len())*(carry as int)==(word as int)*value(original),
                (word as int)*value(original)<radix(dst@.len()),0<=value(dst@),carry>=0,radix(dst@.len())>0;
    }
}

#[inline(always)]
pub fn divide_exact(dst:&mut[u64],divisor:u64)
    requires divisor>0,value(old(dst)@)%(divisor as int)==0,
    ensures final(dst)@.len()==old(dst)@.len(),value(old(dst)@)==(divisor as int)*value(final(dst)@),
{
    let rem=divide_word(dst,divisor);
    proof {
        lemma_fundamental_div_mod_converse(value(old(dst)@),divisor as int,value(dst@),rem as int);
    }
}

pub fn add_shifted(dst:&mut[u64],rhs:&[u64],offset:usize)
    requires offset<=old(dst)@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==(value(old(dst)@)+radix(offset as nat)*value(rhs@))%radix(old(dst)@.len()),
{
    assert!(offset<=dst.len());let length=dst.len()-offset;
    let ghost original=dst@;
    if length>=rhs.len() {
        let carry=fast_words::add_extended(&mut dst[offset..],rhs);
        proof {
            prefix_range(dst@.subrange(offset as int,dst@.len() as int),length as nat);radix_positive(length as nat);
            assert(value(original.subrange(offset as int,original.len() as int))+value(rhs@)
                ==(carry as int)*radix(length as nat)+value(dst@.subrange(offset as int,dst@.len() as int))) by(nonlinear_arith)
                requires value(dst@.subrange(offset as int,dst@.len() as int))+radix(length as nat)*(carry as int)
                    ==value(original.subrange(offset as int,original.len() as int))+value(rhs@);
            lemma_fundamental_div_mod_converse(value(original.subrange(offset as int,original.len() as int))+value(rhs@),
                radix(length as nat),carry as int,value(dst@.subrange(offset as int,dst@.len() as int)));
            congruent_suffix(original,dst@,offset as nat,value(rhs@));
        }
    } else {
        let carry=fast_words::add_extended(&mut dst[offset..],&rhs[..length]);
        proof {
            let delta=prefix(rhs@,length as nat);
            equal_prefix(rhs@,rhs@.subrange(0,length as int),length as nat);
            prefix_range(dst@.subrange(offset as int,dst@.len() as int),length as nat);radix_positive(length as nat);
            lemma_fundamental_div_mod_converse(value(original.subrange(offset as int,original.len() as int))+delta,
                radix(length as nat),carry as int,value(dst@.subrange(offset as int,dst@.len() as int)));
            congruent_suffix(original,dst@,offset as nat,delta);
            split_value(rhs@,length as nat);radix_add(offset as nat,length as nat);radix_positive(dst@.len());
            assert(value(original)+radix(offset as nat)*value(rhs@)
                ==value(original)+radix(offset as nat)*delta+radix(dst@.len())*tail(rhs@,length as nat)) by(nonlinear_arith)
                requires value(rhs@)==delta+radix(length as nat)*tail(rhs@,length as nat),
                    radix(dst@.len())==radix(offset as nat)*radix(length as nat);
            assert(radix(dst@.len())>0) by {radix_positive(dst@.len());}
            lemma_mod_multiples_vanish(tail(rhs@,length as nat),value(original)+radix(offset as nat)*delta,radix(dst@.len()));
        }
    }
}
}

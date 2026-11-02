//! Generic odd exact division: every positive u64 divisor with a radix inverse.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::wide_odd_division_spec::*;
verus! {
#[inline(always)]
pub fn quotient_limb(x:u64,carry:u64,divisor:u64,inv:u64)->(out:(u64,u64))
    requires inverse_valid(divisor as int,inv as int),carry<divisor,
    ensures out.1<divisor,
        (divisor as int)*(out.0 as int)+(carry as int)==(x as int)+base()*(out.1 as int),
{
    let difference=x.wrapping_sub(carry);
    let q=difference.wrapping_mul(inv);
    proof {
        inverse_identity(divisor as int,inv as int);
        assert((divisor as int)*(q as int)+(carry as int)<base()*base()) by(nonlinear_arith)
            requires 0<divisor<=u64::MAX,q<=u64::MAX,carry<divisor;
    }
    let wide=(divisor as u128)*(q as u128)+(carry as u128);
    let next=(wide/18446744073709551616u128) as u64;
    proof {
        let borrow=if x<carry {1int}else{0int};
        let product=(difference as int)*(inv as int);
        let quotient=product/base();
        assert(difference as int==(x as int)-(carry as int)+base()*borrow);
        assert(q as int==product%base());
        lemma_fundamental_div_mod(product,base());
        let multiple=borrow+(difference as int)*factor(divisor as int,inv as int)-(divisor as int)*quotient;
        assert(wide as int==(x as int)+base()*multiple) by(nonlinear_arith)
            requires multiple==borrow+(difference as int)*factor(divisor as int,inv as int)-(divisor as int)*quotient,
                wide as int==(divisor as int)*(q as int)+(carry as int),
                product==(difference as int)*(inv as int),product==base()*quotient+(q as int),
                (divisor as int)*(inv as int)==1+base()*factor(divisor as int,inv as int),
                difference as int==(x as int)-(carry as int)+base()*borrow;
        lemma_mod_multiples_vanish(multiple,x as int,base());
        lemma_fundamental_div_mod(wide as int,base());
        assert((wide as int)<(divisor as int)*base()) by(nonlinear_arith)
            requires wide as int==(divisor as int)*(q as int)+(carry as int),q<=u64::MAX,carry<divisor;
        assert(next<divisor) by(nonlinear_arith)
            requires (wide as int)<(divisor as int)*base(),wide as int==base()*(next as int)+(x as int),x>=0;
    }
    (q,next)
}

#[inline(always)]
pub fn divide_exact_with_inverse(dst:&mut[u64],divisor:u64,inv:u64)
    requires inverse_valid(divisor as int,inv as int),value(old(dst)@)%(divisor as int)==0,
    ensures final(dst)@.len()==old(dst)@.len(),value(old(dst)@)==(divisor as int)*value(final(dst)@),
{
    assert!(divisor>0);
    let ghost original=dst@;
    let mut carry=0u64;let mut i=0usize;
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()==original.len(),inverse_valid(divisor as int,inv as int),carry<divisor,
            value(original)%(divisor as int)==0,
            forall|j:int|i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            (divisor as int)*prefix(dst@,i as nat)==prefix(original,i as nat)+radix(i as nat)*(carry as int),
        decreases dst.len()-i,
    {
        let ghost before=dst@;let ghost incoming=carry;
        let x=dst[i];let (q,next)=quotient_limb(x,carry,divisor,inv);dst[i]=q;
        proof {
            equal_prefix(dst@,before,i as nat);
            assert((divisor as int)*prefix(dst@,(i+1) as nat)
                ==prefix(original,(i+1) as nat)+radix((i+1) as nat)*(next as int)) by(nonlinear_arith)
                requires (divisor as int)*prefix(before,i as nat)==prefix(original,i as nat)+radix(i as nat)*(incoming as int),
                    (divisor as int)*(q as int)+(incoming as int)==(x as int)+base()*(next as int),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(q as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(x as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        carry=next;i+=1;
    }
    proof {
        lemma_fundamental_div_mod(value(original),divisor as int);
        let q=value(dst@)-value(original)/(divisor as int);
        assert(radix(dst@.len())*(carry as int)==(divisor as int)*q) by(nonlinear_arith)
            requires q==value(dst@)-value(original)/(divisor as int),
                (divisor as int)*value(dst@)==value(original)+radix(dst@.len())*(carry as int),
                value(original)==(divisor as int)*(value(original)/(divisor as int));
        lemma_mod_multiples_basic(q,divisor as int);
        cancel_radix(dst@.len(),carry as int,divisor as int,inv as int);
        assert(carry==0);
    }
}
}

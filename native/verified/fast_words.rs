//! Word/slice primitives used by the difference-form Karatsuba implementation.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{kernel,limbs,multiply};
pub use crate::kernel::sub_limb as sub_word;
verus! {

pub fn copy_words(dst:&mut[u64],src:&[u64])
    requires old(dst)@.len()==src@.len(),
    ensures final(dst)@==src@,
{
    assert!(dst.len()==src.len());
    let mut i=0usize;
    while i<dst.len()
        invariant dst@.len()==src@.len(), i<=dst@.len(),
            forall|j:int| 0<=j<i ==> #[trigger] dst@[j]==src@[j],
        decreases dst.len()-i,
    { dst[i]=src[i]; i+=1; }
    assert(dst@ =~= src@);
}

/// Numeric comparison with implicit high zero words; no padded allocation.
pub fn less(a:&[u64],b:&[u64])->(out:bool)
    requires a@.len()>=b@.len(),
    ensures out==(value(a@)<value(b@)),
{
    assert!(a.len()>=b.len());
    let mut i=a.len();
    while i>0
        invariant i<=a@.len(), a@.len()>=b@.len(),
            value(a@)-value(b@)==prefix(a@,i as nat)-extended(b@,i as nat),
        decreases i,
    {
        let ghost previous=i;
        i-=1;
        let y=if i<b.len() { b[i] } else { 0 };
        proof { extended_step(b@,i as nat); prefix_range(a@,i as nat);
            if i<b.len() { prefix_range(b@,i as nat); }
            else { prefix_range(b@,b@.len()); radix_positive(i as nat); }
        }
        if a[i]!=y {
            proof {
                assert(value(a@)-value(b@)==prefix(a@,i as nat)-extended(b@,i as nat)
                    +((a@[i as int] as int)-(y as int))*radix(i as nat)) by(nonlinear_arith)
                    requires value(a@)-value(b@)==prefix(a@,previous as nat)-extended(b@,previous as nat),
                        prefix(a@,previous as nat)==prefix(a@,i as nat)+(a@[i as int] as int)*radix(i as nat),
                        extended(b@,previous as nat)==extended(b@,i as nat)+(y as int)*radix(i as nat);
                // Only a shorter operand's missing top digit can reach this branch.
                if i>=b.len() {
                    radix_add(b@.len(),(i-b@.len()) as nat);
                    radix_positive((i-b@.len()) as nat);
                    assert(radix(b@.len())<=radix(i as nat)) by(nonlinear_arith)
                        requires radix(i as nat)==radix(b@.len())*radix((i-b@.len()) as nat),
                            radix((i-b@.len()) as nat)>=1, radix(b@.len())>0;
                }
                assert((value(a@)<value(b@))==(a@[i as int]<y)) by(nonlinear_arith)
                    requires value(a@)-value(b@)==prefix(a@,i as nat)-extended(b@,i as nat)
                            +((a@[i as int] as int)-(y as int))*radix(i as nat),
                        0<=prefix(a@,i as nat)<radix(i as nat),
                        0<=extended(b@,i as nat)<radix(i as nat), a@[i as int]!=y;
            }
            return a[i]<y;
        }
    }
    false
}

/// Both source lengths may be shorter than dst, representing implicit high zeros.
#[inline(always)]
pub fn subtract(dst:&mut[u64],a:&[u64],b:&[u64])->(borrow_out:u64)
    requires old(dst)@.len()>=a@.len(),old(dst)@.len()>=b@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),borrow_out<=1,
        value(final(dst)@)-radix(old(dst)@.len())*(borrow_out as int)==value(a@)-value(b@),
{
    assert!(dst.len()>=a.len() && dst.len()>=b.len());
    let mut i=0usize;
    let mut borrow=0u64;
    let common=if a.len()<b.len(){a.len()}else{b.len()};
    while i<common
        invariant i<=common,common<=a@.len(),common<=b@.len(),common<=dst@.len(),dst@.len()>=a@.len(),dst@.len()>=b@.len(),
            dst@.len()==old(dst)@.len(), borrow<=1,
            prefix(dst@,i as nat)-radix(i as nat)*(borrow as int)==extended(a@,i as nat)-extended(b@,i as nat),
        decreases common-i,
    {
        let x=a[i];
        let y=b[i];
        let ghost before=dst@;
        let ghost incoming=borrow;
        let (low,next)=sub_word(x,y,borrow);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat); extended_step(a@,i as nat); extended_step(b@,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)
                ==extended(a@,(i+1) as nat)-extended(b@,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)==extended(a@,i as nat)-extended(b@,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    (low as int)-base()*(next as int)==(x as int)-(y as int)-(incoming as int),
                    extended(a@,(i+1) as nat)==extended(a@,i as nat)+(x as int)*radix(i as nat),
                    extended(b@,(i+1) as nat)==extended(b@,i as nat)+(y as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        borrow=next; i+=1;
    }
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()>=a@.len(),dst@.len()>=b@.len(),
            dst@.len()==old(dst)@.len(), borrow<=1,
            prefix(dst@,i as nat)-radix(i as nat)*(borrow as int)==extended(a@,i as nat)-extended(b@,i as nat),
        decreases dst.len()-i,
    {
        let x=if i<a.len(){a[i]}else{0};
        let y=if i<b.len(){b[i]}else{0};
        let ghost before=dst@;
        let ghost incoming=borrow;
        let (low,next)=sub_word(x,y,borrow);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat); extended_step(a@,i as nat); extended_step(b@,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)
                ==extended(a@,(i+1) as nat)-extended(b@,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)==extended(a@,i as nat)-extended(b@,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    (low as int)-base()*(next as int)==(x as int)-(y as int)-(incoming as int),
                    extended(a@,(i+1) as nat)==extended(a@,i as nat)+(x as int)*radix(i as nat),
                    extended(b@,(i+1) as nat)==extended(b@,i as nat)+(y as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        borrow=next; i+=1;
    }
    borrow
}

pub fn abs_difference(dst:&mut[u64],a:&[u64],b:&[u64])->(negative:bool)
    requires old(dst)@.len()==a@.len(), a@.len()>=b@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),
        negative==(value(a@)<value(b@)),
        value(final(dst)@)==if negative {value(b@)-value(a@)} else {value(a@)-value(b@)},
{
    assert!(dst.len()==a.len()); assert!(a.len()>=b.len());
    let neg=less(a,b);
    let borrow=if neg {subtract(dst,b,a)} else {subtract(dst,a,b)};
    proof {
        prefix_range(dst@,dst@.len());
        assert(borrow==0) by(nonlinear_arith)
            requires 0<=value(dst@)<radix(dst@.len()),borrow<=1,
                value(dst@)-radix(dst@.len())*(borrow as int)
                    == if neg {value(b@)-value(a@)} else {value(a@)-value(b@)},
                neg==(value(a@)<value(b@));
        assert(value(dst@)==if neg {value(b@)-value(a@)} else {value(a@)-value(b@)})
            by(nonlinear_arith)
            requires borrow==0,
                value(dst@)-radix(dst@.len())*(borrow as int)
                    ==if neg {value(b@)-value(a@)} else {value(a@)-value(b@)};
    }
    neg
}

/// Propagate a single word, stopping as soon as there is no carry.
pub fn add_small(dst:&mut[u64],small:u64)->(carry_out:u64)
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)+radix(old(dst)@.len())*(carry_out as int)==value(old(dst)@)+(small as int),
        old(dst)@.len()>0 ==> carry_out<=1,
        old(dst)@.len()==0 ==> carry_out==small,
{
    let ghost original=dst@;
    let mut i=0usize;
    let mut carry=small;
    while i<dst.len() && carry!=0
        invariant dst@.len()==original.len(),i<=dst@.len(),i>0 ==> carry<=1,
            forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)==prefix(original,i as nat)+(small as int),
        decreases dst.len()-i,
    {
        let ghost before=dst@;
        let ghost incoming=carry;
        let (low,next)=kernel::add_limb(dst[i],carry,0);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)==prefix(original,(i+1) as nat)+(small as int))
                by(nonlinear_arith)
                requires prefix(before,i as nat)+radix(i as nat)*(incoming as int)==prefix(original,i as nat)+(small as int),
                    before[i as int]==original[i as int],
                    (low as int)+base()*(next as int)==(before[i as int] as int)+(incoming as int),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(original[i as int] as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        carry=next;i+=1;
    }
    proof { if i<dst.len() {prefix_frame(original,dst@,i as nat);} }
    carry
}

pub fn add_extended(dst:&mut[u64],rhs:&[u64])->(carry_out:u64)
    requires old(dst)@.len()>=rhs@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),carry_out<=1,
        value(final(dst)@)+radix(old(dst)@.len())*(carry_out as int)==value(old(dst)@)+value(rhs@),
{
    assert!(dst.len()>=rhs.len());
    let ghost before=dst@;
    let k=rhs.len();
    let carry=limbs::add_assign(&mut dst[..k],rhs);
    let ghost mid=dst@;
    let out=add_small(&mut dst[k..],carry);
    proof {
        split(before,k as nat);split(mid,k as nat);split(dst@,k as nat);
        radix_add(k as nat,(dst@.len()-k) as nat);
        assert(value(dst@)+radix(dst@.len())*(out as int)==value(before)+value(rhs@)) by(nonlinear_arith)
            requires part(mid,0,k as nat)+radix(k as nat)*(carry as int)==part(before,0,k as nat)+value(rhs@),
                part(dst@,k as nat,dst@.len())+radix((dst@.len()-k) as nat)*(out as int)==part(mid,k as nat,mid.len())+(carry as int),
                value(dst@)==part(mid,0,k as nat)+radix(k as nat)*part(dst@,k as nat,dst@.len()),
                value(before)==part(before,0,k as nat)+radix(k as nat)*part(mid,k as nat,mid.len()),
                radix(dst@.len())==radix(k as nat)*radix((dst@.len()-k) as nat);
    }
    out
}

/// rhs - old(dst), kept modulo the slice radix with an explicit borrow.
pub fn reverse_subtract(dst:&mut[u64],rhs:&[u64])->(borrow_out:u64)
    requires old(dst)@.len()==rhs@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),borrow_out<=1,
        value(final(dst)@)-radix(old(dst)@.len())*(borrow_out as int)==value(rhs@)-value(old(dst)@),
{
    assert!(dst.len()==rhs.len());
    let ghost original=dst@;
    let mut i=0usize;let mut borrow=0u64;
    while i<dst.len()
        invariant dst@.len()==original.len(),dst@.len()==rhs@.len(),i<=dst@.len(),borrow<=1,
            forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            prefix(dst@,i as nat)-radix(i as nat)*(borrow as int)==prefix(rhs@,i as nat)-prefix(original,i as nat),
        decreases dst.len()-i,
    {
        let ghost before=dst@;let ghost incoming=borrow;
        let (low,next)=sub_word(rhs[i],dst[i],borrow);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)==prefix(rhs@,(i+1) as nat)-prefix(original,(i+1) as nat))
                by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)==prefix(rhs@,i as nat)-prefix(original,i as nat),
                    before[i as int]==original[i as int],
                    (low as int)-base()*(next as int)==(rhs@[i as int] as int)-(before[i as int] as int)-(incoming as int),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(rhs@,(i+1) as nat)==prefix(rhs@,i as nat)+(rhs@[i as int] as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(original[i as int] as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        borrow=next;i+=1;
    }
    borrow
}

/// First product row overwrites the destination, avoiding a separate zero pass.
pub fn mul_word(dst:&mut[u64],rhs:&[u64],word:u64)->(carry_out:u64)
    requires old(dst)@.len()==rhs@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)+radix(rhs@.len())*(carry_out as int)==(word as int)*value(rhs@),
{
    assert!(dst.len()==rhs.len());
    let mut i=0usize;let mut carry=0u64;
    while i<dst.len()
        invariant dst@.len()==rhs@.len(),i<=dst@.len(),
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)==(word as int)*prefix(rhs@,i as nat),
        decreases dst.len()-i,
    {
        let ghost before=dst@;let ghost incoming=carry;
        let (low,next)=multiply::mac(word,rhs[i],0,carry);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)==(word as int)*prefix(rhs@,(i+1) as nat))
                by(nonlinear_arith)
                requires prefix(before,i as nat)+radix(i as nat)*(incoming as int)==(word as int)*prefix(rhs@,i as nat),
                    (low as int)+base()*(next as int)==(word as int)*(rhs@[i as int] as int)+(incoming as int),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(rhs@,(i+1) as nat)==prefix(rhs@,i as nat)+(rhs@[i as int] as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        carry=next;i+=1;
    }
    carry
}

#[inline(always)]
fn cross_limb(a:u64,b:u64,c:u64,carry:u64)->(out:(u64,u64))
    requires carry<=2,
    ensures out.1<=2,
        (out.0 as int)+base()*(out.1 as int)==(a as int)+(b as int)+(c as int)+(carry as int),
{
    let total=(a as u128)+(b as u128)+(c as u128)+(carry as u128);
    let radix=18446744073709551616u128;
    let low=(total%radix) as u64;
    let next=(total/radix) as u64;
    proof {
        lemma_fundamental_div_mod(total as int,base());
        lemma_mod_division_less_than_divisor(total as int,base());
        assert(next<=2) by(nonlinear_arith)
            requires total as int==(a as int)+(b as int)+(c as int)+(carry as int),
                a<=u64::MAX,b<=u64::MAX,c<=u64::MAX,carry<=2,
                total as int==base()*(next as int)+(low as int),low>=0;
    }
    (low,next)
}

proof fn cross_step(original:Seq<u64>,before:Seq<u64>,after:Seq<u64>,z0:Seq<u64>,z2:Seq<u64>,
    i:nat,incoming:u64,low:u64,next:u64,plus:bool)
    requires original.len()==before.len(),before.len()==after.len(),after.len()==z0.len(),i<original.len(),
        before[i as int]==original[i as int],after[i as int]==low,
        forall|j:int| 0<=j<i ==> before[j]==after[j],
        prefix(before,i)+radix(i)*((incoming as int)-(if plus {0int}else{1int}))
            ==prefix(z0,i)+extended(z2,i)+(if plus {prefix(original,i)}else{-prefix(original,i)}),
        (low as int)+base()*(next as int)==(z0[i as int] as int)+digit(z2,i)
            +(if plus {original[i as int] as int}else{base()-1-(original[i as int] as int)})+(incoming as int),
    ensures prefix(after,i+1)+radix(i+1)*((next as int)-(if plus {0int}else{1int}))
            ==prefix(z0,i+1)+extended(z2,i+1)+(if plus {prefix(original,i+1)}else{-prefix(original,i+1)}),
{
    equal_prefix(after,before,i);
    extended_step(z2,i);
    assert((low as int)+base()*((next as int)-(if plus {0int}else{1int}))
        ==(z0[i as int] as int)+digit(z2,i)+(if plus {original[i as int] as int}else{-(original[i as int] as int)})
            +(incoming as int)-(if plus {0int}else{1int})) by(nonlinear_arith)
        requires (low as int)+base()*(next as int)==(z0[i as int] as int)+digit(z2,i)
            +(if plus {original[i as int] as int}else{base()-1-(original[i as int] as int)})+(incoming as int);
    assert(prefix(after,i+1)+radix(i+1)*((next as int)-(if plus {0int}else{1int}))
        ==prefix(z0,i+1)+extended(z2,i+1)+(if plus {prefix(original,i+1)}else{-prefix(original,i+1)})) by(nonlinear_arith)
        requires prefix(before,i)+radix(i)*((incoming as int)-(if plus {0int}else{1int}))
                ==prefix(z0,i)+extended(z2,i)+(if plus {prefix(original,i)}else{-prefix(original,i)}),
            prefix(after,i+1)==prefix(before,i)+(low as int)*radix(i),
            prefix(z0,i+1)==prefix(z0,i)+(z0[i as int] as int)*radix(i),
            prefix(original,i+1)==prefix(original,i)+(original[i as int] as int)*radix(i),
            extended(z2,i+1)==extended(z2,i)+digit(z2,i)*radix(i),
            (low as int)+base()*((next as int)-(if plus {0int}else{1int}))
                ==(z0[i as int] as int)+digit(z2,i)+(if plus {original[i as int] as int}else{-(original[i as int] as int)})
                    +(incoming as int)-(if plus {0int}else{1int}),
            radix(i+1)==base()*radix(i);
}

/// Reconstruct the cross term from z0, z2 and an absolute difference product.
pub fn combine_cross(dst:&mut[u64],z0:&[u64],z2:&[u64],negative:bool)->(high:u64)
    requires old(dst)@.len()==z0@.len(),z2@.len()<=z0@.len(),
        0<=value(z0@)+value(z2@)+(if negative {value(old(dst)@)}else{-value(old(dst)@)})<2*radix(z0@.len()),
    ensures final(dst)@.len()==old(dst)@.len(), high<=1,
        value(final(dst)@)+radix(z0@.len())*(high as int)
            ==value(z0@)+value(z2@)+(if negative {value(old(dst)@)}else{-value(old(dst)@)}),
{
    assert!(dst.len()==z0.len() && z2.len()<=z0.len());
    let ghost original=dst@;
    let mut i=0usize;
    if negative {
        let mut carry=0u64;
        while i<z2.len()
            invariant i<=z2@.len(),z2@.len()<=z0@.len(),dst@.len()==z0@.len(),dst@.len()==original.len(),carry<=2,
                forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
                prefix(dst@,i as nat)+radix(i as nat)*(carry as int)
                    ==prefix(z0@,i as nat)+extended(z2@,i as nat)+prefix(original,i as nat),
            decreases z2.len()-i,
        {
            let ghost before=dst@;let ghost incoming=carry;
            let (low,next)=cross_limb(z0[i],z2[i],dst[i],carry);
            dst[i]=low;
            proof {cross_step(original,before,dst@,z0@,z2@,i as nat,incoming,low,next,true);}
            carry=next;i+=1;
        }
        while i<dst.len()
            invariant z2@.len()<=i<=dst@.len(),z2@.len()<=z0@.len(),dst@.len()==z0@.len(),dst@.len()==original.len(),carry<=2,
                forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
                prefix(dst@,i as nat)+radix(i as nat)*(carry as int)
                    ==prefix(z0@,i as nat)+extended(z2@,i as nat)+prefix(original,i as nat),
            decreases dst.len()-i,
        {
            let ghost before=dst@;let ghost incoming=carry;
            let (low,next)=cross_limb(z0[i],0,dst[i],carry);
            dst[i]=low;
            proof {cross_step(original,before,dst@,z0@,z2@,i as nat,incoming,low,next,true);}
            carry=next;i+=1;
        }
        proof {
            prefix_range(dst@,dst@.len());
            assert(carry<=1) by(nonlinear_arith)
                requires 0<=value(dst@)<radix(dst@.len()),
                    value(dst@)+radix(z0@.len())*(carry as int)==value(z0@)+value(z2@)+value(original),
                    0<=value(z0@)+value(z2@)+value(original)<2*radix(z0@.len());
        }
        carry
    } else {
        let mut carry=1u64;
        while i<z2.len()
            invariant i<=z2@.len(),z2@.len()<=z0@.len(),dst@.len()==z0@.len(),dst@.len()==original.len(),carry<=2,
                forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
                prefix(dst@,i as nat)+radix(i as nat)*((carry as int)-1)
                    ==prefix(z0@,i as nat)+extended(z2@,i as nat)-prefix(original,i as nat),
            decreases z2.len()-i,
        {
            let ghost before=dst@;let ghost incoming=carry;
            let (low,next)=cross_limb(z0[i],z2[i],u64::MAX-dst[i],carry);
            dst[i]=low;
            proof {cross_step(original,before,dst@,z0@,z2@,i as nat,incoming,low,next,false);}
            carry=next;i+=1;
        }
        while i<dst.len()
            invariant z2@.len()<=i<=dst@.len(),z2@.len()<=z0@.len(),dst@.len()==z0@.len(),dst@.len()==original.len(),carry<=2,
                forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
                prefix(dst@,i as nat)+radix(i as nat)*((carry as int)-1)
                    ==prefix(z0@,i as nat)+extended(z2@,i as nat)-prefix(original,i as nat),
            decreases dst.len()-i,
        {
            let ghost before=dst@;let ghost incoming=carry;
            let (low,next)=cross_limb(z0[i],0,u64::MAX-dst[i],carry);
            dst[i]=low;
            proof {cross_step(original,before,dst@,z0@,z2@,i as nat,incoming,low,next,false);}
            carry=next;i+=1;
        }
        proof {
            prefix_range(dst@,dst@.len());
            assert(carry>=1) by(nonlinear_arith)
                requires 0<=value(dst@)<radix(z0@.len()),
                    value(dst@)+radix(z0@.len())*((carry as int)-1)==value(z0@)+value(z2@)-value(original),
                    0<=value(z0@)+value(z2@)-value(original)<2*radix(z0@.len());
        }
        carry-1
    }
}

/// Add a slice plus its one-word high part, modulo the destination radix.
pub fn add_cross(dst:&mut[u64],rhs:&[u64],high:u64)
    requires old(dst)@.len()>=rhs@.len(),high<=1,
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==(value(old(dst)@)+value(rhs@)+radix(rhs@.len())*(high as int))%radix(old(dst)@.len()),
{
    assert!(dst.len()>=rhs.len());
    let ghost before=dst@;
    let overflow=add_extended(dst,rhs);
    let ghost middle=dst@;
    let k=rhs.len();
    let overflow2=add_small(&mut dst[k..],high);
    proof {
        split(middle,k as nat);split(dst@,k as nat);radix_add(k as nat,(dst@.len()-k) as nat);
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        let total=value(before)+value(rhs@)+radix(k as nat)*(high as int);
        assert(total==((overflow as int)+(overflow2 as int))*radix(dst@.len())+value(dst@)) by(nonlinear_arith)
            requires value(middle)+radix(dst@.len())*(overflow as int)==value(before)+value(rhs@),
                part(dst@,k as nat,dst@.len())+radix((dst@.len()-k) as nat)*(overflow2 as int)
                    ==part(middle,k as nat,middle.len())+(high as int),
                value(dst@)==part(middle,0,k as nat)+radix(k as nat)*part(dst@,k as nat,dst@.len()),
                value(middle)==part(middle,0,k as nat)+radix(k as nat)*part(middle,k as nat,middle.len()),
                radix(dst@.len())==radix(k as nat)*radix((dst@.len()-k) as nat),
                total==value(before)+value(rhs@)+radix(k as nat)*(high as int);
        lemma_fundamental_div_mod_converse(total,radix(dst@.len()),(overflow as int)+(overflow2 as int),value(dst@));
    }
}
} // verus!

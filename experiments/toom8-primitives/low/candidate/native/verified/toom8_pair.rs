//! Simultaneous signed point-pair sums and differences in caller-owned slices.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::toom8_pair_spec::*;
use crate::{kernel,toom_words};
verus! {
#[inline(always)]
pub fn sum_difference(plus:&mut[u64],minus:&mut[u64],negative:bool)
    requires old(plus)@.len()==old(minus)@.len(),value(old(minus)@)<=value(old(plus)@),
        value(old(plus)@)+value(old(minus)@)<radix(old(plus)@.len()),
    ensures final(plus)@.len()==old(plus)@.len(),final(minus)@.len()==old(minus)@.len(),
        value(final(plus)@)==value(old(plus)@)+signed_magnitude(value(old(minus)@),negative),
        value(final(minus)@)==value(old(plus)@)-signed_magnitude(value(old(minus)@),negative),
{
    let ghost a=plus@;let ghost b=minus@;
    let n=plus.len();assert!(minus.len()==n);
    let mut i=0usize;let mut carry=0u64;let mut borrow=0u64;
    while i<n
        invariant i<=n,a.len()==n,b.len()==n,plus@.len()==n,minus@.len()==n,
            carry<=1,borrow<=1,
            value(b)<=value(a),value(a)+value(b)<radix(n as nat),
            forall|j:int|i<=j<n ==> #[trigger] plus@[j]==a[j],
            forall|j:int|i<=j<n ==> #[trigger] minus@[j]==b[j],
            sum_prefix(plus@,minus@,i as nat,negative)+radix(i as nat)*(carry as int)==prefix(a,i as nat)+prefix(b,i as nat),
            difference_prefix(plus@,minus@,i as nat,negative)-radix(i as nat)*(borrow as int)==prefix(a,i as nat)-prefix(b,i as nat),
        decreases n-i,
    {
        let ghost before_plus=plus@;let ghost before_minus=minus@;
        let ghost incoming_sum=carry;let ghost incoming_difference=borrow;
        let x=plus[i];let y=minus[i];
        let (sum,next_sum)=kernel::add_limb(x,y,carry);
        let (difference,next_difference)=kernel::sub_limb(x,y,borrow);
        plus[i]=if negative {difference}else{sum};
        minus[i]=if negative {sum}else{difference};
        proof {
            equal_prefix(plus@,before_plus,i as nat);equal_prefix(minus@,before_minus,i as nat);
            let r=radix(i as nat);
            lemma_mul_is_commutative(r,sum as int);lemma_mul_is_commutative(r,difference as int);
            lemma_mul_is_commutative(r,x as int);lemma_mul_is_commutative(r,y as int);
            scale_sum(sum_prefix(before_plus,before_minus,i as nat,negative),prefix(a,i as nat),prefix(b,i as nat),r,incoming_sum as int,sum as int,next_sum as int,x as int,y as int);
            scale_difference(difference_prefix(before_plus,before_minus,i as nat,negative),prefix(a,i as nat),prefix(b,i as nat),r,incoming_difference as int,difference as int,next_difference as int,x as int,y as int);
        }
        carry=next_sum;borrow=next_difference;i+=1;
    }
    proof {
        prefix_range(plus@,n as nat);prefix_range(minus@,n as nat);
        assert(carry==0 && borrow==0);
    }
}

#[inline(always)]
pub fn half_pair(plus:&mut[u64],minus:&mut[u64],negative:bool)
    requires old(plus)@.len()==old(minus)@.len(),value(old(minus)@)<=value(old(plus)@),
        value(old(plus)@)+value(old(minus)@)<radix(old(plus)@.len()),
        value(old(plus)@)%2==value(old(minus)@)%2,
    ensures final(plus)@.len()==old(plus)@.len(),final(minus)@.len()==old(minus)@.len(),
        2*value(final(plus)@)==value(old(plus)@)+signed_magnitude(value(old(minus)@),negative),
        2*value(final(minus)@)==value(old(plus)@)-signed_magnitude(value(old(minus)@),negative),
{
    let ghost a=value(plus@);let ghost b=value(minus@);
    proof {
        lemma_fundamental_div_mod(a,2);lemma_fundamental_div_mod(b,2);
        let qa=a/2;let qb=b/2;let rem=a%2;
        assert(a+b==2*(qa+qb+rem));assert(a-b==2*(qa-qb));
        lemma_mod_multiples_basic(qa+qb+rem,2);lemma_mod_multiples_basic(qa-qb,2);
        assert((a+b)%2==0 && (a-b)%2==0);
    }
    sum_difference(plus,minus,negative);
    toom_words::divide_exact(plus,2);
    toom_words::divide_exact(minus,2);
}
}

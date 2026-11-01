//! Single-pass four-block weighted evaluation; signed points reuse caller scratch.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::fast_product::*;
use crate::{fast_words,toom_words};
verus! {
pub proof fn term_bound(w:int,x:int)
    requires 0<=w,0<=x<=u64::MAX,
    ensures 0<=w*x<=w*(u64::MAX as int),
{
    assert(0<=w*x<=w*(u64::MAX as int)) by(nonlinear_arith)
        requires 0<=w,0<=x<=u64::MAX;
}

#[inline(always)]
pub fn weighted(dst:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],w0:u64,w1:u64,w2:u64,w3:u64)
    requires a0@.len()==a1@.len(),a0@.len()==a2@.len(),a3@.len()<=a0@.len(),old(dst)@.len()==a0@.len()+1,
        w0<=8,w1<=8,w2<=8,w3<=8,(w0 as int)+(w1 as int)+(w2 as int)+(w3 as int)<=15,
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==(w0 as int)*value(a0@)+(w1 as int)*value(a1@)+(w2 as int)*value(a2@)+(w3 as int)*value(a3@),
{
    let _output_len=dst.len();
    assert!(a0.len()==a1.len() && a0.len()==a2.len() && a3.len()<=a0.len());
    assert!(a0.len()<usize::MAX && dst.len()==a0.len()+1);
    assert!(w0<=8 && w1<=8 && w2<=8 && w3<=8 && w0+w1+w2+w3<=15);
    let k=a0.len();let mut carry=0u64;let mut i=0usize;
    while i<k
        invariant i<=k,a0@.len()==k,a1@.len()==k,a2@.len()==k,a3@.len()<=k,dst@.len()==k+1,carry<=14,
            w0<=8,w1<=8,w2<=8,w3<=8,(w0 as int)+(w1 as int)+(w2 as int)+(w3 as int)<=15,
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)
                ==(w0 as int)*prefix(a0@,i as nat)+(w1 as int)*prefix(a1@,i as nat)
                    +(w2 as int)*prefix(a2@,i as nat)+(w3 as int)*extended(a3@,i as nat),
        decreases k-i,
    {
        let x0=a0[i];let x1=a1[i];let x2=a2[i];let x3=if i<a3.len(){a3[i]}else{0};
        let ghost before=dst@;let ghost incoming=carry;
        proof {term_bound(w0 as int,x0 as int);term_bound(w1 as int,x1 as int);
            term_bound(w2 as int,x2 as int);term_bound(w3 as int,x3 as int);}
        let total=(w0 as u128)*(x0 as u128)+(w1 as u128)*(x1 as u128)
            +(w2 as u128)*(x2 as u128)+(w3 as u128)*(x3 as u128)+(carry as u128);
        let low=(total%18446744073709551616u128) as u64;
        let next=(total/18446744073709551616u128) as u64;
        proof {
            lemma_fundamental_div_mod(total as int,base());
            assert(total<=15*base()-1);
            assert(next<=14);
        }
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);extended_step(a3@,i as nat);
            let r=radix(i as nat);
            lemma_mul_is_distributive_add(w0 as int,prefix(a0@,i as nat),(x0 as int)*r);
            lemma_mul_is_distributive_add(w1 as int,prefix(a1@,i as nat),(x1 as int)*r);
            lemma_mul_is_distributive_add(w2 as int,prefix(a2@,i as nat),(x2 as int)*r);
            lemma_mul_is_distributive_add(w3 as int,extended(a3@,i as nat),(x3 as int)*r);
            lemma_mul_is_associative(w0 as int,x0 as int,r);
            lemma_mul_is_associative(w1 as int,x1 as int,r);
            lemma_mul_is_associative(w2 as int,x2 as int,r);
            lemma_mul_is_associative(w3 as int,x3 as int,r);
            lemma_mul_is_distributive_add_other_way(r,(w0 as int)*(x0 as int)+(w1 as int)*(x1 as int)
                +(w2 as int)*(x2 as int)+(w3 as int)*(x3 as int),incoming as int);
            lemma_mul_is_distributive_add_other_way(r,(w0 as int)*(x0 as int)+(w1 as int)*(x1 as int)
                +(w2 as int)*(x2 as int),(w3 as int)*(x3 as int));
            lemma_mul_is_distributive_add_other_way(r,(w0 as int)*(x0 as int)+(w1 as int)*(x1 as int),(w2 as int)*(x2 as int));
            lemma_mul_is_distributive_add_other_way(r,(w0 as int)*(x0 as int),(w1 as int)*(x1 as int));
            lemma_mul_is_distributive_add_other_way(r,low as int,base()*(next as int));
            lemma_mul_is_commutative(r,incoming as int);
            lemma_mul_is_commutative(base()*r,next as int);
            lemma_mul_is_associative(next as int,base(),r);
            lemma_mul_is_commutative(next as int,base());
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)
                ==(w0 as int)*prefix(a0@,(i+1) as nat)+(w1 as int)*prefix(a1@,(i+1) as nat)
                    +(w2 as int)*prefix(a2@,(i+1) as nat)+(w3 as int)*extended(a3@,(i+1) as nat));
        }
        carry=next;i+=1;
    }
    let ghost before=dst@;dst[k]=carry;
    proof {equal_prefix(dst@,before,k as nat);assert(extended(a3@,k as nat)==value(a3@));
        lemma_mul_is_commutative(carry as int,radix(k as nat));}
}

pub fn signed(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],half:bool)->(neg:bool)
    requires a0@.len()==a1@.len(),a0@.len()==a2@.len(),a3@.len()<=a0@.len(),
        old(dst)@.len()==a0@.len()+1,old(tmp)@.len()==old(dst)@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),final(tmp)@.len()==old(tmp)@.len(),
        (if neg{-value(final(dst)@)}else{value(final(dst)@)})
            ==if half{8*value(a0@)-4*value(a1@)+2*value(a2@)-value(a3@)}
                else{value(a0@)-value(a1@)+value(a2@)-value(a3@)},
        neg==(if half{8*value(a0@)+2*value(a2@)<4*value(a1@)+value(a3@)}
            else{value(a0@)+value(a2@)<value(a1@)+value(a3@)}),
{
    if half {
        weighted(dst,a0,a1,a2,a3,8,0,2,0);weighted(tmp,a0,a1,a2,a3,0,4,0,1);
    }else{
        weighted(dst,a0,a1,a2,a3,1,0,1,0);weighted(tmp,a0,a1,a2,a3,0,1,0,1);
    }
    let neg=fast_words::less(dst,tmp);
    if neg {
        let borrow=fast_words::reverse_subtract(dst,tmp);
        proof {prefix_range(dst@,dst@.len());if borrow!=0{assert(borrow==1);}}
    }else{toom_words::sub_exact(dst,tmp);}
    neg
}
}

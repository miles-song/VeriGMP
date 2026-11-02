//! Linear-time Toom-3 evaluation with one extra carry word.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::fast_product::*;
use crate::{fast_words,toom_words};
verus! {

#[inline(always)]
pub fn positive(dst:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],x:u64)
    requires a0@.len()==a1@.len(),a2@.len()<=a0@.len(),old(dst)@.len()==a0@.len()+1,1<=x<=2,
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==value(a0@)+(x as int)*value(a1@)+(x as int)*(x as int)*value(a2@),
{
    let _output_len=dst.len();
    assert!(a0.len()==a1.len() && a2.len()<=a0.len());
    assert!(a0.len()<usize::MAX && dst.len()==a0.len()+1);assert!(1<=x && x<=2);
    proof {assert((x as int)*(x as int)<=4) by(nonlinear_arith) requires 1<=x<=2;}
    let k=a0.len();let xx=x*x;let mut carry=0u64;let mut i=0usize;
    while i<k
        invariant i<=k,a0@.len()==k,a1@.len()==k,a2@.len()<=k,dst@.len()==k+1,carry<=6,
            1<=x<=2,xx as int==(x as int)*(x as int),xx<=4,
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)
                ==prefix(a0@,i as nat)+(x as int)*prefix(a1@,i as nat)+(xx as int)*extended(a2@,i as nat),
        decreases k-i,
    {
        let z=if i<a2.len(){a2[i]}else{0};
        let y=a1[i];let w=a0[i];let ghost incoming=carry;let ghost before=dst@;
        proof {
            assert(0<=(x as int)*(y as int)<=2*u64::MAX && 0<=(xx as int)*(z as int)<=4*u64::MAX)
                by(nonlinear_arith) requires 0<=x<=2,0<=xx<=4,0<=y<=u64::MAX,0<=z<=u64::MAX;
        }
        let total=(w as u128)+(x as u128)*(y as u128)+(xx as u128)*(z as u128)+(carry as u128);
        let low=(total%18446744073709551616u128) as u64;
        let next=(total/18446744073709551616u128) as u64;
        proof {
            lemma_fundamental_div_mod(total as int,base());
            assert(next<=6) by(nonlinear_arith)
                requires total==(w as int)+(x as int)*(y as int)+(xx as int)*(z as int)+(incoming as int),
                    w<=u64::MAX,y<=u64::MAX,z<=u64::MAX,x<=2,xx<=4,incoming<=6,
                    total==(next as int)*base()+(low as int),low>=0;
        }
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);extended_step(a2@,i as nat);
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)
                ==prefix(a0@,(i+1) as nat)+(x as int)*prefix(a1@,(i+1) as nat)+(xx as int)*extended(a2@,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)+radix(i as nat)*(incoming as int)
                    ==prefix(a0@,i as nat)+(x as int)*prefix(a1@,i as nat)+(xx as int)*extended(a2@,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(a0@,(i+1) as nat)==prefix(a0@,i as nat)+(w as int)*radix(i as nat),
                    prefix(a1@,(i+1) as nat)==prefix(a1@,i as nat)+(y as int)*radix(i as nat),
                    extended(a2@,(i+1) as nat)==extended(a2@,i as nat)+(z as int)*radix(i as nat),
                    (low as int)+base()*(next as int)==(w as int)+(x as int)*(y as int)+(xx as int)*(z as int)+(incoming as int),
                    radix((i+1) as nat)==base()*radix(i as nat);
        }
        carry=next;i+=1;
    }
    let ghost before=dst@;dst[k]=carry;
    proof {
        equal_prefix(dst@,before,k as nat);
        assert(extended(a2@,k as nat)==value(a2@));
        assert(value(dst@)==value(a0@)+(x as int)*value(a1@)+(x as int)*(x as int)*value(a2@)) by(nonlinear_arith)
            requires prefix(before,k as nat)+radix(k as nat)*(carry as int)
                    ==value(a0@)+(x as int)*value(a1@)+(xx as int)*value(a2@),
                value(dst@)==prefix(before,k as nat)+(carry as int)*radix(k as nat),
                xx as int==(x as int)*(x as int);
    }
}

pub fn negative(dst:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64])->(neg:bool)
    requires a0@.len()==a1@.len(),a2@.len()<=a0@.len(),old(dst)@.len()==a0@.len()+1,
    ensures final(dst)@.len()==old(dst)@.len(),
        (if neg {-value(final(dst)@)}else{value(final(dst)@)})==value(a0@)-value(a1@)+value(a2@),
        neg==(value(a0@)+value(a2@)<value(a1@)),
{
    let _output_len=dst.len();
    assert!(a0.len()==a1.len() && a2.len()<=a0.len());
    assert!(a0.len()<usize::MAX && dst.len()==a0.len()+1);
    toom_words::copy_pad(dst,a0);
    proof {
        prefix_range(a0@,a0@.len());prefix_range(a2@,a2@.len());
        crate::product::radix_add(a2@.len(),(a0@.len()-a2@.len()) as nat);
        radix_positive((a0@.len()-a2@.len()) as nat);radix_positive(a0@.len());
        assert(value(a2@)<radix(a0@.len())) by(nonlinear_arith)
            requires 0<=value(a2@)<radix(a2@.len()),radix(a0@.len())==radix(a2@.len())*radix((a0@.len()-a2@.len()) as nat),
                radix((a0@.len()-a2@.len()) as nat)>=1,radix(a2@.len())>0;
        assert(value(dst@)+value(a2@)<radix(dst@.len())) by(nonlinear_arith)
            requires value(dst@)==value(a0@),value(a0@)<radix(a0@.len()),value(a2@)<radix(a0@.len()),
                radix(dst@.len())==base()*radix(a0@.len()),radix(a0@.len())>0;
    }
    toom_words::add_exact(dst,a2);
    let neg=fast_words::less(dst,a1);
    if neg {
        let borrow=toom_words::reverse_subtract_extended(dst,a1);
        proof {prefix_range(dst@,dst@.len());if borrow!=0 {assert(borrow==1);}}
    } else {toom_words::sub_exact(dst,a1);}
    neg
}
}

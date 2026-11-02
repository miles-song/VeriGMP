//! One signed evaluation pass, followed by magnitude conversion only if negative.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::fast_product::*;
use crate::signed_evaluation_spec::*;
use crate::kernel;
verus! {
#[inline(always)]
pub fn limb(x0:u64,x1:u64,x2:u64,x3:u64,incoming:i64,half:bool)->(out:(u64,i64))
    requires -5<=incoming<=10,
    ensures -5<=out.1<=10,
        (out.0 as int)+base()*(out.1 as int)
            ==weighted(x0 as int,x1 as int,x2 as int,x3 as int,half)+(incoming as int),
{
    let total=if half {8*(x0 as i128)-4*(x1 as i128)+2*(x2 as i128)-(x3 as i128)+(incoming as i128)}
        else {(x0 as i128)-(x1 as i128)+(x2 as i128)-(x3 as i128)+(incoming as i128)};
    assert(-5*base()<=total<=10*base());
    let biased=(total+295147905179352825856i128) as u128;
    let low=(biased%18446744073709551616u128) as u64;
    let high=(biased/18446744073709551616u128) as i64;
    proof {
        lemma_fundamental_div_mod(biased as int,base());
        assert(11<=high<=26);
    }
    (low,high-16)
}

pub fn negate(dst:&mut[u64])
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==if value(old(dst)@)==0 {0} else {radix(old(dst)@.len())-value(old(dst)@)},
{
    let ghost original=dst@;
    let n=dst.len();let mut i=0usize;let mut borrow=0u64;
    while i<n
        invariant i<=n,dst@.len()==n,original.len()==n,borrow<=1,
            prefix(dst@,i as nat)-radix(i as nat)*(borrow as int)==-prefix(original,i as nat),
            forall|j:int| i<=j<n ==> dst@[j]==original[j],
        decreases n-i,
    {
        let ghost before=dst@;let ghost incoming=borrow;
        let (low,next)=kernel::sub_limb(0,dst[i],borrow);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)==-prefix(original,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)==-prefix(original,i as nat),
                    (low as int)-base()*(next as int)==-(original[i as int] as int)-(incoming as int),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    radix((i+1) as nat)==base()*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(original[i as int] as int)*radix(i as nat);
        }
        borrow=next;i+=1;
    }
    proof {
        prefix_range(original,n as nat);prefix_range(dst@,n as nat);
        if value(original)==0 {assert(borrow==0);} else {assert(borrow==1);}
    }
}

#[inline(always)]
pub fn signed(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],half:bool)->(neg:bool)
    requires a0@.len()==a1@.len(),a0@.len()==a2@.len(),a3@.len()<=a0@.len(),
        old(dst)@.len()==a0@.len()+1,old(tmp)@.len()==old(dst)@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),final(tmp)@==old(tmp)@,
        (if neg {-value(final(dst)@)}else{value(final(dst)@)})==evaluation(a0@,a1@,a2@,a3@,half),
        neg==(evaluation(a0@,a1@,a2@,a3@,half)<0),
{
    let _capacity=dst.len();let _tmp_capacity=tmp.len();
    let k=a0.len();
    assert!(a0.len()==a1.len() && a0.len()==a2.len() && a3.len()<=k);
    assert!(k<usize::MAX && dst.len()==k+1 && tmp.len()==dst.len());
    let mut i=0usize;let mut carry=0i64;
    while i<k
        invariant i<=k,a0@.len()==k,a1@.len()==k,a2@.len()==k,a3@.len()<=k,dst@.len()==k+1,
            -5<=carry<=10,
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)==input_prefix(a0@,a1@,a2@,a3@,i as nat,half),
        decreases k-i,
    {
        let ghost before=dst@;let ghost incoming=carry;
        let x3=if i<a3.len(){a3[i]}else{0};
        let (low,next)=limb(a0[i],a1[i],a2[i],x3,carry,half);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);prefix_step(a0@,a1@,a2@,a3@,i as nat,half);
            let r=radix(i as nat);
            let w=weighted(digit(a0@,i as nat),digit(a1@,i as nat),digit(a2@,i as nat),digit(a3@,i as nat),half);
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)==input_prefix(a0@,a1@,a2@,a3@,(i+1) as nat,half)) by(nonlinear_arith)
                requires prefix(before,i as nat)+r*(incoming as int)==input_prefix(a0@,a1@,a2@,a3@,i as nat,half),
                    input_prefix(a0@,a1@,a2@,a3@,(i+1) as nat,half)==input_prefix(a0@,a1@,a2@,a3@,i as nat,half)+r*w,
                    (low as int)+base()*(next as int)==w+(incoming as int),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*r,
                    radix((i+1) as nat)==base()*r;
        }
        carry=next;i+=1;
    }
    let negative=carry<0;
    let high=if negative {(18446744073709551616i128+(carry as i128)) as u64}else{carry as u64};
    let ghost before=dst@;dst[k]=high;
    proof {
        equal_prefix(dst@,before,k as nat);prefix_range(before,k as nat);radix_positive(k as nat);
        assert(input_prefix(a0@,a1@,a2@,a3@,k as nat,half)==evaluation(a0@,a1@,a2@,a3@,half));
        let e=evaluation(a0@,a1@,a2@,a3@,half);
        let r=radix(k as nat);
        lemma_mul_is_commutative(high as int,r);
        assert(value(dst@)==prefix(before,k as nat)+r*(high as int));
        assert(negative==(e<0)) by(nonlinear_arith)
            requires e==prefix(before,k as nat)+r*(carry as int),0<=prefix(before,k as nat)<r,r>0,negative==(carry<0);
        assert(value(dst@)==e+(if negative {radix(dst@.len())}else{0})) by(nonlinear_arith)
            requires e==prefix(before,k as nat)+r*(carry as int),
                value(dst@)==prefix(before,k as nat)+r*(high as int),
                high as int==(carry as int)+(if negative {base()}else{0}),radix(dst@.len())==base()*r;
        if negative {
            assert(value(dst@)>0) by(nonlinear_arith)
                requires value(dst@)==prefix(before,k as nat)+r*(high as int),prefix(before,k as nat)>=0,r>0,high>0;
        }
    }
    if negative {negate(dst);}
    negative
}
}

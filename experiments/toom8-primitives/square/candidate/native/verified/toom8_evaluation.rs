//! One weighted carry pass and optional magnitude conversion; no heap workspace.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::fast_product::*;
use crate::toom8_evaluation_spec::*;
verus! {
pub proof fn product_bound(x:u64,w:u64)
    requires w<=2097152,
    ensures 0<=(x as int)*(w as int)<=(base()-1)*(w as int)<=(base()-1)*2097152,
{
    assert(0<=(x as int)*(w as int)<=(base()-1)*(w as int)<=(base()-1)*2097152) by(nonlinear_arith)
        requires 0<=x<base(),0<=w<=2097152;
}
#[inline(always)]
pub fn limb(x0:u64,x1:u64,x2:u64,x3:u64,x4:u64,x5:u64,x6:u64,x7:u64,w:[u64;8],incoming:i64,negative:bool)->(out:(u64,i64))
    requires weights_valid(w@),-4194304<=incoming<=4194304,
    ensures -4194304<=out.1<=4194304,
        (out.0 as int)+base()*(out.1 as int)==weighted(x0 as int,x1 as int,x2 as int,x3 as int,x4 as int,x5 as int,x6 as int,x7 as int,w@,negative)+(incoming as int),
{
    proof {
        product_bound(x0,w[0]);
        product_bound(x1,w[1]);
        product_bound(x2,w[2]);
        product_bound(x3,w[3]);
        product_bound(x4,w[4]);
        product_bound(x5,w[5]);
        product_bound(x6,w[6]);
        product_bound(x7,w[7]);
    }
    let p0=(x0 as i128)*(w[0] as i128);
    let p1=(x1 as i128)*(w[1] as i128);
    let p2=(x2 as i128)*(w[2] as i128);
    let p3=(x3 as i128)*(w[3] as i128);
    let p4=(x4 as i128)*(w[4] as i128);
    let p5=(x5 as i128)*(w[5] as i128);
    let p6=(x6 as i128)*(w[6] as i128);
    let p7=(x7 as i128)*(w[7] as i128);
    let even=p0+p2+p4+p6;let odd=p1+p3+p5+p7;
    proof {
        assert((p0 as int)+(p1 as int)+(p2 as int)+(p3 as int)+(p4 as int)+(p5 as int)+(p6 as int)+(p7 as int)
            <=18446744073709551615int*((w[0] as int)+(w[1] as int)+(w[2] as int)+(w[3] as int)+(w[4] as int)+(w[5] as int)+(w[6] as int)+(w[7] as int))) by(nonlinear_arith)
            requires 0<=p0<=(base()-1)*(w[0] as int),
                0<=p1<=(base()-1)*(w[1] as int),
                0<=p2<=(base()-1)*(w[2] as int),
                0<=p3<=(base()-1)*(w[3] as int),
                0<=p4<=(base()-1)*(w[4] as int),
                0<=p5<=(base()-1)*(w[5] as int),
                0<=p6<=(base()-1)*(w[6] as int),
                0<=p7<=(base()-1)*(w[7] as int);
        lemma_mul_is_commutative(x0 as int,w[0] as int);
        lemma_mul_is_commutative(x1 as int,w[1] as int);
        lemma_mul_is_commutative(x2 as int,w[2] as int);
        lemma_mul_is_commutative(x3 as int,w[3] as int);
        lemma_mul_is_commutative(x4 as int,w[4] as int);
        lemma_mul_is_commutative(x5 as int,w[5] as int);
        lemma_mul_is_commutative(x6 as int,w[6] as int);
        lemma_mul_is_commutative(x7 as int,w[7] as int);
    }
    let total=even+(if negative {-odd}else{odd})+(incoming as i128);
    assert(-77371252455336267181195264i128<total<77371252455336267181195264i128);
    let biased=(total+77371252455336267181195264i128) as u128;
    let low=(biased%18446744073709551616u128) as u64;
    let high=(biased/18446744073709551616u128) as i64;
    proof {lemma_fundamental_div_mod(biased as int,base());assert(0<=high<8388608);}
    (low,high-4194304)
}
#[inline(always)]
pub fn evaluate(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64],weights:[u64;8],negative_point:bool)->(neg:bool)
    requires a1@.len()==a0@.len(),a2@.len()==a0@.len(),a3@.len()==a0@.len(),a4@.len()==a0@.len(),a5@.len()==a0@.len(),a6@.len()==a0@.len(),a7@.len()<=a0@.len(),weights_valid(weights@),
        old(dst)@.len()==a0@.len()+1,old(tmp)@.len()==old(dst)@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),final(tmp)@==old(tmp)@,
        (if neg {-value(final(dst)@)}else{value(final(dst)@)})==evaluation(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,weights@,negative_point),
        neg==(evaluation(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,weights@,negative_point)<0),
{
    let _capacity=dst.len();let _tmp_capacity=tmp.len();
    let k=a0.len();
    assert!(a0.len()==a1.len() && a0.len()==a2.len() && a3.len()==k && a4.len()==k && a5.len()==k && a6.len()==k && a7.len()<=k);
    assert!(k<usize::MAX && dst.len()==k+1 && tmp.len()==dst.len());
    let mut i=0usize;let mut carry=0i64;
    while i<k
        invariant i<=k,a0@.len()==k,a1@.len()==k,a2@.len()==k,a3@.len()==k,a4@.len()==k,a5@.len()==k,a6@.len()==k,a7@.len()<=k,weights_valid(weights@),dst@.len()==k+1,
            -4194304<=carry<=4194304,
            prefix(dst@,i as nat)+radix(i as nat)*(carry as int)==input_prefix(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,i as nat,weights@,negative_point),
        decreases k-i,
    {
        let ghost before=dst@;let ghost incoming=carry;
        let x7=if i<a7.len(){a7[i]}else{0};
        let (low,next)=limb(a0[i],a1[i],a2[i],a3[i],a4[i],a5[i],a6[i],x7,weights,carry,negative_point);
        dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);prefix_step(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,i as nat,weights@,negative_point);
            let r=radix(i as nat);
            let w=weighted(digit(a0@,i as nat),digit(a1@,i as nat),digit(a2@,i as nat),digit(a3@,i as nat),digit(a4@,i as nat),digit(a5@,i as nat),digit(a6@,i as nat),digit(a7@,i as nat),weights@,negative_point);
            assert(prefix(dst@,(i+1) as nat)+radix((i+1) as nat)*(next as int)==input_prefix(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,(i+1) as nat,weights@,negative_point)) by(nonlinear_arith)
                requires prefix(before,i as nat)+r*(incoming as int)==input_prefix(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,i as nat,weights@,negative_point),
                    input_prefix(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,(i+1) as nat,weights@,negative_point)==input_prefix(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,i as nat,weights@,negative_point)+r*w,
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
        assert(input_prefix(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,k as nat,weights@,negative_point)==evaluation(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,weights@,negative_point));
        let e=evaluation(a0@,a1@,a2@,a3@,a4@,a5@,a6@,a7@,weights@,negative_point);
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
    if negative {crate::signed_evaluation::negate(dst);}
    negative
}

#[inline(always)]
pub fn dyadic_weights(exponent:u32,reciprocal:bool)->(out:[u64;8])
    requires exponent<=3,
    ensures weights_valid(out@),
        forall|j:int| 0<=j<8 ==> #[trigger] out@[j] as int==point_weight(exponent,j,reciprocal),
{
    assert!(exponent<=3);
    let out=if exponent==0 {[1u64,1,1,1,1,1,1,1]}
    else if exponent==1 {if reciprocal {[128u64,64,32,16,8,4,2,1]}else{[1u64,2,4,8,16,32,64,128]}}
    else if exponent==2 {if reciprocal {[16384u64,4096,1024,256,64,16,4,1]}else{[1u64,4,16,64,256,1024,4096,16384]}}
    else {if reciprocal {[2097152u64,262144,32768,4096,512,64,8,1]}else{[1u64,8,64,512,4096,32768,262144,2097152]}}
    ;
    proof {
        point_constants();
        assert forall|j:int|0<=j<8 implies #[trigger] out@[j] as int==point_weight(exponent,j,reciprocal) by {
            if exponent==0 {if j==0 {} else if j==1 {} else if j==2 {} else if j==3 {} else if j==4 {} else if j==5 {} else if j==6 {} else {assert(j==7);}}
            else if exponent==1 {if j==0 {} else if j==1 {} else if j==2 {} else if j==3 {} else if j==4 {} else if j==5 {} else if j==6 {} else {assert(j==7);}}
            else if exponent==2 {if j==0 {} else if j==1 {} else if j==2 {} else if j==3 {} else if j==4 {} else if j==5 {} else if j==6 {} else {assert(j==7);}}
            else {assert(exponent==3);if j==0 {} else if j==1 {} else if j==2 {} else if j==3 {} else if j==4 {} else if j==5 {} else if j==6 {} else {assert(j==7);}}
        }
        assert forall|j:int|0<=j<8 implies out@[j]<=2097152 by {
            if j==0 {} else if j==1 {} else if j==2 {} else if j==3 {}
            else if j==4 {} else if j==5 {} else if j==6 {} else {assert(j==7);}
        }
    }
    out
}
#[inline(always)]
pub fn dyadic(dst:&mut[u64],tmp:&mut[u64],a0:&[u64],a1:&[u64],a2:&[u64],a3:&[u64],a4:&[u64],a5:&[u64],a6:&[u64],a7:&[u64],exponent:u32,reciprocal:bool,negative_point:bool)->(neg:bool)
    requires exponent<=3,a1@.len()==a0@.len(),a2@.len()==a0@.len(),a3@.len()==a0@.len(),a4@.len()==a0@.len(),a5@.len()==a0@.len(),a6@.len()==a0@.len(),a7@.len()<=a0@.len(),
        old(dst)@.len()==a0@.len()+1,old(tmp)@.len()==old(dst)@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),final(tmp)@==old(tmp)@,
        (if neg {-value(final(dst)@)}else{value(final(dst)@)})==homogeneous(seq![value(a0@),value(a1@),value(a2@),value(a3@),value(a4@),value(a5@),value(a6@),value(a7@)],exponent,reciprocal,negative_point),
        neg==(homogeneous(seq![value(a0@),value(a1@),value(a2@),value(a3@),value(a4@),value(a5@),value(a6@),value(a7@)],exponent,reciprocal,negative_point)<0),
{
    let weights=dyadic_weights(exponent,reciprocal);
    evaluate(dst,tmp,a0,a1,a2,a3,a4,a5,a6,a7,weights,negative_point)
}
}

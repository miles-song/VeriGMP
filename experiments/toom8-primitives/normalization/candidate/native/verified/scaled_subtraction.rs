//! Exact scaled subtraction used only by this isolated Toom-4 interpolation candidate.
use vstd::prelude::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::{fast_words,multiply};
verus! {
#[inline(always)]
pub fn sub_scaled_exact(dst:&mut[u64],rhs:&[u64],word:u64)
    requires old(dst)@.len()>=rhs@.len(),
        value(old(dst)@)>=(word as int)*value(rhs@),
    ensures final(dst)@.len()==old(dst)@.len(),
        value(final(dst)@)==value(old(dst)@)-(word as int)*value(rhs@),
{
    assert!(dst.len()>=rhs.len());
    let ghost original=dst@;
    let mut i=0usize;let mut carry=0u64;
    while i<dst.len()
        invariant i<=dst@.len(),dst@.len()==original.len(),dst@.len()>=rhs@.len(),carry<=word,
            value(original)>=(word as int)*value(rhs@),
            forall|j:int| i<=j<dst@.len() ==> #[trigger] dst@[j]==original[j],
            prefix(dst@,i as nat)-radix(i as nat)*(carry as int)
                ==prefix(original,i as nat)-(word as int)*extended(rhs@,i as nat),
        decreases dst.len()-i,
    {
        let x=dst[i];let y=if i<rhs.len(){rhs[i]}else{0};
        let ghost before=dst@;let ghost incoming=carry;
        let (product,high)=multiply::mac(word,y,0,carry);
        let (low,borrow)=fast_words::sub_word(x,product,0);
        proof {
            assert((product as int)+base()*(high as int)<=base()*(word as int)) by(nonlinear_arith)
                requires (product as int)+base()*(high as int)==(word as int)*(y as int)+(incoming as int),
                    incoming<=word,word>=0,y<base();
            assert(high<=word) by(nonlinear_arith)
                requires (product as int)+base()*(high as int)<=base()*(word as int),product>=0,base()>0;
            if high==word {
                assert(product==0) by(nonlinear_arith)
                    requires (product as int)+base()*(high as int)<=base()*(word as int),high==word,product>=0;
                assert(borrow==0) by(nonlinear_arith)
                    requires (low as int)-base()*(borrow as int)==(x as int)-(product as int),
                        product==0,low<base(),x>=0,borrow>=0,base()>0;
            }
            assert((high as int)+(borrow as int)<=word);
        }
        let next=high+borrow;dst[i]=low;
        proof {
            equal_prefix(dst@,before,i as nat);extended_step(rhs@,i as nat);
            assert(prefix(dst@,(i+1) as nat)-radix((i+1) as nat)*(next as int)
                ==prefix(original,(i+1) as nat)-(word as int)*extended(rhs@,(i+1) as nat)) by(nonlinear_arith)
                requires prefix(before,i as nat)-radix(i as nat)*(incoming as int)
                        ==prefix(original,i as nat)-(word as int)*extended(rhs@,i as nat),
                    prefix(dst@,(i+1) as nat)==prefix(before,i as nat)+(low as int)*radix(i as nat),
                    prefix(original,(i+1) as nat)==prefix(original,i as nat)+(x as int)*radix(i as nat),
                    extended(rhs@,(i+1) as nat)==extended(rhs@,i as nat)+(y as int)*radix(i as nat),
                    (product as int)+base()*(high as int)==(word as int)*(y as int)+(incoming as int),
                    (low as int)-base()*(borrow as int)==(x as int)-(product as int),
                    next==(high as int)+(borrow as int),radix((i+1) as nat)==base()*radix(i as nat);
        }
        carry=next;
        i+=1;
    }
    proof {
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        assert(carry==0) by(nonlinear_arith)
            requires value(dst@)-radix(dst@.len())*(carry as int)
                    ==value(original)-(word as int)*value(rhs@),
                value(original)>=(word as int)*value(rhs@),value(dst@)<radix(dst@.len()),
                radix(dst@.len())>0,carry>=0;
        assert(value(dst@)==value(original)-(word as int)*value(rhs@)) by(nonlinear_arith)
            requires value(dst@)-radix(dst@.len())*(carry as int)
                    ==value(original)-(word as int)*value(rhs@),carry==0;
    }
}

}

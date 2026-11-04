//! One triangular set of cross products, then fused doubling and diagonal squares.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;
use crate::square_base_spec::*;
use crate::{multiply,square_spec};
verus! {

fn double_diagonal(lo:u64,hi:u64,a:u64,carry:u64)->(out:(u64,u64,u64))
    requires carry<=2,
    ensures out.2<=2,
        (out.0 as int)+base()*(out.1 as int)+(base()*base())*(out.2 as int)
            ==2*((lo as int)+base()*(hi as int))+(a as int)*(a as int)+(carry as int),
{
    assert((a as int)*(a as int)<=u128::MAX) by(nonlinear_arith);
    let radix=18446744073709551616u128;
    let square=(a as u128)*(a as u128);
    let low=2*(lo as u128)+square%radix+(carry as u128);
    let high=2*(hi as u128)+square/radix+low/radix;
    proof {
        lemma_fundamental_div_mod(square as int,base());
        lemma_mod_division_less_than_divisor(square as int,base());
        lemma_fundamental_div_mod(low as int,base());
        lemma_mod_division_less_than_divisor(low as int,base());
        lemma_fundamental_div_mod(high as int,base());
        lemma_mod_division_less_than_divisor(high as int,base());
        assert((low as int)%base()+base()*((high as int)%base())+(base()*base())*((high as int)/base())
            ==2*((lo as int)+base()*(hi as int))+(a as int)*(a as int)+(carry as int)) by(nonlinear_arith)
            requires square as int==(a as int)*(a as int),
                square as int==base()*((square as int)/base())+(square as int)%base(),
                low as int==2*(lo as int)+(square as int)%base()+(carry as int),
                high as int==2*(hi as int)+(square as int)/base()+(low as int)/base(),
                low as int==base()*((low as int)/base())+(low as int)%base(),
                high as int==base()*((high as int)/base())+(high as int)%base();
    }
    ((low%radix) as u64,(high%radix) as u64,(high/radix) as u64)
}

#[verifier::rlimit(20)]
#[verifier::spinoff_prover]
pub fn full(dst:&mut[u64],a:&[u64])
    requires a@.len()>0,old(dst)@.len()==2*a@.len(),
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(a@)*value(a@),
{
    let _output_len=dst.len();
    proof {lemma_fundamental_div_mod(usize::MAX as int,2);}
    assert!(a.len()>0 && a.len()<=usize::MAX/2);
    let n=a.len();assert!(dst.len()==2*n);
    let mut z=0usize;
    while z<dst.len()
        invariant dst@.len()==2*n,n<=usize::MAX/2,z<=dst@.len(),prefix(dst@,z as nat)==0,
            forall|j:int| 0<=j<z ==> #[trigger] dst@[j]==0,
        decreases dst.len()-z,
    {
        let ghost before=dst@;dst[z]=0;
        proof {equal_prefix(before,dst@,z as nat);}
        z+=1;
    }
    proof {reveal_with_fuel(triangle,2);assert(triangle(a@,1)==0);}
    let mut i=1usize;
    while i<n
        invariant a@.len()==n,dst@.len()==2*n,n<=usize::MAX/2,1<=i<=n,
            value(dst@)==triangle(a@,i as nat),
            forall|j:int| 2*i<=j<dst@.len() ==> #[trigger] dst@[j]==0,
        decreases n-i,
    {
        let ghost before=dst@;
        let carry=multiply::add_mul_word(&mut dst[i..2*i],&a[..i],a[i]);
        let ghost middle=dst@;
        dst[2*i]=carry;
        proof {
            reveal_with_fuel(prefix,2);
            equal_prefix(a@,a@.subrange(0,i as int),i as nat);
            segment_split(before,i as nat,(2*i) as nat);
            segment_split(middle,i as nat,(2*i) as nat);
            equal_prefix(before,middle,i as nat);
            equal_prefix(middle,dst@,(2*i) as nat);
            prefix_frame(before,dst@,(2*i+1) as nat);
            radix_add(i as nat,i as nat);
            assert(before[2*i as int]==0);
            assert(value(dst@)==value(before)+radix(i as nat)*(a@[i as int] as int)*prefix(a@,i as nat))
                by(nonlinear_arith)
                requires value(dst@)-value(before)==prefix(dst@,(2*i+1) as nat)-prefix(before,(2*i+1) as nat),
                    prefix(dst@,(2*i+1) as nat)==prefix(middle,(2*i) as nat)+(carry as int)*radix((2*i) as nat),
                    prefix(before,(2*i+1) as nat)==prefix(before,(2*i) as nat),
                    prefix(middle,(2*i) as nat)==prefix(before,i as nat)+radix(i as nat)*part(middle,i as nat,(2*i) as nat),
                    prefix(before,(2*i) as nat)==prefix(before,i as nat)+radix(i as nat)*part(before,i as nat,(2*i) as nat),
                    part(middle,i as nat,(2*i) as nat)+radix(i as nat)*(carry as int)
                        ==part(before,i as nat,(2*i) as nat)+(a@[i as int] as int)*prefix(a@,i as nat),
                    radix((2*i) as nat)==radix(i as nat)*radix(i as nat);
            assert(triangle(a@,(i+1) as nat)==triangle(a@,i as nat)+(a@[i as int] as int)*prefix(a@,i as nat)*radix(i as nat));
            assert(value(dst@)==triangle(a@,(i+1) as nat)) by(nonlinear_arith)
                requires value(dst@)==value(before)+radix(i as nat)*(a@[i as int] as int)*prefix(a@,i as nat),
                    value(before)==triangle(a@,i as nat),
                    triangle(a@,(i+1) as nat)==triangle(a@,i as nat)+(a@[i as int] as int)*prefix(a@,i as nat)*radix(i as nat);
        }
        i+=1;
    }
    let ghost cross=dst@;
    let mut j=0usize;let mut carry=0u64;
    while j<n
        invariant a@.len()==n,dst@.len()==2*n,cross.len()==2*n,n<=usize::MAX/2,j<=n,carry<=2,
            value(cross)==triangle(a@,n as nat),
            forall|k:int| 2*j<=k<dst@.len() ==> #[trigger] dst@[k]==cross[k],
            prefix(dst@,(2*j) as nat)+radix((2*j) as nat)*(carry as int)
                ==2*prefix(cross,(2*j) as nat)+diagonal(a@,j as nat),
        decreases n-j,
    {
        let ghost before=dst@;let ghost incoming=carry;
        let (low,high,next)=double_diagonal(dst[2*j],dst[2*j+1],a[j],carry);
        dst[2*j]=low;dst[2*j+1]=high;
        proof {
            reveal_with_fuel(prefix,2);
            equal_prefix(before,dst@,(2*j) as nat);
            assert(prefix(dst@,(2*j+2) as nat)+radix((2*j+2) as nat)*(next as int)
                ==2*prefix(cross,(2*j+2) as nat)+diagonal(a@,(j+1) as nat)) by(nonlinear_arith)
                requires prefix(dst@,(2*j) as nat)==prefix(before,(2*j) as nat),
                    prefix(before,(2*j) as nat)+radix((2*j) as nat)*(incoming as int)
                        ==2*prefix(cross,(2*j) as nat)+diagonal(a@,j as nat),
                    prefix(dst@,(2*j+2) as nat)==prefix(before,(2*j) as nat)
                        +(low as int)*radix((2*j) as nat)+(high as int)*radix((2*j+1) as nat),
                    prefix(cross,(2*j+2) as nat)==prefix(cross,(2*j) as nat)
                        +(cross[2*j as int] as int)*radix((2*j) as nat)+(cross[2*j as int+1] as int)*radix((2*j+1) as nat),
                    (low as int)+base()*(high as int)+(base()*base())*(next as int)
                        ==2*((cross[2*j as int] as int)+base()*(cross[2*j as int+1] as int))+(a@[j as int] as int)*(a@[j as int] as int)+(incoming as int),
                    diagonal(a@,(j+1) as nat)==diagonal(a@,j as nat)+(a@[j as int] as int)*(a@[j as int] as int)*radix((2*j) as nat),
                    radix((2*j+1) as nat)==base()*radix((2*j) as nat),
                    radix((2*j+2) as nat)==base()*radix((2*j+1) as nat);
        }
        carry=0;j+=1;
    }
    proof {
        square_identity(a@,n as nat);prefix_range(a@,n as nat);
        square_spec::square_range(value(a@),radix(n as nat));radix_add(n as nat,n as nat);
        prefix_range(dst@,dst@.len());radix_positive(dst@.len());
        assert(carry==0) by(nonlinear_arith)
            requires value(dst@)+radix((2*n) as nat)*(carry as int)==value(a@)*value(a@),
                value(a@)*value(a@)<radix((2*n) as nat),value(dst@)>=0,carry>=0,radix((2*n) as nat)>0;
    }
}
}

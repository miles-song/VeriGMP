//! Const-size row multiplication for measured full-product leaves.
//! The first row overwrites dirty output; all storage belongs to the caller.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::product::*;
use crate::fast_product::*;

verus! {

#[inline(always)]
fn wide(a:u64,b:u64,acc:u64,carry:u128)->(out:(u64,u128))
    requires carry<=u64::MAX,
    ensures out.1<=u64::MAX,
        out.0 as int+base()*(out.1 as int)
            ==(a as int)*(b as int)+(acc as int)+(carry as int),
{
    assert((a as int)*(b as int)+(acc as int)+(carry as int)<=u128::MAX)
        by(nonlinear_arith);
    let total=(a as u128)*(b as u128)+(acc as u128)+carry;
    let radix:u128=18446744073709551616;
    proof {lemma_fundamental_div_mod(total as int,radix as int);}
    ((total%radix) as u64,total/radix)
}

#[inline(always)]
fn first<const N:usize>(dst:&mut[u64],b:&[u64],word:u64)->(out:u64)
    requires old(dst)@.len()==N,b@.len()==N,
    ensures final(dst)@.len()==N,
        value(final(dst)@)+radix(N as nat)*(out as int)==(word as int)*value(b@),
{
    assert!(dst.len()==N && b.len()==N);
    let mut j=0usize;
    let mut carry=0u128;
    while j<N
        invariant dst@.len()==N,b@.len()==N,j<=N,carry<=u64::MAX,
            prefix(dst@,j as nat)+radix(j as nat)*(carry as int)
                ==(word as int)*prefix(b@,j as nat),
        decreases N-j,
    {
        let ghost before=dst@;
        let ghost incoming=carry;
        let (low,next)=wide(word,b[j],0,carry);
        dst[j]=low;
        proof {
            equal_prefix(dst@,before,j as nat);
            assert(prefix(dst@,(j+1) as nat)+radix((j+1) as nat)*(next as int)
                ==(word as int)*prefix(b@,(j+1) as nat)) by(nonlinear_arith)
                requires prefix(before,j as nat)+radix(j as nat)*(incoming as int)
                        ==(word as int)*prefix(b@,j as nat),
                    low as int+base()*(next as int)==(word as int)*(b@[j as int] as int)+(incoming as int),
                    prefix(dst@,(j+1) as nat)==prefix(before,j as nat)+(low as int)*radix(j as nat),
                    prefix(b@,(j+1) as nat)==prefix(b@,j as nat)+(b@[j as int] as int)*radix(j as nat),
                    radix((j+1) as nat)==base()*radix(j as nat);
        }
        carry=next;
        j+=1;
    }
    carry as u64
}

#[inline(always)]
fn add<const N:usize>(dst:&mut[u64],b:&[u64],word:u64)->(out:u64)
    requires old(dst)@.len()==N,b@.len()==N,
    ensures final(dst)@.len()==N,
        value(final(dst)@)+radix(N as nat)*(out as int)
            ==value(old(dst)@)+(word as int)*value(b@),
{
    assert!(dst.len()==N && b.len()==N);
    let ghost original=dst@;
    let mut j=0usize;
    let mut carry=0u128;
    while j<N
        invariant dst@.len()==N,b@.len()==N,original.len()==N,j<=N,carry<=u64::MAX,
            forall|k:int| j<=k<N ==> #[trigger] dst@[k]==original[k],
            prefix(dst@,j as nat)+radix(j as nat)*(carry as int)
                ==prefix(original,j as nat)+(word as int)*prefix(b@,j as nat),
        decreases N-j,
    {
        let ghost before=dst@;
        let ghost incoming=carry;
        let (low,next)=wide(word,b[j],dst[j],carry);
        dst[j]=low;
        proof {
            equal_prefix(dst@,before,j as nat);
            mac_prefix_step(prefix(before,j as nat),prefix(original,j as nat),
                prefix(b@,j as nat),radix(j as nat),word as int,
                word as int,b@[j as int] as int,before[j as int] as int,
                incoming as int,low as int,next as int);
            assert((word as int)*prefix(b@,(j+1) as nat)
                ==(word as int)*prefix(b@,j as nat)
                    +(word as int)*(b@[j as int] as int)*radix(j as nat)) by(nonlinear_arith)
                requires prefix(b@,(j+1) as nat)==prefix(b@,j as nat)
                    +(b@[j as int] as int)*radix(j as nat);
        }
        carry=next;
        j+=1;
    }
    carry as u64
}

/// Exact full product. Const N enables inner-loop specialization without scratch.
#[inline(always)]
pub fn full<const N:usize>(dst:&mut[u64],a:&[u64],b:&[u64])
    requires 0<N<=usize::MAX/2,a@.len()==N,b@.len()==N,old(dst)@.len()==2*N,
    ensures final(dst)@.len()==old(dst)@.len(),value(final(dst)@)==value(a@)*value(b@),
{
    assert!(N>0 && N<=usize::MAX/2 && dst.len()==2*N && a.len()==N && b.len()==N);
    let carry=first::<N>(&mut dst[..N],b,a[0]);
    let ghost first_row=dst@;
    dst[N]=carry;
    proof {
        equal_prefix(dst@,first_row,N as nat);
        split(first_row,N as nat);
        assert(prefix(a@,0)==0);assert(radix(0)==1);
        assert(prefix(a@,1)==a@[0] as int);
        assert(prefix(dst@,(N+1) as nat)==prefix(a@,1)*value(b@)) by(nonlinear_arith)
            requires prefix(dst@,(N+1) as nat)==prefix(first_row,N as nat)+(carry as int)*radix(N as nat),
                prefix(first_row,N as nat)+radix(N as nat)*(carry as int)==(a@[0] as int)*value(b@),
                prefix(a@,1)==a@[0] as int;
    }
    let mut i=1usize;
    while i<N
        invariant dst@.len()==2*N,a@.len()==N,b@.len()==N,1<=i<=N,N<=usize::MAX/2,
            prefix(dst@,(N+i) as nat)==prefix(a@,i as nat)*value(b@),
        decreases N-i,
    {
        let ghost before=dst@;
        let carry=add::<N>(&mut dst[i..i+N],b,a[i]);
        let ghost middle=dst@;
        dst[i+N]=carry;
        proof {
            equal_prefix(dst@,middle,(i+N) as nat);
            segment_split(before,i as nat,(i+N) as nat);
            segment_split(middle,i as nat,(i+N) as nat);
            equal_prefix(before,middle,i as nat);radix_add(i as nat,N as nat);
            assert(prefix(middle,(i+N) as nat)+radix((i+N) as nat)*(carry as int)
                ==prefix(before,(i+N) as nat)+radix(i as nat)*(a@[i as int] as int)*value(b@))
                by(nonlinear_arith)
                requires part(middle,i as nat,(i+N) as nat)+radix(N as nat)*(carry as int)
                        ==part(before,i as nat,(i+N) as nat)+(a@[i as int] as int)*value(b@),
                    prefix(before,(i+N) as nat)==prefix(before,i as nat)+radix(i as nat)*part(before,i as nat,(i+N) as nat),
                    prefix(middle,(i+N) as nat)==prefix(before,i as nat)+radix(i as nat)*part(middle,i as nat,(i+N) as nat),
                    radix((i+N) as nat)==radix(i as nat)*radix(N as nat);
            assert(prefix(dst@,(i+N+1) as nat)==prefix(a@,(i+1) as nat)*value(b@)) by(nonlinear_arith)
                requires prefix(dst@,(i+N+1) as nat)==prefix(middle,(i+N) as nat)+(carry as int)*radix((i+N) as nat),
                    prefix(middle,(i+N) as nat)+radix((i+N) as nat)*(carry as int)
                        ==prefix(before,(i+N) as nat)+radix(i as nat)*(a@[i as int] as int)*value(b@),
                    prefix(before,(i+N) as nat)==prefix(a@,i as nat)*value(b@),
                    prefix(a@,(i+1) as nat)==prefix(a@,i as nat)+(a@[i as int] as int)*radix(i as nat);
        }
        i+=1;
    }
}
} // verus!

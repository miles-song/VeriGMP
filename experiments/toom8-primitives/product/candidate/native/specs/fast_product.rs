//! Arithmetic identities and slice interpretation for allocation-free fast products.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
use crate::product::*;
verus! {

pub open spec fn part(a: Seq<u64>, lo: nat, hi: nat) -> int {
    value(a.subrange(lo as int, hi as int))
}
pub open spec fn extended(a: Seq<u64>, n: nat) -> int {
    prefix(a, if n < a.len() { n } else { a.len() })
}
pub open spec fn digit(a: Seq<u64>, i: nat) -> int {
    if i < a.len() { a[i as int] as int } else { 0 }
}
pub proof fn extended_step(a: Seq<u64>, i: nat)
    ensures extended(a,i+1) == extended(a,i) + digit(a,i)*radix(i),
{}

pub proof fn split(a: Seq<u64>, k: nat)
    requires k <= a.len(),
    ensures value(a) == part(a,0,k) + radix(k)*part(a,k,a.len()),
        part(a,0,k)==prefix(a,k),
{
    equal_prefix(a,a.subrange(0,k as int),k);
    subrange_value(a,k,(a.len()-k) as nat);
}

pub proof fn segment_split(a:Seq<u64>, k:nat, end:nat)
    requires k<=end<=a.len(),
    ensures prefix(a,end)==prefix(a,k)+radix(k)*part(a,k,end),
{
    subrange_value(a,k,(end-k) as nat);
    equal_prefix(a.subrange(k as int,a.len() as int),a.subrange(k as int,end as int),(end-k) as nat);
}

pub proof fn prefix_frame(before: Seq<u64>, after: Seq<u64>, k: nat)
    requires before.len()==after.len(), k<=before.len(),
        forall|j:int| k<=j<before.len() ==> before[j]==after[j],
    ensures value(after)-value(before)==prefix(after,k)-prefix(before,k),
{
    split(before,k); split(after,k);
    assert(before.subrange(k as int,before.len() as int) =~= after.subrange(k as int,after.len() as int));
}

pub proof fn congruent_suffix(before: Seq<u64>, after: Seq<u64>, k: nat, delta: int)
    requires before.len()==after.len(), k<=before.len(),
        forall|j:int| 0<=j<k ==> before[j]==after[j],
        part(after,k,after.len()) == (part(before,k,before.len())+delta)%radix((before.len()-k) as nat),
    ensures value(after)==(value(before)+radix(k)*delta)%radix(before.len()),
{
    let len=(before.len()-k) as nat;
    split(before,k); split(after,k); equal_prefix(before,after,k);
    radix_add(k,len); radix_positive(len); radix_positive(k);
    prefix_range(after,after.len());
    let x=part(before,k,before.len())+delta;
    lemma_fundamental_div_mod(x,radix(len));
    let q=x/radix(len);
    assert(value(before)+radix(k)*delta == q*radix(before.len())+value(after))
        by(nonlinear_arith)
        requires value(before)==prefix(before,k)+radix(k)*part(before,k,before.len()),
            value(after)==prefix(before,k)+radix(k)*part(after,k,after.len()),
            x==part(before,k,before.len())+delta,
            x==radix(len)*q+part(after,k,after.len()),
            radix(before.len())==radix(k)*radix(len);
    lemma_fundamental_div_mod_converse(value(before)+radix(k)*delta,radix(before.len()),q,value(after));
}

pub proof fn karatsuba_identity(a0:int,a1:int,b0:int,b1:int,r:int)
    ensures (a0+r*a1)*(b0+r*b1)
        == a0*b0+r*(a0*b0+a1*b1-(a0-a1)*(b0-b1))+r*r*a1*b1,
        (a0+r*a1)*(b0+r*b1)==a0*b0+r*(a0*b1+a1*b0)+(r*r)*(a1*b1),
{
    broadcast use group_mul_is_commutative_and_distributive;
    assert(a0*b0+a1*b1-(a0-a1)*(b0-b1)==a0*b1+a1*b0);
    lemma_mul_is_associative(r,a1,b0);
    lemma_mul_is_associative(r,b1,a0);
    lemma_mul_is_associative(r,a1,r*b1);
    lemma_mul_is_associative(a1,r,b1);
    lemma_mul_is_associative(r,r*a1,b1);
    lemma_mul_is_associative(r,r,a1);
    lemma_mul_is_associative(r*r,a1,b1);
}

pub proof fn low_identity(a:Seq<u64>,b:Seq<u64>,k:nat,h:nat,z0:int,c1:int,c2:int)
    requires a.len()==b.len(), a.len()==k+h, h<=k,
        z0==part(a,0,k)*part(b,0,k),
        c1==(part(a,k,a.len())*part(b,0,h))%radix(h),
        c2==(part(a,0,h)*part(b,k,b.len()))%radix(h),
    ensures (value(a)*value(b))%radix(a.len())==(z0+radix(k)*(c1+c2))%radix(a.len()),
{
    split(a,k);split(b,k);segment_split(a,h,k);segment_split(b,h,k);
    split(a,h);split(b,h);radix_add(k,h);radix_add(h,(k-h) as nat);
    radix_positive(h);radix_positive(a.len());
    let a0=part(a,0,k);let a1=part(a,k,a.len());
    let b0=part(b,0,k);let b1=part(b,k,b.len());
    let al=part(a,0,h);let bl=part(b,0,h);
    let at=part(a,h,k);let bt=part(b,h,k);
    let r=radix(k);let s=radix(h);let d=radix((k-h) as nat);
    let q1=a1*bl/s;let q2=al*b1/s;
    lemma_fundamental_div_mod(a1*bl,s);lemma_fundamental_div_mod(al*b1,s);
    assert(a1*b0+a0*b1==c1+c2+s*(q1+q2+a1*bt+at*b1)) by(nonlinear_arith)
        requires a0==al+s*at,b0==bl+s*bt,a1*bl==s*q1+c1,al*b1==s*q2+c2;
    let q=q1+q2+a1*bt+at*b1+d*a1*b1;
    karatsuba_identity(a0,a1,b0,b1,r);
    let qc=q1+q2+a1*bt+at*b1;
    let z2=a1*b1;
    assert(q==qc+d*z2) by(nonlinear_arith)
        requires q==q1+q2+a1*bt+at*b1+d*a1*b1,qc==q1+q2+a1*bt+at*b1,z2==a1*b1;
    assert(value(a)*value(b)==z0+r*(c1+c2+s*qc)+(r*r)*z2);
    assert(value(a)*value(b)==z0+r*(c1+c2)+radix(a.len())*q) by(nonlinear_arith)
        requires value(a)*value(b)==z0+r*(c1+c2+s*qc)+(r*r)*z2,
            radix(a.len())==r*s,r==s*d,q==qc+d*z2;
    lemma_mod_multiples_basic(q,radix(a.len()));
    lemma_add_mod_noop(z0+r*(c1+c2),radix(a.len())*q,radix(a.len()));
    lemma_mod_twice(z0+r*(c1+c2),radix(a.len()));
}

pub proof fn prefix_mod(a:Seq<u64>,n:nat)
    requires n<=a.len(),
    ensures part(a,0,n)==value(a)%radix(n),
{
    split(a,n);prefix_range(a,n);radix_positive(n);
    assert(value(a)==part(a,n,a.len())*radix(n)+part(a,0,n)) by(nonlinear_arith)
        requires value(a)==part(a,0,n)+radix(n)*part(a,n,a.len());
    lemma_fundamental_div_mod_converse(value(a),radix(n),part(a,n,a.len()),part(a,0,n));
}

pub proof fn mod_add_scaled(x:int,c:int,r:int,s:int)
    requires r>0,s>0,
    ensures ((x%(r*s))+r*c)%(r*s)==(x+r*c)%(r*s),
{
    lemma_mul_strictly_positive(r,s);lemma_add_mod_noop_right(r*c,x,r*s);
}
} // verus!

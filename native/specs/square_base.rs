//! Independent diagonal/triangle identity for a schoolbook square.
use vstd::prelude::*;
use crate::radix::*;
use crate::product::*;
use vstd::arithmetic::div_mod::*;
verus! {
pub open spec fn triangle(a:Seq<u64>,n:nat)->int
    recommends n<=a.len(),
    decreases n,
{
    if n==0 {0} else {
        triangle(a,(n-1) as nat)+(a[n-1] as int)*prefix(a,(n-1) as nat)*radix((n-1) as nat)
    }
}
pub open spec fn diagonal(a:Seq<u64>,n:nat)->int
    recommends n<=a.len(),
    decreases n,
{
    if n==0 {0} else {
        diagonal(a,(n-1) as nat)+(a[n-1] as int)*(a[n-1] as int)*radix(2*((n-1) as nat))
    }
}
pub proof fn square_identity(a:Seq<u64>,n:nat)
    requires n<=a.len(),
    ensures prefix(a,n)*prefix(a,n)==2*triangle(a,n)+diagonal(a,n),
        triangle(a,n)>=0,diagonal(a,n)>=0,
    decreases n,
{
    if n>0 {
        let k=(n-1) as nat;
        square_identity(a,k);prefix_range(a,k);radix_positive(k);radix_add(k,k);
        assert(prefix(a,n)*prefix(a,n)==2*triangle(a,n)+diagonal(a,n)) by(nonlinear_arith)
            requires prefix(a,n)==prefix(a,k)+(a[k as int] as int)*radix(k),
                prefix(a,k)*prefix(a,k)==2*triangle(a,k)+diagonal(a,k),
                triangle(a,n)==triangle(a,k)+(a[k as int] as int)*prefix(a,k)*radix(k),
                diagonal(a,n)==diagonal(a,k)+(a[k as int] as int)*(a[k as int] as int)*radix(2*k),
                radix(2*k)==radix(k)*radix(k);
        assert(triangle(a,n)>=0 && diagonal(a,n)>=0) by(nonlinear_arith)
            requires triangle(a,k)>=0,diagonal(a,k)>=0,prefix(a,k)>=0,
                a[k as int]>=0,radix(k)>0,radix(2*k)==radix(k)*radix(k),
                triangle(a,n)==triangle(a,k)+(a[k as int] as int)*prefix(a,k)*radix(k),
                diagonal(a,n)==diagonal(a,k)+(a[k as int] as int)*(a[k as int] as int)*radix(2*k);
    }
}

pub proof fn diagonal_drop_high(a:Seq<u64>,cut:nat,total:nat,words:nat)
    requires cut<=total<=a.len(),2*cut>=words,
    ensures diagonal(a,total)%radix(words)==diagonal(a,cut)%radix(words),
    decreases total-cut,
{
    radix_positive(words);
    if total>cut {
        let k=(total-1) as nat;
        diagonal_drop_high(a,cut,k,words);
        radix_add(words,(2*k-words) as nat);
        let q=(a[k as int] as int)*(a[k as int] as int)*radix((2*k-words) as nat);
        assert(diagonal(a,total)==radix(words)*q+diagonal(a,k)) by(nonlinear_arith)
            requires diagonal(a,total)==diagonal(a,k)+(a[k as int] as int)*(a[k as int] as int)*radix(2*k),
                radix(2*k)==radix(words)*radix((2*k-words) as nat),
                q==(a[k as int] as int)*(a[k as int] as int)*radix((2*k-words) as nat);
        lemma_mod_multiples_vanish(q,diagonal(a,k),radix(words));
    }
}
}

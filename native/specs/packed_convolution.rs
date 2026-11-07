//! Exact finite convolution and Kronecker packing, independent of runtime outputs.
//! All objects in this module are erased mathematical specifications or proofs.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::power::*;
use vstd::arithmetic::mul::*;
use crate::radix::{radix, radix_is_power_of_two, value, prefix, equal_prefix};
use crate::product::subrange_value;

verus! {

pub open spec fn power(b: int, n: nat) -> int
    decreases n,
{
    if n == 0 { 1 } else { b * power(b, (n - 1) as nat) }
}

/// The mathematical integer represented by the first n coefficients in radix b.
pub open spec fn packed_prefix(a: Seq<int>, b: int, n: nat) -> int
    recommends n <= a.len(),
    decreases n,
{
    if n == 0 { 0 } else {
        packed_prefix(a, b, (n - 1) as nat) + a[n - 1] * power(b, (n - 1) as nat)
    }
}

pub open spec fn packed(a: Seq<int>, b: int) -> int { packed_prefix(a, b, a.len()) }

pub open spec fn canonical(a: Seq<int>, m: int) -> bool {
    forall|i: int| 0 <= i < a.len() ==> 0 <= #[trigger] a[i] < m
}

pub open spec fn term(a: Seq<int>, c: Seq<int>, k: nat, i: nat) -> int {
    if i < a.len() && i <= k && k - i < c.len() { a[i as int] * c[(k - i) as int] }
    else { 0 }
}

/// The finite sum over input indices i<n of a_i*c_(k-i), with zero extension.
pub open spec fn convolution_prefix(a: Seq<int>, c: Seq<int>, k: nat, n: nat) -> int
    recommends n <= a.len(),
    decreases n,
{
    if n == 0 { 0 } else {
        convolution_prefix(a, c, k, (n - 1) as nat) + term(a, c, k, (n - 1) as nat)
    }
}

pub open spec fn coefficient(a: Seq<int>, c: Seq<int>, k: nat) -> int {
    convolution_prefix(a, c, k, a.len())
}

/// A harmless final zero slot avoids subtracting one in the empty-input case.
pub open spec fn convolution(a: Seq<int>, c: Seq<int>) -> Seq<int> {
    Seq::new(a.len() + c.len(), |k: int| coefficient(a, c, k as nat))
}

pub open spec fn retained(a: Seq<int>, d: nat) -> Seq<int> {
    a.take(if d < a.len() { d as int } else { a.len() as int })
}

pub open spec fn shorter(a: Seq<int>, c: Seq<int>) -> nat {
    if a.len() < c.len() { a.len() } else { c.len() }
}

/// Cardinality of [0,n) intersect [max(0,k+1-len),k+1).
pub open spec fn overlap(k: nat, len: nat, n: nat) -> nat {
    let hi = if n < k + 1 { n } else { k + 1 };
    let lo = if k + 1 > len { (k + 1 - len) as nat } else { 0 };
    (hi - if n < lo { n } else { lo }) as nat
}

pub proof fn overlap_step(k: nat, len: nat, n: nat)
    ensures
        overlap(k, len, n) <= n,
        overlap(k, len, n) <= len,
        overlap(k, len, n + 1) == overlap(k, len, n)
            + if n <= k && k - n < len { 1nat } else { 0nat },
{}

pub proof fn coefficient_bound(a: Seq<int>, c: Seq<int>, m: int, k: nat, n: nat)
    requires m >= 1, canonical(a, m), canonical(c, m), n <= a.len(),
    ensures 0 <= convolution_prefix(a, c, k, n)
        <= overlap(k, c.len(), n) * ((m - 1) * (m - 1)),
    decreases n,
{
    assert((m - 1) * (m - 1) >= 0) by(nonlinear_arith);
    if n > 0 {
        let i = (n - 1) as nat;
        coefficient_bound(a, c, m, k, i);
        overlap_step(k, c.len(), i);
        if i <= k && k - i < c.len() {
            assert(0 <= a[i as int] < m);
            assert(0 <= c[(k - i) as int] < m);
            assert(0 <= term(a,c,k,i) <= (m-1)*(m-1)) by(nonlinear_arith)
                requires 0 <= a[i as int] < m, 0 <= c[(k-i) as int] < m,
                    term(a,c,k,i) == a[i as int] * c[(k-i) as int], m >= 1;
            assert(overlap(k,c.len(),n)*((m-1)*(m-1))
                == overlap(k,c.len(),i)*((m-1)*(m-1)) + (m-1)*(m-1)) by(nonlinear_arith)
                requires overlap(k,c.len(),n)==overlap(k,c.len(),i)+1;
        }
    }
}

pub proof fn no_carry_bound(a: Seq<int>, c: Seq<int>, m: int, b: int, k: nat)
    requires m >= 1, canonical(a,m), canonical(c,m), b > 0,
        b >= shorter(a,c) * m * m,
    ensures 0 <= coefficient(a,c,k) < b,
{
    coefficient_bound(a,c,m,k,a.len());
    overlap_step(k,c.len(),a.len());
    let l = shorter(a,c);
    assert(overlap(k,c.len(),a.len()) <= l);
    assert(coefficient(a,c,k) <= l*((m-1)*(m-1))) by(nonlinear_arith)
        requires coefficient(a,c,k) <= overlap(k,c.len(),a.len())*((m-1)*(m-1)),
            overlap(k,c.len(),a.len()) <= l, (m-1)*(m-1) >= 0;
    if l > 0 {
        assert(l*((m-1)*(m-1)) < l*m*m) by(nonlinear_arith)
            requires l>0, m>=1;
        assert(b>=l*m*m);
    } else {
        assert(l*((m-1)*(m-1))==0) by(nonlinear_arith) requires l==0;
    }
}

pub proof fn power_positive(b: int, n: nat)
    requires b > 0,
    ensures power(b,n) > 0,
    decreases n,
{
    if n > 0 {
        power_positive(b,(n-1) as nat);
        assert(b*power(b,(n-1) as nat)>0) by(nonlinear_arith)
            requires b>0, power(b,(n-1) as nat)>0;
    }
}

pub proof fn power_add(b: int, i: nat, j: nat)
    ensures power(b,i+j)==power(b,i)*power(b,j),
    decreases j,
{
    if j>0 {
        power_add(b,i,(j-1) as nat);
        assert(power(b,i+j)==power(b,i)*power(b,j)) by(nonlinear_arith)
            requires power(b,i+j)==b*power(b,(i+j-1) as nat),
                power(b,(i+j-1) as nat)==power(b,i)*power(b,(j-1) as nat),
                power(b,j)==b*power(b,(j-1) as nat);
    }
}

/// Weighted sum of one shifted row of the double finite sum.
pub open spec fn row(a: Seq<int>, c: Seq<int>, b: int, i: nat, t: nat) -> int
    decreases t,
{
    if t==0 { 0 } else {
        row(a,c,b,i,(t-1) as nat) + term(a,c,(t-1) as nat,i)*power(b,(t-1) as nat)
    }
}

pub proof fn row_identity(a: Seq<int>, c: Seq<int>, b: int, i: nat, t: nat)
    requires i<a.len(),
    ensures row(a,c,b,i,t)==a[i as int]*power(b,i)*packed_prefix(c,b,
        if t<=i {0} else if t-i<c.len() {(t-i) as nat} else {c.len()}),
    decreases t,
{
    if t>0 {
        row_identity(a,c,b,i,(t-1) as nat);
        if i<t && t-i<=c.len() {
            let j=(t-1-i) as nat;
            power_add(b,i,j);
            let x=a[i as int]; let y=c[j as int];
            let r=power(b,i); let s=power(b,j);
            lemma_mul_is_associative(x,y,r*s);
            lemma_mul_is_associative(y,r,s);
            lemma_mul_is_commutative(y,r);
            lemma_mul_is_associative(r,y,s);
            lemma_mul_is_associative(x,r,y*s);
            lemma_mul_is_associative(x*r,y,s);
            assert((x*y)*(r*s)==(x*r)*(y*s));
            assert(term(a,c,(t-1) as nat,i)*power(b,(t-1) as nat)==(x*r)*(y*s));
            lemma_mul_is_distributive_add(x*r,packed_prefix(c,b,j),y*s);
            assert(row(a,c,b,i,(t-1) as nat)==(x*r)*packed_prefix(c,b,j));
            assert(packed_prefix(c,b,(t-i) as nat)==packed_prefix(c,b,j)+y*s);
            assert(row(a,c,b,i,t)==row(a,c,b,i,(t-1) as nat)
                +term(a,c,(t-1) as nat,i)*power(b,(t-1) as nat));
            assert(row(a,c,b,i,t)==(x*r)*packed_prefix(c,b,(t-i) as nat));
        } else {
            assert(term(a,c,(t-1) as nat,i)==0);
        }
    }
}

pub open spec fn weighted(a: Seq<int>, c: Seq<int>, b: int, n: nat, t: nat) -> int
    recommends n<=a.len(),
    decreases t,
{
    if t==0 {0} else {
        weighted(a,c,b,n,(t-1) as nat)
            +convolution_prefix(a,c,(t-1) as nat,n)*power(b,(t-1) as nat)
    }
}

pub proof fn weighted_step(a: Seq<int>, c: Seq<int>, b: int, n: nat, t: nat)
    requires n<a.len(),
    ensures weighted(a,c,b,n+1,t)==weighted(a,c,b,n,t)+row(a,c,b,n,t),
    decreases t,
{
    if t>0 {
        weighted_step(a,c,b,n,(t-1) as nat);
        assert(weighted(a,c,b,n+1,t)==weighted(a,c,b,n,t)+row(a,c,b,n,t))
            by(nonlinear_arith)
            requires weighted(a,c,b,n+1,(t-1) as nat)
                    ==weighted(a,c,b,n,(t-1) as nat)+row(a,c,b,n,(t-1) as nat),
                convolution_prefix(a,c,(t-1) as nat,n+1)
                    ==convolution_prefix(a,c,(t-1) as nat,n)+term(a,c,(t-1) as nat,n),
                weighted(a,c,b,n+1,t)==weighted(a,c,b,n+1,(t-1) as nat)
                    +convolution_prefix(a,c,(t-1) as nat,n+1)*power(b,(t-1) as nat),
                weighted(a,c,b,n,t)==weighted(a,c,b,n,(t-1) as nat)
                    +convolution_prefix(a,c,(t-1) as nat,n)*power(b,(t-1) as nat),
                row(a,c,b,n,t)==row(a,c,b,n,(t-1) as nat)
                    +term(a,c,(t-1) as nat,n)*power(b,(t-1) as nat);
    }
}

pub proof fn weighted_zero(a: Seq<int>, c: Seq<int>, b: int, t: nat)
    ensures weighted(a,c,b,0,t)==0,
    decreases t,
{
    if t>0 {weighted_zero(a,c,b,(t-1) as nat);}
}

pub proof fn weighted_product(a: Seq<int>, c: Seq<int>, b: int, n: nat, t: nat)
    requires n<=a.len(), t>=n+c.len(),
    ensures weighted(a,c,b,n,t)==packed_prefix(a,b,n)*packed(c,b),
    decreases n,
{
    if n==0 {weighted_zero(a,c,b,t);}
    else {
        let i=(n-1) as nat;
        weighted_product(a,c,b,i,t);
        weighted_step(a,c,b,i,t);
        row_identity(a,c,b,i,t);
        assert(weighted(a,c,b,n,t)==packed_prefix(a,b,n)*packed(c,b)) by(nonlinear_arith)
            requires weighted(a,c,b,i,t)==packed_prefix(a,b,i)*packed(c,b),
                weighted(a,c,b,n,t)==weighted(a,c,b,i,t)+row(a,c,b,i,t),
                row(a,c,b,i,t)==a[i as int]*power(b,i)*packed(c,b),
                packed_prefix(a,b,n)==packed_prefix(a,b,i)+a[i as int]*power(b,i);
    }
}

pub proof fn packed_convolution_prefix(a: Seq<int>, c: Seq<int>, b: int, t: nat)
    requires t<=a.len()+c.len(),
    ensures packed_prefix(convolution(a,c),b,t)==weighted(a,c,b,a.len(),t),
    decreases t,
{
    if t>0 {packed_convolution_prefix(a,c,b,(t-1) as nat);}
}

/// Polynomial multiplication evaluated at b, with no coefficient range premise.
pub proof fn convolution_product(a: Seq<int>, c: Seq<int>, b: int)
    ensures packed(convolution(a,c),b)==packed(a,b)*packed(c,b),
{
    weighted_product(a,c,b,a.len(),a.len()+c.len());
    packed_convolution_prefix(a,c,b,a.len()+c.len());
}

pub proof fn packed_range(a: Seq<int>, b: int, n: nat)
    requires b>0, canonical(a,b), n<=a.len(),
    ensures 0<=packed_prefix(a,b,n)<power(b,n),
    decreases n,
{
    if n>0 {
        packed_range(a,b,(n-1) as nat);
        power_positive(b,(n-1) as nat);
        assert(0<=a[n-1]<b);
        assert(0<=packed_prefix(a,b,n)<power(b,n)) by(nonlinear_arith)
            requires 0<=packed_prefix(a,b,(n-1) as nat)<power(b,(n-1) as nat),
                power(b,(n-1) as nat)>0, 0<=a[n-1]<b,
                packed_prefix(a,b,n)==packed_prefix(a,b,(n-1) as nat)+a[n-1]*power(b,(n-1) as nat),
                power(b,n)==b*power(b,(n-1) as nat);
    }
}

pub open spec fn packed_suffix(a: Seq<int>, b: int, start: nat) -> int
    recommends start<=a.len(),
    decreases a.len()-start,
{
    if start>=a.len() {0} else {a[start as int]+b*packed_suffix(a,b,start+1)}
}

pub proof fn packed_split(a: Seq<int>, b: int, start: nat)
    requires start<=a.len(),
    ensures packed(a,b)==packed_prefix(a,b,start)+power(b,start)*packed_suffix(a,b,start),
    decreases a.len()-start,
{
    if start<a.len() {
        packed_split(a,b,start+1);
        assert(packed(a,b)==packed_prefix(a,b,start)+power(b,start)*packed_suffix(a,b,start))
            by(nonlinear_arith)
            requires packed(a,b)==packed_prefix(a,b,start+1)+power(b,start+1)*packed_suffix(a,b,start+1),
                packed_prefix(a,b,start+1)==packed_prefix(a,b,start)+a[start as int]*power(b,start),
                power(b,start+1)==b*power(b,start),
                packed_suffix(a,b,start)==a[start as int]+b*packed_suffix(a,b,start+1);
    }
}

pub proof fn extract_digit(a: Seq<int>, b: int, k: nat)
    requires b>0, canonical(a,b), k<a.len(),
    ensures (packed(a,b)/power(b,k))%b==a[k as int],
{
    packed_split(a,b,k);
    packed_range(a,b,k);
    power_positive(b,k);
    lemma_fundamental_div_mod_converse(packed(a,b),power(b,k),packed_suffix(a,b,k),packed_prefix(a,b,k));
    assert(0<=a[k as int]<b);
    assert(packed_suffix(a,b,k)==packed_suffix(a,b,k+1)*b+a[k as int]) by(nonlinear_arith)
        requires packed_suffix(a,b,k)==a[k as int]+b*packed_suffix(a,b,k+1);
    lemma_fundamental_div_mod_converse(packed_suffix(a,b,k),b,packed_suffix(a,b,k+1),a[k as int]);
}

/// Arbitrary finite lengths and precision: no carry between the full product's slots.
pub proof fn packed_convolution_extract(a: Seq<int>, c: Seq<int>, m: int, b: int, k: nat)
    requires m>=1, canonical(a,m), canonical(c,m), b>0,
        b>=shorter(a,c)*m*m, k<a.len()+c.len(),
    ensures
        (packed(a,b)*packed(c,b)/power(b,k))%b==coefficient(a,c,k),
        ((packed(a,b)*packed(c,b)/power(b,k))%b)%m==coefficient(a,c,k)%m,
{
    assert forall|j:int| 0<=j<convolution(a,c).len()
        implies 0<=#[trigger] convolution(a,c)[j]<b by {
        no_carry_bound(a,c,m,b,j as nat);
    }
    convolution_product(a,c,b);
    extract_digit(convolution(a,c),b,k);
}

/// If m divides the radix, residue extraction can bypass the guard-bit remainder.
pub proof fn packed_convolution_residue(a: Seq<int>, c: Seq<int>, m: int, b: int, k: nat)
    requires m>=1, canonical(a,m), canonical(c,m), b>0, b%m==0,
        b>=shorter(a,c)*m*m, k<a.len()+c.len(),
    ensures (packed(a,b)*packed(c,b)/power(b,k))%m==coefficient(a,c,k)%m,
{
    packed_convolution_extract(a,c,m,b,k);
    let x=packed(a,b)*packed(c,b)/power(b,k);
    lemma_fundamental_div_mod(x,b);
    lemma_fundamental_div_mod(b,m);
    let q=(b/m)*(x/b);
    assert(x==coefficient(a,c,k)+q*m) by(nonlinear_arith)
        requires x==b*(x/b)+coefficient(a,c,k), b==m*(b/m), q==(b/m)*(x/b);
    lemma_mod_multiples_basic(q,m);
    lemma_add_mod_noop(coefficient(a,c,k),q*m,m);
    lemma_mod_twice(coefficient(a,c,k),m);
}

/// The guard budget uses input precision p and an upper power-of-two bound 2^g
/// on the shorter input length; it does not change any coefficient's meaning.
pub proof fn guard_bits(a: Seq<int>, c: Seq<int>, p: nat, g: nat, w: nat)
    requires p>0, shorter(a,c)<=pow(2,g), w>=2*p+g,
    ensures pow(2,w)>0, pow(2,p)>=1,
        pow(2,w)>=shorter(a,c)*pow(2,p)*pow(2,p),
{
    lemma_pow_positive(2,w);
    lemma_pow_positive(2,p);
    lemma_pow_positive(2,g);
    lemma_pow_positive(2,(w-2*p-g) as nat);
    lemma_pow_adds(2,p,p);
    lemma_pow_adds(2,2*p,g);
    lemma_pow_adds(2,2*p+g,(w-2*p-g) as nat);
    assert(pow(2,w)>=shorter(a,c)*pow(2,p)*pow(2,p)) by(nonlinear_arith)
        requires pow(2,w)==pow(2,2*p+g)*pow(2,(w-2*p-g) as nat),
            pow(2,2*p+g)==pow(2,2*p)*pow(2,g),
            pow(2,2*p)==pow(2,p)*pow(2,p),
            pow(2,(w-2*p-g) as nat)>=1, pow(2,p)>=1, pow(2,g)>=1,
            shorter(a,c)<=pow(2,g);
}

pub proof fn word_aligned_guard(a: Seq<int>, c: Seq<int>, p: nat, g: nat, slot_limbs: nat)
    requires p>0, shorter(a,c)<=pow(2,g), 64*slot_limbs>=2*p+g,
    ensures radix(slot_limbs)>0,
        radix(slot_limbs)>=shorter(a,c)*pow(2,p)*pow(2,p),
{
    radix_is_power_of_two(slot_limbs);
    guard_bits(a,c,p,g,64*slot_limbs);
}

pub proof fn power_of_two_divides(p: nat, w: nat)
    requires p<=w,
    ensures pow(2,w)%pow(2,p)==0,
{
    lemma_pow_positive(2,p);
    lemma_pow_adds(2,p,(w-p) as nat);
    lemma_mod_multiples_basic(pow(2,(w-p) as nat),pow(2,p));
}

/// Input truncation preserves every output coefficient below the requested order.
pub proof fn truncate_prefix(a: Seq<int>, c: Seq<int>, d: nat, k: nat, n: nat)
    requires k<d, n<=a.len(),
    ensures convolution_prefix(a,c,k,n)==convolution_prefix(retained(a,d),retained(c,d),k,
        if n<d {n} else {d}),
    decreases n,
{
    if n>0 {
        let i=(n-1) as nat;
        truncate_prefix(a,c,d,k,i);
        if n<=d {
            assert(term(a,c,k,i)==term(retained(a,d),retained(c,d),k,i));
        } else {
            assert(term(a,c,k,i)==0);
        }
    }
}

pub proof fn truncate_coefficient(a: Seq<int>, c: Seq<int>, d: nat, k: nat)
    requires k<d,
    ensures coefficient(a,c,k)==coefficient(retained(a,d),retained(c,d),k),
{
    truncate_prefix(a,c,d,k,a.len());
}

/// A complete finite-order extraction entry for canonical input coefficients.
/// Beyond the retained product support, coefficient_zero supplies zero padding.
pub proof fn truncated_extract(a: Seq<int>, c: Seq<int>, p: nat, g: nat, w: nat, d: nat, k: nat)
    requires p>0, canonical(a,pow(2,p)), canonical(c,pow(2,p)),
        shorter(retained(a,d),retained(c,d))<=pow(2,g), w>=2*p+g,
        k<d, k<retained(a,d).len()+retained(c,d).len(),
    ensures (packed(retained(a,d),pow(2,w))*packed(retained(c,d),pow(2,w))
        /power(pow(2,w),k))%pow(2,p)==coefficient(a,c,k)%pow(2,p),
{
    assert(canonical(retained(a,d),pow(2,p)));
    assert(canonical(retained(c,d),pow(2,p)));
    guard_bits(retained(a,d),retained(c,d),p,g,w);
    power_of_two_divides(p,w);
    packed_convolution_residue(retained(a,d),retained(c,d),pow(2,p),pow(2,w),k);
    truncate_coefficient(a,c,d,k);
}

pub proof fn coefficient_zero(a: Seq<int>, c: Seq<int>, k: nat, n: nat)
    requires n<=a.len(), k+1>=n+c.len(),
    ensures convolution_prefix(a,c,k,n)==0,
    decreases n,
{
    if n>0 {
        coefficient_zero(a,c,k,(n-1) as nat);
        assert(term(a,c,k,(n-1) as nat)==0);
    }
}

/// Empty operands and D=0 have zero packed product, with no positive-L premise.
pub proof fn empty_product(a: Seq<int>, c: Seq<int>, d: nat, b: int)
    requires a.len()==0 || c.len()==0 || d==0,
    ensures packed(retained(a,d),b)*packed(retained(c,d),b)==0,
{}

/// Interpretation of contiguous little-endian limb slots; no allocation is
/// required of an implementation using this erased representation relation.
pub open spec fn slots(words: Seq<u64>, slot_limbs: nat, count: nat) -> Seq<int>
    recommends count*slot_limbs<=words.len(),
{
    Seq::new(count, |i:int| value(words.subrange(i*slot_limbs,(i+1)*slot_limbs)))
}

pub proof fn slot_power(slot_limbs: nat, n: nat)
    ensures power(radix(slot_limbs),n)==radix(slot_limbs*n),
    decreases n,
{
    if n>0 {
        slot_power(slot_limbs,(n-1) as nat);
        crate::product::radix_add(slot_limbs*((n-1) as nat),slot_limbs);
        assert(slot_limbs*n==slot_limbs*((n-1) as nat)+slot_limbs) by(nonlinear_arith)
            requires n>0;
        assert(power(radix(slot_limbs),n)==radix(slot_limbs*n)) by(nonlinear_arith)
            requires power(radix(slot_limbs),n)==radix(slot_limbs)*power(radix(slot_limbs),(n-1) as nat),
                power(radix(slot_limbs),(n-1) as nat)==radix(slot_limbs*((n-1) as nat)),
                radix(slot_limbs*n)==radix(slot_limbs*((n-1) as nat))*radix(slot_limbs);
    } else {
        assert(slot_limbs*n==0) by(nonlinear_arith) requires n==0;
        assert(radix(0)==1);
    }
}

/// alpha_slots followed by polynomial packing is exactly the limb integer.
pub proof fn slots_prefix(words: Seq<u64>, slot_limbs: nat, count: nat, n: nat)
    requires count*slot_limbs<=words.len(), n<=count,
    ensures packed_prefix(slots(words,slot_limbs,count),radix(slot_limbs),n)
        ==prefix(words,n*slot_limbs),
    decreases n,
{
    if n>0 {
        let start=slot_limbs*((n-1) as nat);
        slots_prefix(words,slot_limbs,count,(n-1) as nat);
        assert(((n-1) as nat)*slot_limbs==start) by(nonlinear_arith)
            requires start==slot_limbs*((n-1) as nat);
        slot_power(slot_limbs,(n-1) as nat);
        assert(n*slot_limbs==start+slot_limbs) by(nonlinear_arith)
            requires n>0, start==slot_limbs*((n-1) as nat);
        assert(start+slot_limbs<=words.len()) by(nonlinear_arith)
            requires n<=count, count*slot_limbs<=words.len(), start+slot_limbs==n*slot_limbs;
        subrange_value(words,start,slot_limbs);
        equal_prefix(words.subrange(start as int,words.len() as int),
            words.subrange(start as int,(start+slot_limbs) as int),slot_limbs);
        assert(packed_prefix(slots(words,slot_limbs,count),radix(slot_limbs),n)
            ==prefix(words,n*slot_limbs)) by(nonlinear_arith)
            requires packed_prefix(slots(words,slot_limbs,count),radix(slot_limbs),(n-1) as nat)
                    ==prefix(words,start),
                packed_prefix(slots(words,slot_limbs,count),radix(slot_limbs),n)
                    ==packed_prefix(slots(words,slot_limbs,count),radix(slot_limbs),(n-1) as nat)
                        +slots(words,slot_limbs,count)[n-1]*power(radix(slot_limbs),(n-1) as nat),
                power(radix(slot_limbs),(n-1) as nat)==radix(start),
                prefix(words,n*slot_limbs)==prefix(words,start)
                    +radix(start)*slots(words,slot_limbs,count)[n-1];
    } else {
        assert(n*slot_limbs==0) by(nonlinear_arith) requires n==0;
        assert(prefix(words,0)==0);
    }
}

pub proof fn slots_integer(words: Seq<u64>, slot_limbs: nat, count: nat)
    requires count*slot_limbs==words.len(),
    ensures packed(slots(words,slot_limbs,count),radix(slot_limbs))==value(words),
{
    slots_prefix(words,slot_limbs,count,count);
}

} // verus!

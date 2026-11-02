//! Seven-point Toom-4 polynomial meanings and exact interpolation obligations.
//! Coefficients are defined from input blocks, independently of executable output.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
verus! {
pub open spec fn eval(a:Seq<int>,x:int)->int recommends a.len()==4 {
    a[0]+x*a[1]+x*x*a[2]+x*x*x*a[3]
}
pub open spec fn half(a:Seq<int>)->int recommends a.len()==4 {
    8*a[0]+4*a[1]+2*a[2]+a[3]
}
pub open spec fn negative_half(a:Seq<int>)->int recommends a.len()==4 {
    8*a[0]-4*a[1]+2*a[2]-a[3]
}
pub open spec fn coefficients(a:Seq<int>,b:Seq<int>)->Seq<int>
    recommends a.len()==4,b.len()==4,
{
    seq![a[0]*b[0],a[0]*b[1]+a[1]*b[0],
        a[0]*b[2]+a[1]*b[1]+a[2]*b[0],
        a[0]*b[3]+a[1]*b[2]+a[2]*b[1]+a[3]*b[0],
        a[1]*b[3]+a[2]*b[2]+a[3]*b[1],a[2]*b[3]+a[3]*b[2],a[3]*b[3]]
}
pub open spec fn polynomial(c:Seq<int>,x:int)->int recommends c.len()==7 {
    c[0]+x*c[1]+x*x*c[2]+x*x*x*c[3]+x*x*x*x*c[4]+x*x*x*x*x*c[5]+x*x*x*x*x*x*c[6]
}
pub open spec fn one(c:Seq<int>)->int recommends c.len()==7 {
    c[0]+c[1]+c[2]+c[3]+c[4]+c[5]+c[6]
}
pub open spec fn negative(c:Seq<int>)->int recommends c.len()==7 {
    c[0]-c[1]+c[2]-c[3]+c[4]-c[5]+c[6]
}
pub open spec fn scaled_half(c:Seq<int>)->int recommends c.len()==7 {
    64*c[0]+32*c[1]+16*c[2]+8*c[3]+4*c[4]+2*c[5]+c[6]
}
pub open spec fn scaled_negative_half(c:Seq<int>)->int recommends c.len()==7 {
    64*c[0]-32*c[1]+16*c[2]-8*c[3]+4*c[4]-2*c[5]+c[6]
}
pub open spec fn two(c:Seq<int>)->int recommends c.len()==7 {
    c[0]+2*c[1]+4*c[2]+8*c[3]+16*c[4]+32*c[5]+64*c[6]
}

pub proof fn evaluation_forms(a:Seq<int>)
    requires a.len()==4,
    ensures eval(a,1)==a[0]+a[1]+a[2]+a[3],eval(a,-1)==a[0]-a[1]+a[2]-a[3],
        eval(a,2)==a[0]+2*a[1]+4*a[2]+8*a[3],
{
    lemma_mul_basics(a[1]);lemma_mul_basics(a[2]);lemma_mul_basics(a[3]);
    lemma_mul_is_distributive_sub_other_way(a[1],0,1);
    lemma_mul_is_distributive_sub_other_way(a[3],0,1);
    assert(2int*2==4 && 2int*2*2==8);
}

pub proof fn signed_product(a:int,b:int,x:int,y:int,na:bool,nb:bool)
    requires (if na{-a}else{a})==x,(if nb{-b}else{b})==y,
    ensures (if na!=nb{-(a*b)}else{a*b})==x*y,
{
    assert((if na!=nb{-(a*b)}else{a*b})==x*y) by(nonlinear_arith)
        requires (if na{-a}else{a})==x,(if nb{-b}else{b})==y;
}

pub proof fn evaluation_products(a:Seq<int>,b:Seq<int>)
    requires a.len()==4,b.len()==4,
    ensures coefficients(a,b).len()==7,
        eval(a,0)*eval(b,0)==coefficients(a,b)[0],
        a[3]*b[3]==coefficients(a,b)[6],
        eval(a,1)*eval(b,1)==one(coefficients(a,b)),
        eval(a,-1)*eval(b,-1)==negative(coefficients(a,b)),
        eval(a,2)*eval(b,2)==two(coefficients(a,b)),
        half(a)*half(b)==scaled_half(coefficients(a,b)),
        negative_half(a)*negative_half(b)==scaled_negative_half(coefficients(a,b)),
{
    let c=coefficients(a,b);
    recompose(a,b,1);recompose(a,b,-1);recompose(a,b,2);
    half_products(a[0],a[1],a[2],a[3],b[0],b[1],b[2],b[3]);
    lemma_mul_is_associative(64,a[0],b[0]);
    lemma_mul_basics(c[1]);lemma_mul_basics(c[2]);lemma_mul_basics(c[3]);lemma_mul_basics(c[4]);lemma_mul_basics(c[5]);
    lemma_mul_is_distributive_sub_other_way(c[1],0,1);
    lemma_mul_is_distributive_sub_other_way(c[3],0,1);
    lemma_mul_is_distributive_sub_other_way(c[5],0,1);
}

pub proof fn quad_product(a:int,b:int,c:int,d:int,e:int,f:int,g:int,h:int)
    ensures (a+b+c+d)*(e+f+g+h)==a*e+a*f+a*g+a*h+b*e+b*f+b*g+b*h+c*e+c*f+c*g+c*h+d*e+d*f+d*g+d*h,
{
    lemma_mul_is_distributive_add(a+b+c+d,e+f+g,h);
    lemma_mul_is_distributive_add(a+b+c+d,e+f,g);
    lemma_mul_is_distributive_add(a+b+c+d,e,f);
    lemma_mul_is_distributive_add_other_way(e,a+b+c,d);
    lemma_mul_is_distributive_add_other_way(e,a+b,c);
    lemma_mul_is_distributive_add_other_way(e,a,b);
    lemma_mul_is_distributive_add_other_way(f,a+b+c,d);
    lemma_mul_is_distributive_add_other_way(f,a+b,c);
    lemma_mul_is_distributive_add_other_way(f,a,b);
    lemma_mul_is_distributive_add_other_way(g,a+b+c,d);
    lemma_mul_is_distributive_add_other_way(g,a+b,c);
    lemma_mul_is_distributive_add_other_way(g,a,b);
    lemma_mul_is_distributive_add_other_way(h,a+b+c,d);
    lemma_mul_is_distributive_add_other_way(h,a+b,c);
    lemma_mul_is_distributive_add_other_way(h,a,b);
}
pub proof fn monomial_mul(x:int,y:int,p:int,q:int)
    ensures (p*x)*(q*y)==(p*q)*(x*y),
{
    lemma_mul_is_associative(p,x,q*y);
    lemma_mul_is_associative(x,q,y);
    lemma_mul_is_commutative(x,q);
    lemma_mul_is_associative(q,x,y);
    lemma_mul_is_associative(p,q,x*y);
}

pub proof fn half_products(a0:int,a1:int,a2:int,a3:int,b0:int,b1:int,b2:int,b3:int)
    ensures
        (8*a0+4*a1+2*a2+a3)*(8*b0+4*b1+2*b2+b3)==64*a0*b0+32*(a0*b1+a1*b0)
            +16*(a0*b2+a1*b1+a2*b0)+8*(a0*b3+a1*b2+a2*b1+a3*b0)
            +4*(a1*b3+a2*b2+a3*b1)+2*(a2*b3+a3*b2)+a3*b3,
        (8*a0-4*a1+2*a2-a3)*(8*b0-4*b1+2*b2-b3)==64*a0*b0-32*(a0*b1+a1*b0)
            +16*(a0*b2+a1*b1+a2*b0)-8*(a0*b3+a1*b2+a2*b1+a3*b0)
            +4*(a1*b3+a2*b2+a3*b1)-2*(a2*b3+a3*b2)+a3*b3,
{
    quad_product(8*a0,4*a1,2*a2,a3,8*b0,4*b1,2*b2,b3);
    monomial_mul(a0,b0,8,8);monomial_mul(a0,b1,8,4);monomial_mul(a0,b2,8,2);monomial_mul(a0,b3,8,1);
    monomial_mul(a1,b0,4,8);monomial_mul(a1,b1,4,4);monomial_mul(a1,b2,4,2);monomial_mul(a1,b3,4,1);
    monomial_mul(a2,b0,2,8);monomial_mul(a2,b1,2,4);monomial_mul(a2,b2,2,2);monomial_mul(a2,b3,2,1);
    monomial_mul(a3,b0,1,8);monomial_mul(a3,b1,1,4);monomial_mul(a3,b2,1,2);monomial_mul(a3,b3,1,1);
    lemma_mul_is_associative(64,a0,b0);
    quad_product(8*a0,-4*a1,2*a2,-a3,8*b0,-4*b1,2*b2,-b3);
    monomial_mul(a0,b0,8,8);monomial_mul(a0,b1,8,-4);monomial_mul(a0,b2,8,2);monomial_mul(a0,b3,8,-1);
    monomial_mul(a1,b0,-4,8);monomial_mul(a1,b1,-4,-4);monomial_mul(a1,b2,-4,2);monomial_mul(a1,b3,-4,-1);
    monomial_mul(a2,b0,2,8);monomial_mul(a2,b1,2,-4);monomial_mul(a2,b2,2,2);monomial_mul(a2,b3,2,-1);
    monomial_mul(a3,b0,-1,8);monomial_mul(a3,b1,-1,-4);monomial_mul(a3,b2,-1,2);monomial_mul(a3,b3,-1,-1);
}

pub proof fn recompose(a:Seq<int>,b:Seq<int>,r:int)
    requires a.len()==4,b.len()==4,
    ensures eval(a,r)*eval(b,r)==polynomial(coefficients(a,b),r),
{
    let a0=a[0];let a1=a[1];let a2=a[2];let a3=a[3];
    let b0=b[0];let b1=b[1];let b2=b[2];let b3=b[3];
    quad_product(a0,r*a1,r*r*a2,r*r*r*a3,b0,r*b1,r*r*b2,r*r*r*b3);
    monomial_mul(a0,b0,1,1);monomial_mul(a0,b1,1,r);monomial_mul(a0,b2,1,r*r);monomial_mul(a0,b3,1,r*r*r);
    monomial_mul(a1,b0,r,1);monomial_mul(a1,b1,r,r);monomial_mul(a1,b2,r,r*r);monomial_mul(a1,b3,r,r*r*r);
    monomial_mul(a2,b0,r*r,1);monomial_mul(a2,b1,r*r,r);monomial_mul(a2,b2,r*r,r*r);monomial_mul(a2,b3,r*r,r*r*r);
    monomial_mul(a3,b0,r*r*r,1);monomial_mul(a3,b1,r*r*r,r);monomial_mul(a3,b2,r*r*r,r*r);monomial_mul(a3,b3,r*r*r,r*r*r);
    lemma_mul_is_associative(r,r,r);
    lemma_mul_is_associative(r*r,r,r);
    lemma_mul_is_associative(r,r*r,r);
    lemma_mul_is_associative(r*r,r*r,r);
    lemma_mul_is_associative(r,r,r*r*r);
    lemma_mul_is_associative(r*r,r,r*r);
    lemma_mul_is_associative(r*r*r,r,r);
    lemma_mul_is_associative(r*r*r,r*r,r);
    lemma_mul_is_associative(r*r*r,r,r*r);
    lemma_mul_is_distributive_add(r,a0*b1,a1*b0);
    lemma_mul_is_distributive_add(r*r,a0*b2+a1*b1,a2*b0);
    lemma_mul_is_distributive_add(r*r,a0*b2,a1*b1);
    lemma_mul_is_distributive_add(r*r*r,a0*b3+a1*b2+a2*b1,a3*b0);
    lemma_mul_is_distributive_add(r*r*r,a0*b3+a1*b2,a2*b1);
    lemma_mul_is_distributive_add(r*r*r,a0*b3,a1*b2);
    lemma_mul_is_distributive_add(r*r*r*r,a1*b3+a2*b2,a3*b1);
    lemma_mul_is_distributive_add(r*r*r*r,a1*b3,a2*b2);
    lemma_mul_is_distributive_add(r*r*r*r*r,a2*b3,a3*b2);
}

pub proof fn evaluation_bounds(a:Seq<int>,r:int)
    requires a.len()==4,r>0,forall|i:int|0<=i<4 ==> 0<=#[trigger] a[i]<r,
    ensures 0<=eval(a,1)<4*r,-2*r<eval(a,-1)<2*r,
        0<=eval(a,2)<15*r,0<=half(a)<15*r,-5*r<negative_half(a)<10*r,
{
    assert(0<=a[0]<r && 0<=a[1]<r && 0<=a[2]<r && 0<=a[3]<r);
    lemma_mul_basics(a[1]);lemma_mul_basics(a[2]);lemma_mul_basics(a[3]);
    lemma_mul_is_distributive_sub_other_way(a[1],0,1);
    lemma_mul_is_distributive_sub_other_way(a[3],0,1);
    assert(2int*2==4 && 2int*2*2==8);
    assert(eval(a,2)==a[0]+2*a[1]+4*a[2]+8*a[3]);
}

pub proof fn coefficient_bounds(a:Seq<int>,b:Seq<int>,r:int)
    requires a.len()==4,b.len()==4,r>0,
        forall|i:int|0<=i<4 ==> 0<=#[trigger] a[i]<r,
        forall|i:int|0<=i<4 ==> 0<=#[trigger] b[i]<r,
    ensures forall|i:int|0<=i<7 ==> 0<=#[trigger] coefficients(a,b)[i]<4*r*r,
        0<=one(coefficients(a,b))<16*r*r,
{
    assert forall|i:int,j:int|0<=i<4 && 0<=j<4 implies 0<=#[trigger] (a[i]*b[j])<r*r by {
        assert(0<=a[i]<r && 0<=b[j]<r);
        assert(0<=a[i]*b[j]<r*r) by(nonlinear_arith)
            requires r>0,0<=a[i]<r,0<=b[j]<r;
    }
    let c=coefficients(a,b);
    assert(c.len()==7);
    lemma_mul_is_associative(4,r,r);lemma_mul_is_associative(16,r,r);
    assert forall|i:int|0<=i<7 implies 0<=#[trigger] c[i]<4*r*r by {}
}

// Each value is an intermediate in the prospective in-place kernel. Only
// input-defined coefficients occur here; no runtime result defines its own spec.
pub open spec fn even_one(c:Seq<int>)->int { (one(c)+negative(c))/2 }
pub open spec fn odd_one(c:Seq<int>)->int { (one(c)-negative(c))/2 }
pub open spec fn even_half(c:Seq<int>)->int { (scaled_half(c)+scaled_negative_half(c))/2 }
pub open spec fn odd_half(c:Seq<int>)->int { (scaled_half(c)-scaled_negative_half(c))/4 }
pub open spec fn even_middle(c:Seq<int>)->int {even_one(c)-c[0]-c[6]}
pub open spec fn half_middle(c:Seq<int>)->int {(even_half(c)-64*c[0]-c[6])/4}
pub open spec fn recover_c2(c:Seq<int>)->int {(half_middle(c)-even_middle(c))/3}
pub open spec fn recover_c4(c:Seq<int>)->int {even_middle(c)-recover_c2(c)}
pub open spec fn odd_two(c:Seq<int>)->int {(two(c)-c[0]-4*recover_c2(c)-16*recover_c4(c)-64*c[6])/2}
pub open spec fn recover_c3(c:Seq<int>)->int {(17*odd_one(c)-odd_half(c)-odd_two(c))/9}
pub open spec fn recover_c1(c:Seq<int>)->int {(odd_half(c)-odd_one(c)-3*recover_c3(c))/15}
pub open spec fn recover_c5(c:Seq<int>)->int {odd_one(c)-recover_c1(c)-recover_c3(c)}

pub proof fn exact_division(q:int,d:int)
    requires d>0,
    ensures (d*q)%d==0,(d*q)/d==q,
{
    lemma_mod_multiples_basic(q,d);
    lemma_div_multiples_vanish(q,d);
    lemma_mul_is_commutative(q,d);
}

pub proof fn interpolation(c:Seq<int>)
    requires c.len()==7,forall|i:int|0<=i<7 ==> 0<=#[trigger] c[i],
    ensures
        even_one(c)==c[0]+c[2]+c[4]+c[6],odd_one(c)==c[1]+c[3]+c[5],
        even_half(c)==64*c[0]+16*c[2]+4*c[4]+c[6],odd_half(c)==16*c[1]+4*c[3]+c[5],
        even_middle(c)==c[2]+c[4],half_middle(c)==4*c[2]+c[4],
        odd_two(c)==c[1]+4*c[3]+16*c[5],
        recover_c1(c)==c[1],recover_c2(c)==c[2],recover_c3(c)==c[3],recover_c4(c)==c[4],recover_c5(c)==c[5],
        0<=one(c)+negative(c), (one(c)+negative(c))%2==0,
        0<=one(c)-negative(c), (one(c)-negative(c))%2==0,
        0<=scaled_half(c)+scaled_negative_half(c), (scaled_half(c)+scaled_negative_half(c))%2==0,
        0<=scaled_half(c)-scaled_negative_half(c), (scaled_half(c)-scaled_negative_half(c))%4==0,
        0<=even_half(c)-64*c[0]-c[6], (even_half(c)-64*c[0]-c[6])%4==0,
        0<=half_middle(c)-even_middle(c), (half_middle(c)-even_middle(c))%3==0,
        0<=two(c)-c[0]-4*recover_c2(c)-16*recover_c4(c)-64*c[6],
        (two(c)-c[0]-4*recover_c2(c)-16*recover_c4(c)-64*c[6])%2==0,
        0<=17*odd_one(c)-odd_half(c)-odd_two(c), (17*odd_one(c)-odd_half(c)-odd_two(c))%9==0,
        0<=odd_half(c)-odd_one(c)-3*recover_c3(c), (odd_half(c)-odd_one(c)-3*recover_c3(c))%15==0,
{
    exact_division(c[0]+c[2]+c[4]+c[6],2);
    exact_division(c[1]+c[3]+c[5],2);
    exact_division(64*c[0]+16*c[2]+4*c[4]+c[6],2);
    exact_division(16*c[1]+4*c[3]+c[5],4);
    exact_division(4*c[2]+c[4],4);
    exact_division(c[2],3);
    assert(recover_c2(c)==c[2] && recover_c4(c)==c[4]);
    exact_division(c[1]+4*c[3]+16*c[5],2);
    exact_division(c[3],9);
    assert(recover_c3(c)==c[3]);
    exact_division(c[1],15);
}

// This is the numeric capacity obligation for the planned caller-owned layout.
// Slice splitting/lifetimes are not verified until the executable kernel exists.
pub proof fn workspace(n:int,k:int,m:int)
    requires n>=25,k==n/4+if n%4==0{0int}else{1int},m==k+1,
    ensures 0<k,3*k<n<=4*k,m<n,28*m<=12*n,25*m<=10*n,12*m>=2*m,10*m>=2*m,
{
    lemma_fundamental_div_mod(n,4);
    lemma_mod_division_less_than_divisor(n,4);
}
}

//! Five-point Toom-3 identities and interpolation obligations.
use vstd::prelude::*;
use vstd::arithmetic::mul::*;
verus! {
pub open spec fn eval(a0:int,a1:int,a2:int,x:int)->int {a0+x*a1+x*x*a2}
pub open spec fn c1(a0:int,a1:int,b0:int,b1:int)->int {a0*b1+a1*b0}
pub open spec fn c2(a0:int,a1:int,a2:int,b0:int,b1:int,b2:int)->int {a0*b2+a1*b1+a2*b0}
pub open spec fn c3(a1:int,a2:int,b1:int,b2:int)->int {a1*b2+a2*b1}

pub proof fn evaluation_bounds(a0:int,a1:int,a2:int,r:int)
    requires r>0,0<=a0<r,0<=a1<r,0<=a2<r,
    ensures 0<=eval(a0,a1,a2,1)<3*r,-r<eval(a0,a1,a2,-1)<2*r,
        0<=eval(a0,a1,a2,2)<7*r,
{}

pub proof fn coefficient_bounds(a0:int,a1:int,a2:int,b0:int,b1:int,b2:int,r:int)
    requires r>0,0<=a0<r,0<=a1<r,0<=a2<r,0<=b0<r,0<=b1<r,0<=b2<r,
    ensures 0<=a0*b0<r*r,0<=a2*b2<r*r,
        0<=c1(a0,a1,b0,b1)<2*r*r,0<=c2(a0,a1,a2,b0,b1,b2)<3*r*r,
        0<=c3(a1,a2,b1,b2)<2*r*r,
{
    assert(0<=a0*b0<r*r && 0<=a2*b2<r*r) by(nonlinear_arith)
        requires r>0,0<=a0<r,0<=a2<r,0<=b0<r,0<=b2<r;
    assert(0<=a0*b1<r*r && 0<=a1*b0<r*r) by(nonlinear_arith)
        requires r>0,0<=a0<r,0<=a1<r,0<=b0<r,0<=b1<r;
    assert(0<=a0*b2<r*r && 0<=a1*b1<r*r && 0<=a2*b0<r*r) by(nonlinear_arith)
        requires r>0,0<=a0<r,0<=a1<r,0<=a2<r,0<=b0<r,0<=b1<r,0<=b2<r;
    assert(0<=a1*b2<r*r && 0<=a2*b1<r*r) by(nonlinear_arith)
        requires r>0,0<=a1<r,0<=a2<r,0<=b1<r,0<=b2<r;
    assert(2*r*r==2*(r*r) && 3*r*r==3*(r*r)) by(nonlinear_arith);
}

pub proof fn interpolation(a0:int,a1:int,a2:int,b0:int,b1:int,b2:int)
    ensures
        eval(a0,a1,a2,1)*eval(b0,b1,b2,1)+eval(a0,a1,a2,-1)*eval(b0,b1,b2,-1)
            ==2*(a0*b0+c2(a0,a1,a2,b0,b1,b2)+a2*b2),
        eval(a0,a1,a2,1)*eval(b0,b1,b2,1)-eval(a0,a1,a2,-1)*eval(b0,b1,b2,-1)
            ==2*(c1(a0,a1,b0,b1)+c3(a1,a2,b1,b2)),
        eval(a0,a1,a2,2)*eval(b0,b1,b2,2)-a0*b0-16*a2*b2
            ==2*(c1(a0,a1,b0,b1)+2*c2(a0,a1,a2,b0,b1,b2)+4*c3(a1,a2,b1,b2)),
        (c1(a0,a1,b0,b1)+2*c2(a0,a1,a2,b0,b1,b2)+4*c3(a1,a2,b1,b2))
            -(c1(a0,a1,b0,b1)+c3(a1,a2,b1,b2))-2*c2(a0,a1,a2,b0,b1,b2)
            ==3*c3(a1,a2,b1,b2),
{
    recompose(a0,a1,a2,b0,b1,b2,1);
    recompose(a0,a1,a2,b0,b1,b2,-1);
    recompose(a0,a1,a2,b0,b1,b2,2);
    let z0=a0*b0;let z1=c1(a0,a1,b0,b1);let z2=c2(a0,a1,a2,b0,b1,b2);
    let z3=c3(a1,a2,b1,b2);let z4=a2*b2;
    lemma_mul_basics(z1);lemma_mul_basics(z2);lemma_mul_basics(z3);lemma_mul_basics(a2);
    lemma_mul_is_distributive_sub_other_way(z1,0,1);
    lemma_mul_is_distributive_sub_other_way(z3,0,1);
    assert(1int*1*1*1==1);
    assert((-1int)*(-1)*(-1)*(-1)==1);
    assert(1int*1*1*1*a2*b2==z4);
    assert(eval(a0,a1,a2,1)*eval(b0,b1,b2,1)==z0+z1+z2+z3+z4);
    assert(eval(a0,a1,a2,-1)*eval(b0,b1,b2,-1)==z0-z1+z2-z3+z4);
    lemma_mul_is_associative(16,a2,b2);
    assert(eval(a0,a1,a2,2)*eval(b0,b1,b2,2)==z0+2*z1+4*z2+8*z3+16*z4);
}

pub proof fn triple_product(a:int,b:int,c:int,d:int,e:int,f:int)
    ensures (a+b+c)*(d+e+f)==a*d+a*e+a*f+b*d+b*e+b*f+c*d+c*e+c*f,
{
    lemma_mul_is_distributive_add(a+b+c,d+e,f);
    lemma_mul_is_distributive_add(a+b+c,d,e);
    lemma_mul_is_distributive_add_other_way(d,a+b,c);
    lemma_mul_is_distributive_add_other_way(d,a,b);
    lemma_mul_is_distributive_add_other_way(e,a+b,c);
    lemma_mul_is_distributive_add_other_way(e,a,b);
    lemma_mul_is_distributive_add_other_way(f,a+b,c);
    lemma_mul_is_distributive_add_other_way(f,a,b);
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

pub proof fn recompose(a0:int,a1:int,a2:int,b0:int,b1:int,b2:int,r:int)
    ensures eval(a0,a1,a2,r)*eval(b0,b1,b2,r)
        ==a0*b0+r*c1(a0,a1,b0,b1)+r*r*c2(a0,a1,a2,b0,b1,b2)
            +r*r*r*c3(a1,a2,b1,b2)+r*r*r*r*a2*b2,
{
    triple_product(a0,r*a1,r*r*a2,b0,r*b1,r*r*b2);
    monomial_mul(a0,b0,1,1);monomial_mul(a0,b1,1,r);monomial_mul(a0,b2,1,r*r);
    monomial_mul(a1,b0,r,1);monomial_mul(a1,b1,r,r);monomial_mul(a1,b2,r,r*r);
    monomial_mul(a2,b0,r*r,1);monomial_mul(a2,b1,r*r,r);monomial_mul(a2,b2,r*r,r*r);
    lemma_mul_is_associative(r,r,r);
    lemma_mul_is_associative(r*r,r,r);
    lemma_mul_is_associative(r*r*r*r,a2,b2);
    lemma_mul_is_distributive_add(r,a0*b1,a1*b0);
    lemma_mul_is_distributive_add(r*r,a0*b2+a1*b1,a2*b0);
    lemma_mul_is_distributive_add(r*r,a0*b2,a1*b1);
    lemma_mul_is_distributive_add(r*r*r,a1*b2,a2*b1);
}
}

//! Independent radix-unit facts for exact division by the selected odd constants.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
verus! {
pub open spec fn supported(d:int)->bool { d==3 || d==9 || d==15 }
pub open spec fn inverse(d:int)->int {
    if d==3 {12297829382473034411} else if d==9 {10248191152060862009} else {17216961135462248175}
}
pub open spec fn inverse_factor(d:int)->int { if d==3 {2} else if d==9 {5} else {14} }

pub proof fn inverse_identity(d:int)
    requires supported(d),
    ensures d*inverse(d)==1+base()*inverse_factor(d),0<inverse(d)<=u64::MAX,0<d<=15,
{
    if d==3 {} else if d==9 {} else {assert(d==15);}
}

pub proof fn cancel_radix(n:nat,x:int,d:int)
    requires supported(d),(radix(n)*x)%d==0,
    ensures x%d==0,
    decreases n,
{
    if n>0 {
        let y=radix((n-1) as nat)*x;
        let t=if d==9 {4int}else{1int};
        let k=if d==3 {6148914691236517205int}
            else if d==9 {8198552921648689607int}else{1229782938247303441int};
        assert(t*base()==1+d*k);
        assert(radix(n)*x==base()*y) by(nonlinear_arith)
            requires radix(n)==base()*radix((n-1) as nat),y==radix((n-1) as nat)*x;
        lemma_mul_mod_noop_right(t,base()*y,d);
        assert(t*(base()*y)==y+d*(k*y)) by(nonlinear_arith)
            requires t*base()==1+d*k;
        lemma_mod_multiples_vanish(k*y,y,d);
        assert(y%d==0);
        cancel_radix((n-1) as nat,x,d);
    }
}
}

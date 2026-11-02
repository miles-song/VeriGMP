//! Radix-unit cancellation independent of a quotient implementation.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::mul::*;
use crate::radix::*;
verus! {
pub open spec fn inverse_valid(d:int,inv:int)->bool {
    0<d<=u64::MAX && 0<=inv<=u64::MAX && (d*inv)%base()==1
}
pub open spec fn factor(d:int,inv:int)->int { (d*inv)/base() }
pub open spec fn toom8_supported(d:int)->bool {
    d==3 || d==15 || d==63 || d==255 || d==1023 || d==4095
}
pub proof fn inverse_identity(d:int,inv:int)
    requires inverse_valid(d,inv),
    ensures d*inv==1+base()*factor(d,inv),
{
    lemma_fundamental_div_mod(d*inv,base());
}
pub proof fn cancel_radix(n:nat,x:int,d:int,inv:int)
    requires inverse_valid(d,inv),(radix(n)*x)%d==0,
    ensures x%d==0,
    decreases n,
{
    if n>0 {
        inverse_identity(d,inv);
        let y=radix((n-1) as nat)*x;
        let t=-factor(d,inv);
        let k=-inv;
        assert(t*base()==1+d*k) by(nonlinear_arith)
            requires d*inv==1+base()*factor(d,inv),t==-factor(d,inv),k==-inv;
        assert(radix(n)*x==base()*y) by(nonlinear_arith)
            requires radix(n)==base()*radix((n-1) as nat),y==radix((n-1) as nat)*x;
        lemma_mul_mod_noop_right(t,base()*y,d);
        lemma_mul_basics(t);
        lemma_small_mod(0,d as nat);
        assert((t*(base()*y))%d==0);
        assert(t*(base()*y)==y+d*(k*y)) by(nonlinear_arith)
            requires t*base()==1+d*k;
        lemma_mod_multiples_vanish(k*y,y,d);
        assert(y%d==0);
        cancel_radix((n-1) as nat,x,d,inv);
    }
}
}

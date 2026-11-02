//! Independent sum/difference meanings for signed polynomial point pairs.
use vstd::prelude::*;
use crate::radix::*;
verus! {
pub open spec fn signed_magnitude(magnitude:int,negative:bool)->int {if negative {-magnitude}else{magnitude}}
pub open spec fn sum_prefix(a:Seq<u64>,b:Seq<u64>,i:nat,negative:bool)->int {
    if negative {prefix(b,i)}else{prefix(a,i)}
}
pub open spec fn difference_prefix(a:Seq<u64>,b:Seq<u64>,i:nat,negative:bool)->int {
    if negative {prefix(a,i)}else{prefix(b,i)}
}
pub proof fn scale_sum(old:int,ap:int,bp:int,r:int,carry:int,low:int,next:int,x:int,y:int)
    requires old+r*carry==ap+bp,low+base()*next==x+y+carry,
    ensures old+r*low+(base()*r)*next==(ap+r*x)+(bp+r*y),
{
    assert(old+r*low+(base()*r)*next==(ap+r*x)+(bp+r*y)) by(nonlinear_arith)
        requires old+r*carry==ap+bp,low+base()*next==x+y+carry;
}
pub proof fn scale_difference(old:int,ap:int,bp:int,r:int,borrow:int,low:int,next:int,x:int,y:int)
    requires old-r*borrow==ap-bp,low-base()*next==x-y-borrow,
    ensures old+r*low-(base()*r)*next==(ap+r*x)-(bp+r*y),
{
    assert(old+r*low-(base()*r)*next==(ap+r*x)-(bp+r*y)) by(nonlinear_arith)
        requires old-r*borrow==ap-bp,low-base()*next==x-y-borrow;
}
}

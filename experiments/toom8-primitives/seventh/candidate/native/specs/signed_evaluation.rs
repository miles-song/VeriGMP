//! Signed input meanings, independent of the executable digit representation.
use vstd::prelude::*;
use crate::radix::*;
use crate::fast_product::*;
verus! {
pub open spec fn weighted(x0:int,x1:int,x2:int,x3:int,half:bool)->int {
    if half {8*x0-4*x1+2*x2-x3} else {x0-x1+x2-x3}
}
pub open spec fn input_prefix(a0:Seq<u64>,a1:Seq<u64>,a2:Seq<u64>,a3:Seq<u64>,i:nat,half:bool)->int {
    weighted(extended(a0,i),extended(a1,i),extended(a2,i),extended(a3,i),half)
}
pub open spec fn evaluation(a0:Seq<u64>,a1:Seq<u64>,a2:Seq<u64>,a3:Seq<u64>,half:bool)->int {
    weighted(value(a0),value(a1),value(a2),value(a3),half)
}
pub proof fn prefix_step(a0:Seq<u64>,a1:Seq<u64>,a2:Seq<u64>,a3:Seq<u64>,i:nat,half:bool)
    ensures input_prefix(a0,a1,a2,a3,i+1,half)==input_prefix(a0,a1,a2,a3,i,half)
        +radix(i)*weighted(digit(a0,i),digit(a1,i),digit(a2,i),digit(a3,i),half),
{
    extended_step(a0,i);extended_step(a1,i);extended_step(a2,i);extended_step(a3,i);
    if half {
        assert(input_prefix(a0,a1,a2,a3,i+1,half)==input_prefix(a0,a1,a2,a3,i,half)
            +radix(i)*weighted(digit(a0,i),digit(a1,i),digit(a2,i),digit(a3,i),half)) by(nonlinear_arith)
            requires extended(a0,i+1)==extended(a0,i)+digit(a0,i)*radix(i),
                extended(a1,i+1)==extended(a1,i)+digit(a1,i)*radix(i),
                extended(a2,i+1)==extended(a2,i)+digit(a2,i)*radix(i),
                extended(a3,i+1)==extended(a3,i)+digit(a3,i)*radix(i),half;
    } else {
        assert(input_prefix(a0,a1,a2,a3,i+1,half)==input_prefix(a0,a1,a2,a3,i,half)
            +radix(i)*weighted(digit(a0,i),digit(a1,i),digit(a2,i),digit(a3,i),half)) by(nonlinear_arith)
            requires extended(a0,i+1)==extended(a0,i)+digit(a0,i)*radix(i),
                extended(a1,i+1)==extended(a1,i)+digit(a1,i)*radix(i),
                extended(a2,i+1)==extended(a2,i)+digit(a2,i)*radix(i),
                extended(a3,i+1)==extended(a3,i)+digit(a3,i)*radix(i),!half;
    }
}
}

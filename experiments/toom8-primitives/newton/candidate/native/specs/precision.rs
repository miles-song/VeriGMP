//! Precision model: n words with 1..64 significant bits in the top word.
use vstd::prelude::*;
use vstd::arithmetic::power::*;
use vstd::arithmetic::power2::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;

verus! {

pub open spec fn bit_precision(n: nat, top: nat) -> nat
    recommends n > 0, 1 <= top <= 64,
{
    64 * ((n - 1) as nat) + top
}

pub open spec fn modulus(n: nat, top: nat) -> int
    recommends n > 0, 1 <= top <= 64,
{
    radix((n - 1) as nat) * (pow2(top) as int)
}

pub proof fn modulus_properties(n: nat, top: nat)
    requires n > 0, 1 <= top <= 64,
    ensures
        modulus(n, top) > 0,
        modulus(n, top) == pow(2, bit_precision(n, top)),
        radix(n) == modulus(n, top) * (pow2((64 - top) as nat) as int),
{
    radix_positive((n - 1) as nat);
    radix_is_power_of_two((n - 1) as nat);
    lemma_pow2_pos(top);
    lemma_pow2_pos((64 - top) as nat);
    lemma_pow_positive(2, top);
    lemma_pow_positive(2, 64 * ((n - 1) as nat));
    lemma_pow_adds(2, 64 * ((n - 1) as nat), top);
    lemma_pow2_adds(top, (64 - top) as nat);
    lemma2_to64();
    assert(modulus(n, top) > 0) by(nonlinear_arith)
        requires radix((n - 1) as nat) > 0, pow2(top) > 0,
            modulus(n, top) == radix((n - 1) as nat) * (pow2(top) as int);
    assert(radix(n) == modulus(n, top) * (pow2((64 - top) as nat) as int))
        by(nonlinear_arith)
        requires
            radix(n) == base() * radix((n - 1) as nat),
            base() == (pow2(top) as int) * (pow2((64 - top) as nat) as int),
            modulus(n, top) == radix((n - 1) as nat) * (pow2(top) as int);
}

/// Local quotient/remainder replacement lifts to the complete represented integer.
pub proof fn top_replacement_is_mod(before: Seq<u64>, after: Seq<u64>, top: nat)
    requires
        before.len() > 0, after.len() == before.len(), 1 <= top <= 64,
        forall|j: int| 0 <= j < before.len() - 1 ==> after[j] == before[j],
        (after.last() as int) == (before.last() as int) % (pow2(top) as int),
    ensures
        value(after) == value(before) % modulus(before.len(), top),
        0 <= value(after) < modulus(before.len(), top),
{
    let n = before.len();
    let lower = (n - 1) as nat;
    let scale = radix(lower);
    let d = pow2(top) as int;
    equal_prefix(before, after, lower);
    prefix_range(before, lower);
    radix_positive(lower);
    lemma_pow2_pos(top);
    lemma_fundamental_div_mod(before.last() as int, d);
    lemma_mod_division_less_than_divisor(before.last() as int, d);
    let q = (before.last() as int) / d;
    assert(0 <= value(after) < modulus(n, top)) by(nonlinear_arith)
        requires
            0 <= prefix(before, lower) < scale, scale > 0, d > 0,
            0 <= (after.last() as int) < d,
            value(after) == prefix(before, lower) + (after.last() as int) * scale,
            modulus(n, top) == scale * d;
    assert(value(before) == q * modulus(n, top) + value(after)) by(nonlinear_arith)
        requires
            (before.last() as int) == d * q + (after.last() as int),
            value(before) == prefix(before, lower) + (before.last() as int) * scale,
            value(after) == prefix(before, lower) + (after.last() as int) * scale,
            modulus(n, top) == scale * d;
    lemma_fundamental_div_mod_converse(value(before), modulus(n, top), q, value(after));
}

} // verus!

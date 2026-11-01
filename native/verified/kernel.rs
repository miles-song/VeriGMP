use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
verus! {

/// Scalar modular operations are a word-size specialization, not a claim of
/// arbitrary-precision support. The u128 intermediate is proved sufficient.
pub fn add_mod(a: u64, b: u64, modulus: u64) -> (answer: u64)
    requires modulus > 0,
    ensures
        answer as int == ((a as int) + (b as int)) % (modulus as int),
        answer < modulus,
{
    let sum = (a as u128) + (b as u128);
    (sum % (modulus as u128)) as u64
}

pub fn mul_mod(a: u64, b: u64, modulus: u64) -> (answer: u64)
    requires modulus > 0,
    ensures
        answer as int == ((a as int) * (b as int)) % (modulus as int),
        answer < modulus,
{
    assert((a as int) * (b as int) <= u128::MAX) by(nonlinear_arith);
    let product = (a as u128) * (b as u128);
    (product % (modulus as u128)) as u64
}

/// First building block for arbitrary precision: one base-2^64 limb plus carry.
pub fn add_limb(a: u64, b: u64, carry: u64) -> (answer: (u64, u64))
    requires carry <= 1,
    ensures
        answer.1 <= 1,
        answer.0 as int + 18446744073709551616int * (answer.1 as int)
            == (a as int) + (b as int) + (carry as int),
{
    let base: u128 = 18446744073709551616;
    let sum = (a as u128) + (b as u128) + (carry as u128);
    proof { lemma_fundamental_div_mod(sum as int, base as int); }
    ((sum % base) as u64, (sum / base) as u64)
}

} // verus!

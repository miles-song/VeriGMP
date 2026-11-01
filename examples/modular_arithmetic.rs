//! Multiply and square modulo 2^p through VeriGMP's fixed public dispatch.
//!
//! Build after `python3 scripts/verify.py` has exported the library:
//!
//!   "$VERUS_BIN" examples/modular_arithmetic.rs \
//!       --import verigmp=build/verigmp.vir \
//!       --extern verigmp=build/libverigmp.rlib \
//!       --compile -O -o build/modular-example
//!
//! What is verified: the library functions called here (`arithmetic::*`) carry
//! Verus contracts proved against their Rust bodies, and `square_by_product`
//! below is checked by Verus against the imported contract of `mul_mod`.
//! What is not verified: `main` and the small allocation helpers are ordinary
//! Rust. They are checked only by the assertions they execute, so passing
//! this program is a test, not a theorem.

use vstd::prelude::*;
use verigmp::arithmetic;
use verigmp::precision::modulus;
use verigmp::radix::value;

verus! {

/// A verified caller. Verus proves this postcondition from the imported
/// contract of `arithmetic::mul_mod`, using `a` as both operands.
fn square_by_product(dst: &mut [u64], a: &[u64], scratch: &mut [u64], top: u32)
    requires
        a@.len() > 0,
        old(dst)@.len() == a@.len(),
        old(scratch)@.len() >= 12 * a@.len(),
        1 <= top <= 64,
    ensures
        value(final(dst)@) == (value(a@) * value(a@)) % modulus(a@.len(), top as nat),
{
    arithmetic::mul_mod(dst, a, a, scratch, top);
}

} // verus!

/// value(a) * value(b) mod 2^(64*(n-1)+top), using caller-owned Vec storage.
fn mul_mod(a: &[u64], b: &[u64], top: u32) -> Vec<u64> {
    let n = a.len();
    let words = arithmetic::workspace_len(n).expect("n > 0 and 12n must fit in usize");
    let mut scratch = vec![0u64; words];
    let mut out = vec![0u64; n];
    arithmetic::mul_mod(&mut out, a, b, &mut scratch, top);
    out
}

/// value(a)^2 mod 2^(64*(n-1)+top), using the dedicated squaring path.
fn square_mod(a: &[u64], top: u32) -> Vec<u64> {
    let n = a.len();
    let words = arithmetic::square_workspace_len(n).expect("n > 0 and 10n must fit in usize");
    let mut scratch = vec![0u64; words];
    let mut out = vec![0u64; n];
    arithmetic::square_mod(&mut out, a, &mut scratch, top);
    out
}

fn main() {
    // Little-endian limbs: a = 3 + 1*2^64, b = 5 + 2*2^64.
    // a*b = 15 + 11*2^64 + 2*2^128 and a^2 = 9 + 6*2^64 + 1*2^128.
    let a = [3u64, 1];
    let b = [5u64, 2];

    // n = 2, top = 64: p = 128, so the 2^128 terms vanish.
    let product = mul_mod(&a, &b, 64);
    let square = square_mod(&a, 64);
    assert_eq!(product, [15, 11]);
    assert_eq!(square, [9, 6]);
    println!("mod 2^128: a*b = {:?}, a^2 = {:?}", product, square);

    // n = 2, top = 1: p = 65, so only bit 0 of the top limb survives.
    // b's top limb (2) exceeds that precision; the contract still uses value(b).
    let product = mul_mod(&a, &b, 1);
    let square = square_mod(&a, 1);
    assert_eq!(product, [15, 1]);
    assert_eq!(square, [9, 0]);
    println!("mod 2^65:  a*b = {:?}, a^2 = {:?}", product, square);

    // n = 600 >= 512 takes the Toom-3 product branch. With x = 2^(64n) - 1,
    // x^2 = 2^(128n) - 2^(64n+1) + 1, which is 1 modulo 2^p for every top.
    let n = 600;
    let x = vec![u64::MAX; n];
    let mut one = vec![0u64; n];
    one[0] = 1;
    for top in [1u32, 37, 64] {
        assert_eq!(mul_mod(&x, &x, top), one);
        assert_eq!(square_mod(&x, top), one);
    }

    // The verified wrapper agrees with the dedicated square at a partial top.
    let mut out = vec![u64::MAX; n]; // initial output contents are arbitrary
    let mut scratch = vec![0u64; arithmetic::workspace_len(n).unwrap()];
    square_by_product(&mut out, &x, &mut scratch, 37);
    assert_eq!(out, square_mod(&x, 37));
    println!("600 limbs, top in {{1, 37, 64}}: (2^38400 - 1)^2 mod 2^p = 1");
}

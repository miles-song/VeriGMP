//! Positive bit precision without division, allocation or array traversal
//! for normalization. Addition reuses the verified limb loop.
use vstd::prelude::*;
use vstd::bits::*;
use vstd::arithmetic::power2::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::precision::*;
use crate::limbs;

verus! {

/// Compute the storage shape once at the precision boundary, without p+63 overflow.
pub fn precision_layout(bits: usize) -> (layout: (usize, u32))
    requires bits > 0,
    ensures
        layout.0 > 0,
        1 <= layout.1 <= 64,
        bit_precision(layout.0 as nat, layout.1 as nat) == bits as nat,
{
    assert!(bits > 0);
    let remaining = bits - 1;
    proof {
        lemma_fundamental_div_mod(remaining as int, 64);
        lemma_mod_division_less_than_divisor(remaining as int, 64);
    }
    (remaining / 64 + 1, (remaining % 64) as u32 + 1)
}

pub fn mask_word(word: u64, bits: u32) -> (out: u64)
    requires 1 <= bits <= 64,
    ensures
        out as int == (word as int) % (pow2(bits as nat) as int),
        (out as int) < pow2(bits as nat),
{
    assert!(1 <= bits && bits <= 64);
    if bits == 64 {
        proof {
            lemma2_to64();
            lemma_small_mod(word as nat, base() as nat);
        }
        word
    } else {
        proof {
            lemma_u64_pow2_no_overflow(bits as nat);
            lemma_u64_shl_is_mul(1, bits as u64);
            lemma_u64_low_bits_mask_is_mod(word, bits as nat);
        }
        let mask = (1u64 << bits) - 1;
        word & mask
    }
}

pub fn normalize_top(dst: &mut [u64], top: u32)
    requires old(dst)@.len() > 0, 1 <= top <= 64,
    ensures
        final(dst)@.len() == old(dst)@.len(),
        forall|j: int| 0 <= j < old(dst)@.len() - 1 ==> final(dst)@[j] == old(dst)@[j],
        value(final(dst)@) == value(old(dst)@) % modulus(old(dst)@.len(), top as nat),
        0 <= value(final(dst)@) < modulus(old(dst)@.len(), top as nat),
{
    assert!(dst.len() > 0);
    let ghost before = dst@;
    let last = dst.len() - 1;
    dst[last] = mask_word(dst[last], top);
    proof { top_replacement_is_mod(before, dst@, top as nat); }
}

pub fn add_mod_assign(dst: &mut [u64], rhs: &[u64], top: u32)
    requires old(dst)@.len() > 0, old(dst)@.len() == rhs@.len(), 1 <= top <= 64,
    ensures
        final(dst)@.len() == old(dst)@.len(),
        value(final(dst)@) == (value(old(dst)@) + value(rhs@)) % modulus(rhs@.len(), top as nat),
        0 <= value(final(dst)@) < modulus(rhs@.len(), top as nat),
{
    assert!(dst.len() > 0);
    assert!(1 <= top && top <= 64);
    let ghost before = dst@;
    let _carry = limbs::add_assign(dst, rhs);
    normalize_top(dst, top);
    proof {
        modulus_properties(rhs@.len(), top as nat);
        lemma_pow2_pos((64 - top) as nat);
        lemma_mod_mod(value(before) + value(rhs@), modulus(rhs@.len(), top as nat),
            pow2((64 - top) as nat) as int);
    }
}

} // verus!

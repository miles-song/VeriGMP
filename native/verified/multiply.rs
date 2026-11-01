//! Truncated schoolbook basecase. All storage belongs to the caller.
//! The default fast backend is in fast_multiply.rs.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::power2::*;
use crate::radix::*;
use crate::product::*;
use crate::precision::*;
use crate::pow2;

verus! {

/// The carry is a full word, unlike the carry of addition.
pub fn mac(a: u64, b: u64, acc: u64, carry: u64) -> (out: (u64, u64))
    ensures
        (out.0 as int) + base() * (out.1 as int)
            == (a as int) * (b as int) + (acc as int) + (carry as int),
{
    assert((a as int) * (b as int) + (acc as int) + (carry as int) <= u128::MAX)
        by(nonlinear_arith);
    let total = (a as u128) * (b as u128) + (acc as u128) + (carry as u128);
    let radix: u128 = 18446744073709551616;
    proof { lemma_fundamental_div_mod(total as int, radix as int); }
    ((total % radix) as u64, (total / radix) as u64)
}

/// Accumulate a contiguous row; input may be longer than the destination.
pub fn add_mul_word(dst: &mut [u64], rhs: &[u64], word: u64) -> (carry_out: u64)
    requires old(dst)@.len() <= rhs@.len(),
    ensures
        final(dst)@.len() == old(dst)@.len(),
        value(final(dst)@) + radix(old(dst)@.len()) * (carry_out as int)
            == value(old(dst)@) + (word as int) * prefix(rhs@, old(dst)@.len()),
{
    assert!(dst.len() <= rhs.len());
    let ghost original = dst@;
    let mut j: usize = 0;
    let mut carry: u64 = 0;
    let ghost mut visits: nat = 0;
    while j < dst.len()
        invariant
            dst@.len() == original.len(), dst@.len() <= rhs@.len(),
            j <= dst@.len(), visits == j,
            forall|k: int| j <= k < dst@.len() ==> #[trigger] dst@[k] == original[k],
            prefix(dst@, j as nat) + radix(j as nat) * (carry as int)
                == prefix(original, j as nat) + (word as int) * prefix(rhs@, j as nat),
        decreases dst.len() - j,
    {
        let ghost before = dst@;
        let ghost incoming = carry;
        let (low, high) = mac(word, rhs[j], dst[j], carry);
        dst[j] = low;
        proof {
            equal_prefix(dst@, before, j as nat);
            mac_prefix_step(prefix(before, j as nat), prefix(original, j as nat),
                prefix(rhs@, j as nat), radix(j as nat), word as int,
                word as int, rhs@[j as int] as int, before[j as int] as int,
                incoming as int, low as int, high as int);
            assert((word as int) * prefix(rhs@, (j + 1) as nat)
                == (word as int) * prefix(rhs@, j as nat)
                    + (word as int) * (rhs@[j as int] as int) * radix(j as nat)) by(nonlinear_arith)
                requires prefix(rhs@, (j + 1) as nat) == prefix(rhs@, j as nat)
                    + (rhs@[j as int] as int) * radix(j as nat);
        }
        carry = high;
        j += 1;
        proof { visits = visits + 1; }
    }
    proof { assert(visits == original.len()); }
    carry
}

/// The suffix borrow is allocation-free; its final carry starts at position n.
pub fn add_mul_at(dst: &mut [u64], rhs: &[u64], word: u64, offset: usize)
    requires old(dst)@.len() == rhs@.len(), offset <= rhs@.len(),
    ensures
        final(dst)@.len() == old(dst)@.len(),
        value(final(dst)@) == (value(old(dst)@)
            + (word as int) * radix(offset as nat) * value(rhs@)) % radix(rhs@.len()),
{
    assert!(dst.len() == rhs.len());
    assert!(offset <= dst.len());
    let ghost original = dst@;
    let limit = dst.len() - offset;
    let carry = add_mul_word(&mut dst[offset..], rhs, word);
    proof {
        let suffix = dst@.subrange(offset as int, dst@.len() as int);
        let old_suffix = original.subrange(offset as int, original.len() as int);
        equal_prefix(dst@, original, offset as nat);
        subrange_value(dst@, offset as nat, limit as nat);
        subrange_value(original, offset as nat, limit as nat);
        split_value(rhs@, limit as nat);
        radix_add(offset as nat, limit as nat);
        prefix_range(dst@, dst@.len());
        radix_positive(dst@.len());
        let row_sum = (word as int) * prefix(rhs@, limit as nat);
        assert(value(dst@) + radix(offset as nat) * (radix(limit as nat) * (carry as int))
            == value(original) + radix(offset as nat) * row_sum) by(nonlinear_arith)
            requires
                value(suffix) + radix(limit as nat) * (carry as int) == value(old_suffix) + row_sum,
                value(dst@) == prefix(original, offset as nat) + radix(offset as nat) * value(suffix),
                value(original) == prefix(original, offset as nat) + radix(offset as nat) * value(old_suffix);
        assert(value(dst@) + radix(rhs@.len()) * (carry as int)
            == value(original) + (word as int) * radix(offset as nat) * prefix(rhs@, limit as nat)) by(nonlinear_arith)
            requires
                value(dst@) + radix(offset as nat) * (radix(limit as nat) * (carry as int))
                    == value(original) + radix(offset as nat) * row_sum,
                row_sum == (word as int) * prefix(rhs@, limit as nat),
                radix(rhs@.len()) == radix(offset as nat) * radix(limit as nat);
        let total = value(original) + (word as int) * radix(offset as nat) * value(rhs@);
        let quotient = (carry as int) + (word as int) * tail(rhs@, limit as nat);
        assert(total == quotient * radix(rhs@.len()) + value(dst@)) by(nonlinear_arith)
            requires
                value(dst@) + radix(rhs@.len()) * (carry as int)
                    == value(original) + (word as int) * radix(offset as nat) * prefix(rhs@, limit as nat),
                value(rhs@) == prefix(rhs@, limit as nat) + radix(limit as nat) * tail(rhs@, limit as nat),
                radix(rhs@.len()) == radix(offset as nat) * radix(limit as nat),
                total == value(original) + (word as int) * radix(offset as nat) * value(rhs@),
                quotient == (carry as int) + (word as int) * tail(rhs@, limit as nat);
        lemma_fundamental_div_mod_converse(total, radix(rhs@.len()), quotient, value(dst@));
    }
}

/// Overwrite dst with the low n words of the product. Empty slices represent zero.
pub fn mul_low(dst: &mut [u64], lhs: &[u64], rhs: &[u64])
    requires old(dst)@.len() == lhs@.len(), lhs@.len() == rhs@.len(),
    ensures
        final(dst)@.len() == old(dst)@.len(),
        value(final(dst)@) == (value(lhs@) * value(rhs@)) % radix(rhs@.len()),
{
    assert!(dst.len() == lhs.len());
    assert!(lhs.len() == rhs.len());
    let n = dst.len();
    let mut z: usize = 0;
    while z < n
        invariant dst@.len() == n, z <= n, prefix(dst@, z as nat) == 0,
        decreases n - z,
    {
        let ghost before = dst@;
        dst[z] = 0;
        proof { equal_prefix(dst@, before, z as nat); }
        z += 1;
    }
    proof { radix_positive(n as nat); lemma_small_mod(0, radix(n as nat) as nat); }
    let mut i: usize = 0;
    let ghost mut visits: nat = 0;
    while i < n
        invariant
            dst@.len() == n, lhs@.len() == n, rhs@.len() == n, i <= n,
            value(dst@) == (prefix(lhs@, i as nat) * value(rhs@)) % radix(n as nat),
            radix(n as nat) > 0,
            2 * visits == i * (2 * n - i + 1),
        decreases n - i,
    {
        add_mul_at(dst, rhs, lhs[i], i);
        proof {
            let m = radix(n as nat);
            let prev = prefix(lhs@, i as nat) * value(rhs@);
            let term = (lhs@[i as int] as int) * radix(i as nat) * value(rhs@);
            lemma_add_mod_noop_right(term, prev, m);
            assert(prefix(lhs@, (i + 1) as nat) * value(rhs@) == prev + term)
                by(nonlinear_arith)
                requires prefix(lhs@, (i + 1) as nat)
                    == prefix(lhs@, i as nat) + (lhs@[i as int] as int) * radix(i as nat),
                    prev == prefix(lhs@, i as nat) * value(rhs@),
                    term == (lhs@[i as int] as int) * radix(i as nat) * value(rhs@);
            assert(value(dst@) == (prev + term) % m);
            assert(2 * (visits + (n - i)) == (i + 1) * (2 * n - (i + 1) + 1))
                by(nonlinear_arith)
                requires 2 * visits == i * (2 * n - i + 1);
            visits = visits + (n - i) as nat;
        }
        i += 1;
    }
    proof { assert(2 * visits == n * (n + 1)); }
}

pub fn mul_mod(dst: &mut [u64], lhs: &[u64], rhs: &[u64], top: u32)
    requires
        old(dst)@.len() > 0, old(dst)@.len() == lhs@.len(), lhs@.len() == rhs@.len(),
        1 <= top <= 64,
    ensures
        final(dst)@.len() == old(dst)@.len(),
        value(final(dst)@) == (value(lhs@) * value(rhs@)) % modulus(rhs@.len(), top as nat),
        0 <= value(final(dst)@) < modulus(rhs@.len(), top as nat),
{
    assert!(dst.len() > 0);
    assert!(1 <= top && top <= 64);
    mul_low(dst, lhs, rhs);
    pow2::normalize_top(dst, top);
    proof {
        modulus_properties(rhs@.len(), top as nat);
        lemma_pow2_pos((64 - top) as nat);
        lemma_mod_mod(value(lhs@) * value(rhs@), modulus(rhs@.len(), top as nat),
            pow2((64 - top) as nat) as int);
    }
}

} // verus!

//! In-place addition. Rust borrows separate the writable destination from
//! the read-only operand; there is no allocation or whole-array copy here.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use crate::radix::*;
use crate::kernel::add_limb;

verus! {

pub fn add_assign(dst: &mut [u64], rhs: &[u64]) -> (carry: u64)
    requires old(dst)@.len() == rhs@.len(),
    ensures
        final(dst)@.len() == old(dst)@.len(),
        carry <= 1,
        value(final(dst)@) + radix(rhs@.len()) * (carry as int)
            == value(old(dst)@) + value(rhs@),
        value(final(dst)@) == (value(old(dst)@) + value(rhs@)) % radix(rhs@.len()),
{
    assert!(dst.len() == rhs.len());
    let ghost original = dst@;
    let mut i: usize = 0;
    let mut carry: u64 = 0;
    let ghost mut visits: nat = 0;
    while i < dst.len()
        invariant
            dst@.len() == original.len(),
            dst@.len() == rhs@.len(),
            i <= dst@.len(),
            carry <= 1,
            visits == i,
            forall|j: int| i <= j < dst@.len() ==> #[trigger] dst@[j] == original[j],
            prefix(dst@, i as nat) + radix(i as nat) * (carry as int)
                == prefix(original, i as nat) + prefix(rhs@, i as nat),
        decreases dst.len() - i,
    {
        let ghost before = dst@;
        let ghost incoming = carry;
        let (low, next) = add_limb(dst[i], rhs[i], carry);
        dst[i] = low;
        proof {
            equal_prefix(dst@, before, i as nat);
            assert(prefix(dst@, (i + 1) as nat) + radix((i + 1) as nat) * (next as int)
                == prefix(original, (i + 1) as nat) + prefix(rhs@, (i + 1) as nat))
                by(nonlinear_arith)
                requires
                    prefix(dst@, i as nat) == prefix(before, i as nat),
                    prefix(before, i as nat) + radix(i as nat) * (incoming as int)
                        == prefix(original, i as nat) + prefix(rhs@, i as nat),
                    before[i as int] == original[i as int],
                    (low as int) + base() * (next as int)
                        == (before[i as int] as int) + (rhs@[i as int] as int) + (incoming as int),
                    prefix(dst@, (i + 1) as nat) == prefix(dst@, i as nat) + (low as int) * radix(i as nat),
                    prefix(original, (i + 1) as nat) == prefix(original, i as nat) + (original[i as int] as int) * radix(i as nat),
                    prefix(rhs@, (i + 1) as nat) == prefix(rhs@, i as nat) + (rhs@[i as int] as int) * radix(i as nat),
                    radix((i + 1) as nat) == base() * radix(i as nat);
        }
        carry = next;
        i += 1;
        proof { visits = visits + 1; }
    }
    proof {
        assert(visits == original.len());
        prefix_range(dst@, dst@.len());
        assert(value(original) + value(rhs@) == (carry as int) * radix(rhs@.len()) + value(dst@))
            by(nonlinear_arith)
            requires value(dst@) + radix(rhs@.len()) * (carry as int)
                == value(original) + value(rhs@);
        lemma_fundamental_div_mod_converse(value(original) + value(rhs@),
            radix(rhs@.len()), carry as int, value(dst@));
    }
    carry
}

} // verus!

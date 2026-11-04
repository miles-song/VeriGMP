//! Four-word unrolling preserves the exact carry chain, with a short tail.
use vstd::prelude::*;
use crate::radix::*;
use crate::product::*;
use crate::multiply;
verus! {
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
    let limit=if dst.len()>=4 {dst.len()-3}else{0};
    while j<limit
        invariant
            limit as int == if dst@.len()>=4 {dst@.len()-3}else{0},
            dst@.len() == original.len(), dst@.len() <= rhs@.len(),
            j <= dst@.len(), visits == j,
            forall|k: int| j <= k < dst@.len() ==> #[trigger] dst@[k] == original[k],
            prefix(dst@, j as nat) + radix(j as nat) * (carry as int)
                == prefix(original, j as nat) + (word as int) * prefix(rhs@, j as nat),
        decreases dst.len() - j,
    {
        {

            let ghost before = dst@;
            let ghost incoming = carry;
            let (low, high) = multiply::mac(word, rhs[j], dst[j], carry);
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
            carry = 0;
            j += 1;
            proof { visits = visits + 1; }
        }
        {

            let ghost before = dst@;
            let ghost incoming = carry;
            let (low, high) = multiply::mac(word, rhs[j], dst[j], carry);
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
        {

            let ghost before = dst@;
            let ghost incoming = carry;
            let (low, high) = multiply::mac(word, rhs[j], dst[j], carry);
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
        {

            let ghost before = dst@;
            let ghost incoming = carry;
            let (low, high) = multiply::mac(word, rhs[j], dst[j], carry);
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
    }
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
        let (low, high) = multiply::mac(word, rhs[j], dst[j], carry);
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

}

//! Erased functional composition for compact inputs and an exact limb product.
use vstd::prelude::*;
use vstd::arithmetic::power::*;
use crate::{packed_convolution as convolution, packed_layout as layout};
use crate::radix::*;

verus! {

/// The independent input polynomial interpretation uses compact p-bit chunks.
pub open spec fn coefficients(words: Seq<u64>, count: nat, p: nat) -> Seq<int> {
    convolution::slots(words, layout::coefficient_limbs(p), count)
}

/// q is a sufficient exact output precision; empty inputs need no log bound.
pub open spec fn guard_domain(count: nat, p: nat, q: nat, slot: nat) -> bool {
    p > 0 && q > 0
        && slot >= layout::coefficient_limbs(p)
        && slot >= layout::coefficient_limbs(q)
        && (count == 0 || (q >= 2 * p && count <= pow(2, (q - 2 * p) as nat)))
}

pub open spec fn exact_output(
    output: Seq<u64>, left: Seq<u64>, right: Seq<u64>, count: nat, p: nat, q: nat,
) -> bool {
    layout::compact_coefficients(output, 2 * count, q)
        && coefficients(output, 2 * count, q)
            == convolution::convolution(
                coefficients(left, count, p), coefficients(right, count, p),
            )
        && (count == 0 || coefficients(output, 2 * count, q)[(2 * count - 1) as int] == 0)
}

/// Every complete limb slot is a canonical radix digit, regardless of its bits.
pub proof fn complete_slots_canonical(words: Seq<u64>, slot: nat, count: nat)
    requires count * slot == words.len(),
    ensures convolution::canonical(convolution::slots(words, slot, count), radix(slot)),
{
    radix_positive(slot);
    assert forall|i: int| 0 <= i < count as int
        implies 0 <= #[trigger] convolution::slots(words, slot, count)[i] < radix(slot) by {
        assert(i + 1 <= count);
        assert(0 <= i * slot) by(nonlinear_arith)
            requires i >= 0, slot >= 0;
        assert(i * slot <= (i + 1) * slot) by(nonlinear_arith)
            requires slot >= 0;
        assert((i + 1) * slot <= count * slot) by(nonlinear_arith)
            requires i + 1 <= count, slot >= 0;
        assert((i + 1) * slot <= words.len());
        assert((i + 1) * slot - i * slot == slot) by(nonlinear_arith);
        let chunk = words.subrange(i * slot, (i + 1) * slot);
        assert(chunk.len() == slot);
        prefix_range(chunk, slot);
    }
}

/// The product's integer meaning determines every exact convolution slot.
/// The expected polynomial is defined only from compact inputs, never output.
pub proof fn exact_product_slots(
    left: Seq<u64>, right: Seq<u64>, product: Seq<u64>,
    count: nat, p: nat, q: nat, slot: nat,
)
    requires
        guard_domain(count, p, q, slot),
        layout::compact_coefficients(left, count, p),
        layout::compact_coefficients(right, count, p),
        product.len() == 2 * count * slot,
        value(product)
            == convolution::packed(coefficients(left, count, p), radix(slot))
                * convolution::packed(coefficients(right, count, p), radix(slot)),
    ensures
        layout::canonical_packed_slots(product, 2 * count, q, slot),
        convolution::slots(product, slot, 2 * count)
            == convolution::convolution(
                coefficients(left, count, p), coefficients(right, count, p),
            ),
{
    let a = coefficients(left, count, p);
    let b = coefficients(right, count, p);
    let digits = convolution::slots(product, slot, 2 * count);
    let base = radix(slot);
    assert(a.len() == count && b.len() == count);
    assert(convolution::canonical(a, pow(2, p)));
    assert(convolution::canonical(b, pow(2, p)));
    complete_slots_canonical(product, slot, 2 * count);
    convolution::slots_integer(product, slot, 2 * count);
    lemma_pow_positive(2, q);
    if count > 0 {
        let g = (q - 2 * p) as nat;
        layout::coefficient_width_covers_precision(q);
        assert(q <= 64 * slot) by(nonlinear_arith)
            requires q <= 64 * layout::coefficient_limbs(q),
                slot >= layout::coefficient_limbs(q);
        assert(q == 2 * p + g);
        convolution::word_aligned_guard(a, b, p, g, slot);
        convolution::guard_bits(a, b, p, g, q);
        assert forall|k: int| 0 <= k < 2 * count as int
            implies #[trigger] digits[k] == convolution::coefficient(a, b, k as nat)
                && 0 <= digits[k] < pow(2, q) by {
            convolution::extract_digit(digits, base, k as nat);
            convolution::packed_convolution_extract(a, b, pow(2, p), base, k as nat);
            convolution::no_carry_bound(a, b, pow(2, p), pow(2, q), k as nat);
        }
    }
    assert(digits =~= convolution::convolution(a, b));
    assert(convolution::canonical(digits, pow(2, q)));
}

/// Extraction preserves the exact coefficients and gives the allocated zero tail.
pub proof fn extracted_exact_output(
    output: Seq<u64>, product: Seq<u64>, left: Seq<u64>, right: Seq<u64>,
    count: nat, p: nat, q: nat, slot: nat,
)
    requires
        q > 0,
        left.len() == count * layout::coefficient_limbs(p),
        right.len() == count * layout::coefficient_limbs(p),
        output.len() == 2 * count * layout::coefficient_limbs(q),
        layout::canonical_packed_slots(product, 2 * count, q, slot),
        layout::slots_equal(product, slot, output, layout::coefficient_limbs(q), 2 * count),
        convolution::slots(product, slot, 2 * count)
            == convolution::convolution(coefficients(left, count, p), coefficients(right, count, p)),
    ensures exact_output(output, left, right, count, p, q),
{
    let a = coefficients(left, count, p);
    let b = coefficients(right, count, p);
    let result = coefficients(output, 2 * count, q);
    assert(result =~= convolution::convolution(a, b));
    assert(convolution::canonical(result, pow(2, q)));
    if count > 0 {
        convolution::coefficient_zero(a, b, (2 * count - 1) as nat, count);
    }
}

} // verus!

//! Checked borrowed-slice layout conversion for packed coefficient slots.
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::power::*;
use crate::{packed_convolution, pow2};
use crate::radix::*;

verus! {

pub open spec fn coefficient_limbs(p: nat) -> nat {
    if p == 0 { 0 } else { ((p - 1) as nat) / 64 + 1 }
}

pub struct PackedLayout {
    pub coefficient_limbs: usize,
    pub source_words: usize,
    pub packed_words: usize,
}

pub enum PackedLayoutError {
    InvalidPrecision,
    SlotTooNarrow,
    LengthOverflow,
    SourceLengthMismatch,
    DestinationLengthMismatch,
}

/// Relate the existing precision helper to the mathematical limb width.
pub proof fn precision_layout_interpretation(bits: usize, limbs: usize, top: u32)
    requires
        bits > 0,
        limbs > 0,
        1 <= top <= 64,
        crate::precision::bit_precision(limbs as nat, top as nat) == bits as nat,
    ensures
        limbs as nat == coefficient_limbs(bits as nat),
{
    lemma_fundamental_div_mod((bits - 1) as int, 64);
    assert((bits - 1) as int == 64 * ((limbs - 1) as int) + (top - 1) as int)
        by(nonlinear_arith)
        requires
            crate::precision::bit_precision(limbs as nat, top as nat) == bits as nat,
            limbs > 0,
            1 <= top <= 64;
    assert(((top - 1) as int) < 64);
    assert(((bits - 1) as int) / 64 == (limbs - 1) as int)
        by(nonlinear_arith)
        requires
            (bits - 1) as int == 64 * ((limbs - 1) as int) + (top - 1) as int,
            0 <= ((top - 1) as int) < 64;
    assert(((bits - 1) as int) % 64 == (top - 1) as int)
        by(nonlinear_arith)
        requires
            (bits - 1) as int == 64 * ((limbs - 1) as int) + (top - 1) as int,
            0 <= ((top - 1) as int) < 64;
}

/// Validate precision and checked buffer sizes before either conversion writes.
pub fn checked_layout(count: usize, precision_bits: usize, slot_limbs: usize)
    -> (out: Result<PackedLayout, PackedLayoutError>)
    ensures match out {
        Ok(layout) =>
            precision_bits > 0
                && layout.coefficient_limbs as nat == coefficient_limbs(precision_bits as nat)
                && slot_limbs >= layout.coefficient_limbs
                && layout.source_words as int
                    == count as int * layout.coefficient_limbs as int
                && layout.packed_words as int == count as int * slot_limbs as int
                && layout.source_words as int <= usize::MAX as int
                && layout.packed_words as int <= usize::MAX as int,
        Err(PackedLayoutError::InvalidPrecision) => precision_bits == 0,
        Err(PackedLayoutError::SlotTooNarrow) =>
            precision_bits > 0 && (slot_limbs as nat) < coefficient_limbs(precision_bits as nat),
        Err(PackedLayoutError::LengthOverflow) =>
            precision_bits > 0
                && slot_limbs as nat >= coefficient_limbs(precision_bits as nat)
                && (count as int * coefficient_limbs(precision_bits as nat) as int
                        > usize::MAX as int
                    || count as int * slot_limbs as int > usize::MAX as int),
        Err(PackedLayoutError::SourceLengthMismatch)
        | Err(PackedLayoutError::DestinationLengthMismatch) => false,
    },
{
    if precision_bits == 0 {
        return Err(PackedLayoutError::InvalidPrecision);
    }
    let (coefficient_limbs, top_bits) = pow2::precision_layout(precision_bits);
    proof { precision_layout_interpretation(precision_bits, coefficient_limbs, top_bits); }
    if slot_limbs < coefficient_limbs {
        return Err(PackedLayoutError::SlotTooNarrow);
    }
    if count > usize::MAX / coefficient_limbs || count > usize::MAX / slot_limbs {
        proof {
            if count > usize::MAX / coefficient_limbs {
                lemma_fundamental_div_mod(usize::MAX as int, coefficient_limbs as int);
                assert(count as int * coefficient_limbs as int > usize::MAX as int)
                    by(nonlinear_arith)
                    requires
                        coefficient_limbs > 0,
                        count > usize::MAX / coefficient_limbs,
                        usize::MAX as int
                            == (usize::MAX as int / coefficient_limbs as int)
                                * coefficient_limbs as int
                                + (usize::MAX as int % coefficient_limbs as int);
            }
            if count > usize::MAX / slot_limbs {
                lemma_fundamental_div_mod(usize::MAX as int, slot_limbs as int);
                assert(count as int * slot_limbs as int > usize::MAX as int)
                    by(nonlinear_arith)
                    requires
                        slot_limbs > 0,
                        count > usize::MAX / slot_limbs,
                        usize::MAX as int
                            == (usize::MAX as int / slot_limbs as int) * slot_limbs as int
                                + (usize::MAX as int % slot_limbs as int);
            }
        }
        return Err(PackedLayoutError::LengthOverflow);
    }
    let source_words = count * coefficient_limbs;
    let packed_words = count * slot_limbs;
    proof {
        assert(source_words as int == count as int * coefficient_limbs as int);
        assert(packed_words as int == count as int * slot_limbs as int);
    }
    Ok(PackedLayout { coefficient_limbs, source_words, packed_words })
}

pub proof fn zero_prefix(words: Seq<u64>, n: nat)
    requires
        n <= words.len(),
        forall|i: int| 0 <= i < n ==> words[i] == 0,
    ensures prefix(words, n) == 0,
    decreases n,
{
    if n > 0 {
        zero_prefix(words, (n - 1) as nat);
        assert(prefix(words, n) == prefix(words, (n - 1) as nat)
            + (words[n - 1] as int) * radix((n - 1) as nat));
    }
}

/// Prove a padded slot has the value of its compact coefficient chunk.
pub proof fn padded_slot_value(
    packed: Seq<u64>, source: Seq<u64>, packed_start: nat, source_start: nat,
    coefficient_words: nat, slot_words: nat,
)
    requires
        coefficient_words <= slot_words,
        packed_start + slot_words <= packed.len(),
        source_start + coefficient_words <= source.len(),
        forall|j: int| 0 <= j < coefficient_words as int
            ==> packed[packed_start as int + j] == source[source_start as int + j],
        forall|j: int| coefficient_words as int <= j < slot_words as int
            ==> packed[packed_start as int + j] == 0,
    ensures
        value(packed.subrange(packed_start as int,
            (packed_start + slot_words) as int))
            == value(source.subrange(source_start as int,
                (source_start + coefficient_words) as int)),
{
    let dst_slot = packed.subrange(packed_start as int, (packed_start + slot_words) as int);
    let src_coefficient = source.subrange(source_start as int,
        (source_start + coefficient_words) as int);
    let dst_low = dst_slot.subrange(0, coefficient_words as int);
    let dst_pad = dst_slot.subrange(coefficient_words as int, slot_words as int);
    assert forall|j: int| 0 <= j < coefficient_words as int
        implies dst_low[j] == src_coefficient[j] by {
        assert(dst_low[j] == packed[packed_start as int + j]);
        assert(src_coefficient[j] == source[source_start as int + j]);
    }
    equal_prefix(dst_low, src_coefficient, coefficient_words);
    zero_prefix(dst_pad, (slot_words - coefficient_words) as nat);
    crate::product::subrange_value(
        dst_slot, coefficient_words, (slot_words - coefficient_words) as nat,
    );
    assert(value(dst_low) == value(src_coefficient));
    assert(value(dst_slot) == prefix(dst_slot, slot_words));
    assert(value(dst_low) == prefix(dst_slot, coefficient_words));
    assert(value(dst_pad) == prefix(dst_slot.subrange(coefficient_words as int,
        slot_words as int), (slot_words - coefficient_words) as nat));
    assert(value(dst_slot) == value(dst_low)
        + radix(coefficient_words) * value(dst_pad)) by(nonlinear_arith);
    assert(value(dst_pad) == 0);
}

pub open spec fn compact_coefficients(src: Seq<u64>, count: nat, p: nat) -> bool {
    p > 0
        && count * coefficient_limbs(p) == src.len()
        && packed_convolution::canonical(
            packed_convolution::slots(src, coefficient_limbs(p), count),
            pow(2, p),
        )
}

pub open spec fn canonical_packed_slots(src: Seq<u64>, count: nat, p: nat, slot: nat) -> bool {
    p > 0
        && count * slot == src.len()
        && slot >= coefficient_limbs(p)
        && packed_convolution::canonical(
            packed_convolution::slots(src, slot, count),
            pow(2, p),
        )
        && forall|i: int, j: int| 0 <= #[trigger] i < count as int
            && coefficient_limbs(p) as int <= j < slot as int
            ==> src[#[trigger] (i * slot as int + j)] == 0
}

pub open spec fn slots_equal(
    left: Seq<u64>, left_slot: nat,
    right: Seq<u64>, right_slot: nat,
    count: nat,
) -> bool {
    count * left_slot <= left.len()
        && count * right_slot <= right.len()
        && forall|i: int| 0 <= i < count as int
            ==> packed_convolution::slots(left, left_slot, count)[i]
                == packed_convolution::slots(right, right_slot, count)[i]
}

pub open spec fn layout_lengths_fit(count: nat, p: nat, slot: nat) -> bool {
    p > 0
        && slot >= coefficient_limbs(p)
        && count * coefficient_limbs(p) <= usize::MAX as nat
        && count * slot <= usize::MAX as nat
}

pub open spec fn pack_error_matches(
    error: PackedLayoutError,
    count: nat,
    p: nat,
    slot: nat,
    source_words: nat,
    destination_words: nat,
) -> bool {
    match error {
        PackedLayoutError::InvalidPrecision => p == 0,
        PackedLayoutError::SlotTooNarrow => p > 0 && slot < coefficient_limbs(p),
        PackedLayoutError::LengthOverflow =>
            p > 0 && slot >= coefficient_limbs(p)
                && (count * coefficient_limbs(p) > usize::MAX as nat
                    || count * slot > usize::MAX as nat),
        PackedLayoutError::SourceLengthMismatch =>
            layout_lengths_fit(count, p, slot)
                && source_words != count * coefficient_limbs(p),
        PackedLayoutError::DestinationLengthMismatch =>
            layout_lengths_fit(count, p, slot)
                && source_words == count * coefficient_limbs(p)
                && destination_words != count * slot,
    }
}

pub open spec fn extract_error_matches(
    error: PackedLayoutError,
    count: nat,
    p: nat,
    slot: nat,
    source_words: nat,
    destination_words: nat,
) -> bool {
    match error {
        PackedLayoutError::InvalidPrecision => p == 0,
        PackedLayoutError::SlotTooNarrow => p > 0 && slot < coefficient_limbs(p),
        PackedLayoutError::LengthOverflow =>
            p > 0 && slot >= coefficient_limbs(p)
                && (count * coefficient_limbs(p) > usize::MAX as nat
                    || count * slot > usize::MAX as nat),
        PackedLayoutError::SourceLengthMismatch =>
            layout_lengths_fit(count, p, slot) && source_words != count * slot,
        PackedLayoutError::DestinationLengthMismatch =>
            layout_lengths_fit(count, p, slot)
                && source_words == count * slot
                && destination_words != count * coefficient_limbs(p),
    }
}

pub proof fn slot_entry(words: Seq<u64>, slot_words: nat, count: nat, i: nat)
    requires count * slot_words <= words.len(), i < count,
    ensures packed_convolution::slots(words, slot_words, count)[i as int]
        == value(words.subrange((i * slot_words) as int,
            ((i + 1) * slot_words) as int)),
{
    reveal(packed_convolution::slots);
}

/// Expand compact p-bit coefficient chunks into zero-padded contiguous slots.
/// Canonical coefficient representatives are a caller-side representation
/// invariant, so the executable path does not rescan their values.
pub fn pack_coefficients(
    dst: &mut [u64],
    src: &[u64],
    count: usize,
    precision_bits: usize,
    slot_limbs: usize,
) -> (out: Result<(), PackedLayoutError>)
    requires
        (precision_bits > 0
            && slot_limbs as nat >= coefficient_limbs(precision_bits as nat)
            && count as int * coefficient_limbs(precision_bits as nat) as int
                <= usize::MAX as int
            && src@.len() == count as int * coefficient_limbs(precision_bits as nat) as int)
            ==> compact_coefficients(src@, count as nat, precision_bits as nat),
    ensures
        match out {
            Ok(()) =>
                precision_bits > 0
                    && slot_limbs as nat >= coefficient_limbs(precision_bits as nat)
                    && compact_coefficients(src@, count as nat, precision_bits as nat)
                    && src@.len() == count as int * coefficient_limbs(precision_bits as nat) as int
                    && old(dst)@.len() == count as int * slot_limbs as int
                    && final(dst)@.len() == old(dst)@.len()
                    && slots_equal(
                        final(dst)@, slot_limbs as nat,
                        src@, coefficient_limbs(precision_bits as nat), count as nat,
                    )
                    && forall|i: int, j: int| 0 <= i < count as int
                        && coefficient_limbs(precision_bits as nat) as int <= j < slot_limbs as int
                        ==> final(dst)@[i * slot_limbs as int + j] == 0,
            Err(error) =>
                pack_error_matches(
                    error,
                    count as nat,
                    precision_bits as nat,
                    slot_limbs as nat,
                    src@.len() as nat,
                    old(dst)@.len() as nat,
                ) && final(dst)@ == old(dst)@,
        },
{
    let layout = match checked_layout(count, precision_bits, slot_limbs) {
        Ok(layout) => layout,
        Err(error) => return Err(error),
    };
    if src.len() != layout.source_words {
        return Err(PackedLayoutError::SourceLengthMismatch);
    }
    if dst.len() != layout.packed_words {
        return Err(PackedLayoutError::DestinationLengthMismatch);
    }

    assert!(src.len() == layout.source_words && dst.len() == layout.packed_words);
    let mut source_pos = 0usize;
    let mut destination_pos = 0usize;
    let mut coefficient = 0usize;
    let ghost mut copied_words: nat = 0;
    let ghost mut zeroed_words: nat = 0;
    while coefficient < count
        invariant
            coefficient <= count,
            source_pos == coefficient * layout.coefficient_limbs,
            destination_pos == coefficient * slot_limbs,
            source_pos <= layout.source_words,
            destination_pos <= layout.packed_words,
            src@.len() == layout.source_words as int,
            dst@.len() == layout.packed_words as int,
            copied_words == coefficient as nat * layout.coefficient_limbs as nat,
            zeroed_words == coefficient as nat
                * (slot_limbs - layout.coefficient_limbs) as nat,
            layout.source_words == count * layout.coefficient_limbs,
            layout.packed_words == count * slot_limbs,
            forall|i: int| 0 <= i < coefficient as int
                ==> packed_convolution::slots(dst@, slot_limbs as nat, count as nat)[i]
                    == packed_convolution::slots(
                        src@, layout.coefficient_limbs as nat, count as nat,
                    )[i],
            forall|i: int, j: int| 0 <= i < coefficient as int
                && layout.coefficient_limbs as int <= j < slot_limbs as int
                ==> dst@[i * slot_limbs as int + j] == 0,
        decreases count - coefficient,
    {
        assert(source_pos + layout.coefficient_limbs <= src.len());
        assert(destination_pos + layout.coefficient_limbs <= dst.len());
        crate::fast_words::copy_words(
            &mut dst[destination_pos..destination_pos + layout.coefficient_limbs],
            &src[source_pos..source_pos + layout.coefficient_limbs],
        );
        proof { copied_words = copied_words + layout.coefficient_limbs as nat; }
        let mut pad = layout.coefficient_limbs;
        while pad < slot_limbs
            invariant
                layout.coefficient_limbs <= pad <= slot_limbs,
                destination_pos == coefficient * slot_limbs,
                zeroed_words == coefficient as nat
                    * (slot_limbs - layout.coefficient_limbs) as nat
                    + (pad - layout.coefficient_limbs) as nat,
                forall|k: int| layout.coefficient_limbs as int <= k < pad as int
                    ==> dst@[destination_pos as int + k] == 0,
                forall|k: int| pad as int <= k < slot_limbs as int
                    ==> dst@[destination_pos as int + k]
                        == old(dst)@[destination_pos as int + k],
            decreases slot_limbs - pad,
        {
            dst[destination_pos + pad] = 0;
            pad += 1;
            proof { zeroed_words = zeroed_words + 1; }
        }
        proof {
            assert forall|k: int| 0 <= k < layout.coefficient_limbs as int
                implies dst@[destination_pos as int + k] == src@[source_pos as int + k] by {}
            assert forall|k: int|
                layout.coefficient_limbs as int <= k < slot_limbs as int
                implies dst@[destination_pos as int + k] == 0 by {}
            padded_slot_value(
                dst@, src@, destination_pos as nat, source_pos as nat,
                layout.coefficient_limbs as nat, slot_limbs as nat,
            );
            slot_entry(
                dst@, slot_limbs as nat, count as nat, coefficient as nat,
            );
            slot_entry(
                src@, layout.coefficient_limbs as nat, count as nat, coefficient as nat,
            );
            assert(packed_convolution::slots(dst@, slot_limbs as nat, count as nat)
                [coefficient as int]
                == packed_convolution::slots(
                    src@, layout.coefficient_limbs as nat, count as nat,
                )[coefficient as int]);
            assert(copied_words
                == (coefficient as nat + 1) * layout.coefficient_limbs as nat)
                by(nonlinear_arith);
            assert(zeroed_words
                == (coefficient as nat + 1)
                    * (slot_limbs - layout.coefficient_limbs) as nat)
                by(nonlinear_arith);
        }
        source_pos += layout.coefficient_limbs;
        destination_pos += slot_limbs;
        coefficient += 1;
    }
    proof {
        assert(copied_words == count as nat * layout.coefficient_limbs as nat);
        assert(zeroed_words
            == count as nat * (slot_limbs - layout.coefficient_limbs) as nat);
    }
    Ok(())
}

/// Compact the coefficient limbs from canonical zero-padded slots.
/// The input slot interpretation is a caller-side representation invariant.
pub fn extract_coefficients(
    dst: &mut [u64],
    src: &[u64],
    count: usize,
    precision_bits: usize,
    slot_limbs: usize,
) -> (out: Result<(), PackedLayoutError>)
    requires
        (precision_bits > 0
            && slot_limbs as nat >= coefficient_limbs(precision_bits as nat)
            && count as int * slot_limbs as int <= usize::MAX as int
            && src@.len() == count as int * slot_limbs as int)
            ==> canonical_packed_slots(
                src@, count as nat, precision_bits as nat, slot_limbs as nat,
            ),
    ensures
        match out {
            Ok(()) =>
                precision_bits > 0
                    && slot_limbs as nat >= coefficient_limbs(precision_bits as nat)
                    && canonical_packed_slots(
                        src@, count as nat, precision_bits as nat, slot_limbs as nat,
                    )
                    && old(dst)@.len()
                        == count as int * coefficient_limbs(precision_bits as nat) as int
                    && src@.len() == count as int * slot_limbs as int
                    && final(dst)@.len() == old(dst)@.len()
                    && slots_equal(
                        src@, slot_limbs as nat,
                        final(dst)@, coefficient_limbs(precision_bits as nat), count as nat,
                    ),
            Err(error) =>
                extract_error_matches(
                    error,
                    count as nat,
                    precision_bits as nat,
                    slot_limbs as nat,
                    src@.len() as nat,
                    old(dst)@.len() as nat,
                ) && final(dst)@ == old(dst)@,
        },
{
    let layout = match checked_layout(count, precision_bits, slot_limbs) {
        Ok(layout) => layout,
        Err(error) => return Err(error),
    };
    if src.len() != layout.packed_words {
        return Err(PackedLayoutError::SourceLengthMismatch);
    }
    if dst.len() != layout.source_words {
        return Err(PackedLayoutError::DestinationLengthMismatch);
    }

    assert!(src.len() == layout.packed_words && dst.len() == layout.source_words);
    let mut source_pos = 0usize;
    let mut destination_pos = 0usize;
    let mut coefficient = 0usize;
    let ghost mut copied_words: nat = 0;
    while coefficient < count
        invariant
            coefficient <= count,
            source_pos == coefficient * slot_limbs,
            destination_pos == coefficient * layout.coefficient_limbs,
            source_pos <= layout.packed_words,
            destination_pos <= layout.source_words,
            src@.len() == layout.packed_words as int,
            dst@.len() == layout.source_words as int,
            copied_words == coefficient as nat * layout.coefficient_limbs as nat,
            layout.packed_words == count * slot_limbs,
            layout.source_words == count * layout.coefficient_limbs,
            forall|i: int| 0 <= i < coefficient as int
                ==> packed_convolution::slots(src@, slot_limbs as nat, count as nat)[i]
                    == packed_convolution::slots(
                        dst@, layout.coefficient_limbs as nat, count as nat,
                    )[i],
        decreases count - coefficient,
    {
        assert(source_pos + layout.coefficient_limbs <= src.len());
        assert(destination_pos + layout.coefficient_limbs <= dst.len());
        crate::fast_words::copy_words(
            &mut dst[destination_pos..destination_pos + layout.coefficient_limbs],
            &src[source_pos..source_pos + layout.coefficient_limbs],
        );
        proof { copied_words = copied_words + layout.coefficient_limbs as nat; }
        proof {
            assert forall|k: int| 0 <= k < layout.coefficient_limbs as int
                implies dst@[destination_pos as int + k] == src@[source_pos as int + k] by {}
            assert forall|k: int|
                layout.coefficient_limbs as int <= k < slot_limbs as int
                implies src@[source_pos as int + k] == 0 by {
                assert(src@[source_pos as int + k]
                    == src@[coefficient as int * slot_limbs as int + k]);
            }
            padded_slot_value(
                src@, dst@, source_pos as nat, destination_pos as nat,
                layout.coefficient_limbs as nat, slot_limbs as nat,
            );
            slot_entry(
                src@, slot_limbs as nat, count as nat, coefficient as nat,
            );
            slot_entry(
                dst@, layout.coefficient_limbs as nat, count as nat, coefficient as nat,
            );
            assert(packed_convolution::slots(src@, slot_limbs as nat, count as nat)
                [coefficient as int]
                == packed_convolution::slots(
                    dst@, layout.coefficient_limbs as nat, count as nat,
                )[coefficient as int]);
            assert(copied_words
                == (coefficient as nat + 1) * layout.coefficient_limbs as nat)
                by(nonlinear_arith);
        }
        source_pos += slot_limbs;
        destination_pos += layout.coefficient_limbs;
        coefficient += 1;
    }
    proof { assert(copied_words == count as nat * layout.coefficient_limbs as nat); }
    Ok(())
}

} // verus!

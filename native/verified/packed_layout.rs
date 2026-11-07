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
    let source_words = match count.checked_mul(coefficient_limbs) {
        Some(words) => words,
        None => return Err(PackedLayoutError::LengthOverflow),
    };
    let packed_words = match count.checked_mul(slot_limbs) {
        Some(words) => words,
        None => return Err(PackedLayoutError::LengthOverflow),
    };
    Ok(PackedLayout { coefficient_limbs, source_words, packed_words })
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
}

pub open spec fn slots_equal(
    left: Seq<u64>, left_slot: nat,
    right: Seq<u64>, right_slot: nat,
    count: nat,
) -> bool {
    count * left_slot <= left.len()
        && count * right_slot <= right.len()
        && forall|i: int| 0 <= i < count as int
            ==> #[trigger] packed_convolution::slots(left, left_slot, count)[i]
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

proof fn equal_subrange_from_prefix<T>(
    left: Seq<T>, right: Seq<T>, prefix: int, start: int, end: int,
)
    requires
        left.len() == right.len(),
        0 <= start <= end <= prefix <= left.len(),
        left.subrange(0, prefix) == right.subrange(0, prefix),
    ensures left.subrange(start, end) == right.subrange(start, end),
{
    assert(left.subrange(0, prefix).subrange(start, end)
        == right.subrange(0, prefix).subrange(start, end));
    assert(left.subrange(0, prefix).subrange(start, end)
        == left.subrange(start, end));
    assert(right.subrange(0, prefix).subrange(start, end)
        == right.subrange(start, end));
}

proof fn slot_range_before_end(i: nat, width: nat, count: nat)
    requires i < count,
    ensures
        0 <= (i * width) as int
            <= ((i + 1) * width) as int
            <= (count * width) as int,
{
    assert(i + 1 <= count) by(nonlinear_arith)
        requires i < count;
    assert(i * width <= (i + 1) * width) by(nonlinear_arith);
    assert((i + 1) * width <= count * width) by(nonlinear_arith)
        requires i + 1 <= count;
}

pub proof fn coefficient_width_covers_precision(p: nat)
    requires p > 0,
    ensures p <= 64 * coefficient_limbs(p),
{
    lemma_fundamental_div_mod((p - 1) as int, 64);
    assert(coefficient_limbs(p) == ((p - 1) as nat) / 64 + 1);
    assert(((p - 1) as int) == 64 * (((p - 1) as int) / 64)
        + (((p - 1) as int) % 64));
    assert(0 <= ((p - 1) as int) % 64 < 64) by(nonlinear_arith)
        requires p > 0;
    assert(p as int <= 64 * coefficient_limbs(p) as int) by(nonlinear_arith)
        requires
            ((p - 1) as int) == 64 * (((p - 1) as int) / 64)
                + (((p - 1) as int) % 64),
            0 <= ((p - 1) as int) % 64 < 64,
            coefficient_limbs(p) as int == (((p - 1) as int) / 64) + 1;
}

pub proof fn canonical_slot_low_value(words: Seq<u64>, p: nat, coefficient_words: nat)
    requires
        p > 0,
        coefficient_words == coefficient_limbs(p),
        coefficient_words <= words.len(),
        0 <= value(words) < pow(2, p),
    ensures value(words) == value(words.subrange(0, coefficient_words as int)),
{
    coefficient_width_covers_precision(p);
    let slack = (64 * coefficient_words - p) as nat;
    assert(64 * coefficient_words - p >= 0) by(nonlinear_arith)
        requires coefficient_words == coefficient_limbs(p),
            p <= 64 * coefficient_limbs(p);
    assert(slack as int == 64 * coefficient_words as int - p as int)
        by(nonlinear_arith)
        requires
            slack == (64 * coefficient_words - p) as nat,
            p <= 64 * coefficient_words;
    assert((p + slack) as int == 64 * coefficient_words as int)
        by(nonlinear_arith)
        requires slack as int == 64 * coefficient_words as int - p as int;
    assert(p + slack == 64 * coefficient_words) by(nonlinear_arith)
        requires (p + slack) as int == 64 * coefficient_words as int;
    lemma_pow_adds(2, p, slack);
    lemma_pow_positive(2, slack);
    lemma_pow_positive(2, p);
    crate::radix::radix_is_power_of_two(coefficient_words);
    assert(pow(2, p + slack) == pow(2, p) * pow(2, slack));
    assert(pow(2, slack) >= 1);
    assert(pow(2, p) <= pow(2, p) * pow(2, slack)) by(nonlinear_arith)
        requires pow(2, p) > 0, pow(2, slack) >= 1;
    assert(pow(2, p + slack) == pow(2, 64 * coefficient_words));
    assert(pow(2, p) <= radix(coefficient_words)) by(nonlinear_arith)
        requires
            pow(2, p) <= pow(2, p + slack),
            radix(coefficient_words) == pow(2, 64 * coefficient_words),
            p + slack == 64 * coefficient_words;
    crate::fast_product::split(words, coefficient_words);
    crate::radix::prefix_range(words, coefficient_words);
    let upper = words.subrange(coefficient_words as int, words.len() as int);
    crate::radix::prefix_range(upper, (words.len() - coefficient_words) as nat);
    assert(value(words) == value(words.subrange(0, coefficient_words as int))
        + radix(coefficient_words) * value(upper));
    assert(value(words) < radix(coefficient_words)) by(nonlinear_arith)
        requires 0 <= value(words) < pow(2, p), pow(2, p) <= radix(coefficient_words);
    assert(value(upper) == 0) by {
        if value(upper) > 0 {
            assert(value(upper) >= 1);
            assert(value(words) >= radix(coefficient_words)) by(nonlinear_arith)
                requires
                    value(words) == value(words.subrange(0, coefficient_words as int))
                        + radix(coefficient_words) * value(upper),
                    value(words.subrange(0, coefficient_words as int)) >= 0,
                    radix(coefficient_words) > 0,
                    value(upper) >= 1;
            assert(false) by(nonlinear_arith)
                requires value(words) < radix(coefficient_words),
                    value(words) >= radix(coefficient_words);
        }
    }
    assert(value(words) == value(words.subrange(0, coefficient_words as int)))
        by(nonlinear_arith)
        requires
            value(words) == value(words.subrange(0, coefficient_words as int))
                + radix(coefficient_words) * value(upper),
            value(upper) == 0;
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
                    && canonical_packed_slots(
                        final(dst)@, count as nat, precision_bits as nat, slot_limbs as nat,
                    )
                    && slots_equal(
                        final(dst)@, slot_limbs as nat,
                        src@, coefficient_limbs(precision_bits as nat), count as nat,
                    ),
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
        Ok(layout) => {
            assert(precision_bits > 0);
            assert(layout.coefficient_limbs as nat
                == coefficient_limbs(precision_bits as nat));
            layout
        },
        Err(error) => return Err(error),
    };
    if src.len() != layout.source_words {
        return Err(PackedLayoutError::SourceLengthMismatch);
    }
    if dst.len() != layout.packed_words {
        return Err(PackedLayoutError::DestinationLengthMismatch);
    }

    assert!(src.len() == layout.source_words && dst.len() == layout.packed_words);
    assert!(layout.coefficient_limbs > 0 && slot_limbs > 0);
    assert(slot_limbs as int > 0);
    assert(slot_limbs >= layout.coefficient_limbs);
    assert(compact_coefficients(src@, count as nat, precision_bits as nat));
    let mut source_pos = 0usize;
    let mut destination_pos = 0usize;
    let mut coefficient = 0usize;
    let ghost mut copied_words: nat = 0;
    let ghost mut written_words: nat = 0;
    let ghost mut zeroed_words: nat = 0;
    let ghost padding_words = (slot_limbs - layout.coefficient_limbs) as nat;
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
            written_words == coefficient as nat * slot_limbs as nat,
            zeroed_words == coefficient as nat * padding_words,
            layout.source_words == count * layout.coefficient_limbs,
            layout.packed_words == count * slot_limbs,
            slot_limbs >= layout.coefficient_limbs,
            forall|i: int| 0 <= i < coefficient as int
                ==> #[trigger] packed_convolution::slots(dst@, slot_limbs as nat, count as nat)[i]
                    == packed_convolution::slots(
                        src@, layout.coefficient_limbs as nat, count as nat,
                    )[i],
        decreases count - coefficient,
    {
        assert(source_pos + layout.coefficient_limbs <= src.len()) by(nonlinear_arith)
            requires source_pos == coefficient * layout.coefficient_limbs,
                coefficient < count, src.len() == count * layout.coefficient_limbs;
        assert(destination_pos + slot_limbs <= dst.len()) by(nonlinear_arith)
            requires destination_pos == coefficient * slot_limbs,
                coefficient < count, dst.len() == count * slot_limbs;
        let ghost before_dst = dst@;
        let dst_slot = &mut dst[destination_pos..destination_pos + slot_limbs];
        let src_coefficient = &src[source_pos..source_pos + layout.coefficient_limbs];
        assert(dst_slot.len() == slot_limbs);
        assert(src_coefficient.len() == layout.coefficient_limbs);
        assert(dst_slot.len() >= src_coefficient.len()) by(nonlinear_arith)
            requires
                dst_slot.len() == slot_limbs,
                src_coefficient.len() == layout.coefficient_limbs,
                slot_limbs >= layout.coefficient_limbs;
        crate::toom_words::copy_pad(dst_slot, src_coefficient);
        proof {
            copied_words = copied_words + layout.coefficient_limbs as nat;
            written_words = written_words + slot_limbs as nat;
            zeroed_words = zeroed_words + padding_words;
        }
        proof {
            assert(destination_pos as int == coefficient as int * slot_limbs as int)
                by(nonlinear_arith)
                requires destination_pos == coefficient * slot_limbs,
                    coefficient < count,
                    count * slot_limbs <= usize::MAX;
            assert((destination_pos + slot_limbs) as int
                == (coefficient as int + 1) * slot_limbs as int)
                by(nonlinear_arith)
                requires destination_pos == coefficient * slot_limbs,
                    destination_pos + slot_limbs <= dst.len(),
                    dst.len() <= usize::MAX;
            assert(source_pos as int
                == coefficient as int * layout.coefficient_limbs as int)
                by(nonlinear_arith)
                requires source_pos == coefficient * layout.coefficient_limbs,
                    coefficient < count,
                    count * layout.coefficient_limbs <= usize::MAX;
            assert((source_pos + layout.coefficient_limbs) as int
                == (coefficient as int + 1) * layout.coefficient_limbs as int)
                by(nonlinear_arith)
                requires source_pos == coefficient * layout.coefficient_limbs,
                    source_pos + layout.coefficient_limbs <= src.len(),
                    src.len() <= usize::MAX;
            assert((coefficient as nat) as int == coefficient as int);
            assert((coefficient as nat * slot_limbs as nat) as int
                == coefficient as int * slot_limbs as int) by(nonlinear_arith);
            assert(((coefficient as nat + 1) * slot_limbs as nat) as int
                == (coefficient as int + 1) * slot_limbs as int) by(nonlinear_arith);
            assert((coefficient as nat * layout.coefficient_limbs as nat) as int
                == coefficient as int * layout.coefficient_limbs as int)
                by(nonlinear_arith);
            assert(((coefficient as nat + 1) * layout.coefficient_limbs as nat) as int
                == (coefficient as int + 1) * layout.coefficient_limbs as int)
                by(nonlinear_arith);
            assert(value(dst_slot@) == value(src_coefficient@));
            assert(dst@.subrange(destination_pos as int,
                (destination_pos + slot_limbs) as int) == dst_slot@);
            assert(src@.subrange(source_pos as int,
                (source_pos + layout.coefficient_limbs) as int) == src_coefficient@);
            crate::radix::equal_prefix(
                dst@.subrange(destination_pos as int,
                    (destination_pos + slot_limbs) as int),
                dst_slot@,
                slot_limbs as nat,
            );
            crate::radix::equal_prefix(
                src@.subrange(source_pos as int,
                    (source_pos + layout.coefficient_limbs) as int),
                src_coefficient@,
                layout.coefficient_limbs as nat,
            );
            assert(value(dst@.subrange(destination_pos as int,
                (destination_pos + slot_limbs) as int)) == value(dst_slot@));
            assert(value(src@.subrange(source_pos as int,
                (source_pos + layout.coefficient_limbs) as int))
                == value(src_coefficient@));
            crate::radix::prefix_range(
                dst@.subrange(destination_pos as int,
                    (destination_pos + slot_limbs) as int), slot_limbs as nat,
            );
            crate::radix::prefix_range(
                src@.subrange(source_pos as int,
                    (source_pos + layout.coefficient_limbs) as int),
                layout.coefficient_limbs as nat,
            );
            slot_entry(
                dst@, slot_limbs as nat, count as nat, coefficient as nat,
            );
            assert(packed_convolution::slots(
                dst@, slot_limbs as nat, count as nat,
            )[coefficient as int] == value(dst_slot@));
            slot_entry(
                src@, layout.coefficient_limbs as nat, count as nat, coefficient as nat,
            );
            assert(packed_convolution::slots(
                src@, layout.coefficient_limbs as nat, count as nat,
            )[coefficient as int] == value(src_coefficient@));
            assert(packed_convolution::slots(dst@, slot_limbs as nat, count as nat)
                [coefficient as int]
                == packed_convolution::slots(
                    src@, layout.coefficient_limbs as nat, count as nat,
                )[coefficient as int]);
            assert(dst@.subrange(0, destination_pos as int)
                == before_dst.subrange(0, destination_pos as int));
            assert forall|i: int| 0 <= i < (coefficient + 1) as int
                implies #[trigger] packed_convolution::slots(
                    dst@, slot_limbs as nat, count as nat,
                )[i] == packed_convolution::slots(
                    src@, layout.coefficient_limbs as nat, count as nat,
                )[i] by {
                if i < coefficient as int {
                    assert((i as nat) as int == i);
                    assert((coefficient as nat) as int == coefficient as int);
                    assert((slot_limbs as nat) as int == slot_limbs as int);
                    assert((destination_pos as nat) as int == destination_pos as int);
                    assert((i as nat) < (coefficient as nat)) by(nonlinear_arith)
                        requires
                            0 <= i < coefficient as int,
                            (i as nat) as int == i,
                            (coefficient as nat) as int == coefficient as int;
                    slot_range_before_end(
                        i as nat, slot_limbs as nat, coefficient as nat,
                    );
                    assert(destination_pos as nat
                        == coefficient as nat * slot_limbs as nat)
                        by(nonlinear_arith)
                        requires
                            destination_pos == coefficient * slot_limbs,
                            (destination_pos as nat) as int == destination_pos as int,
                            (coefficient as nat) as int == coefficient as int,
                            (slot_limbs as nat) as int == slot_limbs as int;
                    let slot_start = (i as nat * slot_limbs as nat) as int;
                    let slot_end = ((i as nat + 1) * slot_limbs as nat) as int;
                    assert(0 <= slot_start);
                    assert(slot_start <= slot_end);
                    assert(slot_end <= (coefficient as nat * slot_limbs as nat) as int);
                    assert(slot_end <= (destination_pos as nat) as int);
                    assert(slot_end <= destination_pos as int);
                    equal_subrange_from_prefix(
                        dst@, before_dst, destination_pos as int, slot_start, slot_end,
                    );
                    slot_entry(dst@, slot_limbs as nat, count as nat, i as nat);
                    slot_entry(before_dst, slot_limbs as nat, count as nat, i as nat);
                    assert(value(dst@.subrange(slot_start, slot_end))
                        == value(before_dst.subrange(slot_start, slot_end)));
                    assert(packed_convolution::slots(
                        dst@, slot_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        before_dst, slot_limbs as nat, count as nat,
                    )[i]);
                    assert(packed_convolution::slots(
                        before_dst, slot_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        src@, layout.coefficient_limbs as nat, count as nat,
                    )[i]);
                    assert(packed_convolution::slots(
                        dst@, slot_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        src@, layout.coefficient_limbs as nat, count as nat,
                    )[i]);
                } else {
                    assert(i == coefficient as int);
                    assert(packed_convolution::slots(
                        dst@, slot_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        src@, layout.coefficient_limbs as nat, count as nat,
                    )[i]);
                }
            }
            assert(copied_words
                == coefficient as nat * layout.coefficient_limbs as nat
                    + layout.coefficient_limbs as nat);
            assert(written_words
                == coefficient as nat * slot_limbs as nat + slot_limbs as nat);
            assert(zeroed_words
                == coefficient as nat
                    * padding_words + padding_words);
            assert((coefficient as nat + 1) * padding_words
                == coefficient as nat * padding_words + padding_words)
                by(nonlinear_arith);
            assert((coefficient as nat + 1) * layout.coefficient_limbs as nat
                == coefficient as nat * layout.coefficient_limbs as nat
                    + layout.coefficient_limbs as nat) by(nonlinear_arith);
            assert((coefficient as nat + 1) * slot_limbs as nat
                == coefficient as nat * slot_limbs as nat + slot_limbs as nat)
                by(nonlinear_arith);
        }
        source_pos += layout.coefficient_limbs;
        destination_pos += slot_limbs;
        coefficient += 1;
    }
    proof {
        assert(copied_words == count as nat * layout.coefficient_limbs as nat);
        assert(written_words == count as nat * slot_limbs as nat);
        assert(zeroed_words == count as nat * padding_words);
        assert forall|i: int| 0 <= i < count as int
            implies #[trigger] packed_convolution::slots(dst@, slot_limbs as nat, count as nat)[i]
                == packed_convolution::slots(
                    src@, layout.coefficient_limbs as nat, count as nat,
                )[i] by {
            assert(0 <= i < count as int);
        }
        reveal(compact_coefficients);
        assert(packed_convolution::canonical(
            packed_convolution::slots(
                src@, layout.coefficient_limbs as nat, count as nat,
            ),
            pow(2, precision_bits as nat),
        ));
        assert forall|i: int| 0 <= i < count as int
            implies 0 <= #[trigger] packed_convolution::slots(
                dst@, slot_limbs as nat, count as nat,
            )[i] < pow(2, precision_bits as nat) by {
            assert(packed_convolution::slots(
                dst@, slot_limbs as nat, count as nat,
            )[i] == packed_convolution::slots(
                src@, layout.coefficient_limbs as nat, count as nat,
            )[i]);
            assert(0 <= packed_convolution::slots(
                src@, layout.coefficient_limbs as nat, count as nat,
            )[i] < pow(2, precision_bits as nat));
        }
        reveal(canonical_packed_slots);
        assert(slot_limbs as nat >= coefficient_limbs(precision_bits as nat));
        assert(count as nat * slot_limbs as nat == dst@.len() as nat);
        assert(canonical_packed_slots(
            dst@, count as nat, precision_bits as nat, slot_limbs as nat,
        ));
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
        Ok(layout) => {
            assert(precision_bits > 0);
            assert(layout.coefficient_limbs as nat
                == coefficient_limbs(precision_bits as nat));
            layout
        },
        Err(error) => return Err(error),
    };
    if src.len() != layout.packed_words {
        return Err(PackedLayoutError::SourceLengthMismatch);
    }
    if dst.len() != layout.source_words {
        return Err(PackedLayoutError::DestinationLengthMismatch);
    }

    assert!(src.len() == layout.packed_words && dst.len() == layout.source_words);
    assert!(layout.coefficient_limbs > 0 && slot_limbs > 0);
    assert(layout.coefficient_limbs as int > 0);
    assert(slot_limbs >= layout.coefficient_limbs);
    assert(canonical_packed_slots(
        src@, count as nat, precision_bits as nat, slot_limbs as nat,
    ));
    assert(count as int * slot_limbs as int <= usize::MAX as int);
    let mut source_pos = 0usize;
    let mut destination_pos = 0usize;
    let mut coefficient = 0usize;
    let ghost mut copied_words: nat = 0;
    let ghost mut written_words: nat = 0;
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
            written_words == coefficient as nat * layout.coefficient_limbs as nat,
            canonical_packed_slots(
                src@, count as nat, precision_bits as nat, slot_limbs as nat,
            ),
            layout.packed_words == count * slot_limbs,
            layout.source_words == count * layout.coefficient_limbs,
            layout.coefficient_limbs as nat == coefficient_limbs(precision_bits as nat),
            slot_limbs >= layout.coefficient_limbs,
            forall|i: int| 0 <= i < coefficient as int
                ==> #[trigger] packed_convolution::slots(src@, slot_limbs as nat, count as nat)[i]
                    == packed_convolution::slots(
                        dst@, layout.coefficient_limbs as nat, count as nat,
                    )[i],
        decreases count - coefficient,
    {
        assert(source_pos + slot_limbs <= src.len()) by(nonlinear_arith)
            requires source_pos == coefficient * slot_limbs,
                coefficient < count, src.len() == count * slot_limbs;
        assert(source_pos + layout.coefficient_limbs <= src.len())
            by(nonlinear_arith)
            requires source_pos + slot_limbs <= src.len(),
                layout.coefficient_limbs <= slot_limbs;
        assert(destination_pos + layout.coefficient_limbs <= dst.len()) by(nonlinear_arith)
            requires destination_pos == coefficient * layout.coefficient_limbs,
                coefficient < count, dst.len() == count * layout.coefficient_limbs;
        let ghost before_dst = dst@;
        let src_slot = &src[source_pos..source_pos + slot_limbs];
        let src_coefficient = &src[source_pos..source_pos + layout.coefficient_limbs];
        crate::fast_words::copy_words(
            &mut dst[destination_pos..destination_pos + layout.coefficient_limbs],
            src_coefficient,
        );
        proof {
            copied_words = copied_words + layout.coefficient_limbs as nat;
            written_words = written_words + layout.coefficient_limbs as nat;
        }
        proof {
            assert(source_pos as int == coefficient as int * slot_limbs as int)
                by(nonlinear_arith)
                requires source_pos == coefficient * slot_limbs,
                    coefficient < count,
                    count * slot_limbs <= usize::MAX;
            assert((source_pos + layout.coefficient_limbs) as int
                == coefficient as int * slot_limbs as int
                    + layout.coefficient_limbs as int)
                by(nonlinear_arith)
                requires source_pos == coefficient * slot_limbs,
                    source_pos + slot_limbs <= src.len(),
                    layout.coefficient_limbs <= slot_limbs,
                    src.len() <= usize::MAX;
            assert((source_pos + slot_limbs) as int
                == (coefficient as int + 1) * slot_limbs as int)
                by(nonlinear_arith)
                requires source_pos == coefficient * slot_limbs,
                    source_pos + slot_limbs <= src.len(),
                    src.len() <= usize::MAX;
            assert(destination_pos as int
                == coefficient as int * layout.coefficient_limbs as int)
                by(nonlinear_arith)
                requires destination_pos == coefficient * layout.coefficient_limbs,
                    coefficient < count,
                    count * layout.coefficient_limbs <= usize::MAX;
            assert((destination_pos + layout.coefficient_limbs) as int
                == (coefficient as int + 1) * layout.coefficient_limbs as int)
                by(nonlinear_arith)
                requires destination_pos == coefficient * layout.coefficient_limbs,
                    destination_pos + layout.coefficient_limbs <= dst.len(),
                    dst.len() <= usize::MAX;
            assert((coefficient as nat) as int == coefficient as int);
            assert((coefficient as nat * slot_limbs as nat) as int
                == coefficient as int * slot_limbs as int) by(nonlinear_arith);
            assert(((coefficient as nat + 1) * slot_limbs as nat) as int
                == (coefficient as int + 1) * slot_limbs as int) by(nonlinear_arith);
            assert((coefficient as nat * layout.coefficient_limbs as nat) as int
                == coefficient as int * layout.coefficient_limbs as int)
                by(nonlinear_arith);
            assert(((coefficient as nat + 1) * layout.coefficient_limbs as nat) as int
                == (coefficient as int + 1) * layout.coefficient_limbs as int)
                by(nonlinear_arith);
            assert(layout.coefficient_limbs as nat
                == coefficient_limbs(precision_bits as nat));
            assert(src@.subrange(source_pos as int,
                (source_pos + slot_limbs) as int) == src_slot@);
            assert(value(src@.subrange(source_pos as int,
                (source_pos + slot_limbs) as int)) == value(src_slot@));
            slot_entry(
                src@, slot_limbs as nat, count as nat, coefficient as nat,
            );
            assert(packed_convolution::slots(src@, slot_limbs as nat, count as nat)
                [coefficient as int] == value(src_slot@));
            assert(0 <= value(src_slot@) < pow(2, precision_bits as nat));
            canonical_slot_low_value(
                src_slot@, precision_bits as nat, layout.coefficient_limbs as nat,
            );
            assert(src_slot@.subrange(0, layout.coefficient_limbs as int)
                == src_coefficient@);
            crate::radix::equal_prefix(
                src_slot@.subrange(0, layout.coefficient_limbs as int),
                src_coefficient@,
                layout.coefficient_limbs as nat,
            );
            assert(value(src_slot@.subrange(0, layout.coefficient_limbs as int))
                == value(src_coefficient@));
            assert(dst@.subrange(destination_pos as int,
                (destination_pos + layout.coefficient_limbs) as int)
                == src@.subrange(source_pos as int,
                    (source_pos + layout.coefficient_limbs) as int));
            crate::radix::equal_prefix(
                dst@.subrange(destination_pos as int,
                    (destination_pos + layout.coefficient_limbs) as int),
                src@.subrange(source_pos as int,
                    (source_pos + layout.coefficient_limbs) as int),
                layout.coefficient_limbs as nat,
            );
            assert(value(dst@.subrange(destination_pos as int,
                (destination_pos + layout.coefficient_limbs) as int))
                == value(src@.subrange(source_pos as int,
                    (source_pos + layout.coefficient_limbs) as int)));
            slot_entry(
                dst@, layout.coefficient_limbs as nat, count as nat, coefficient as nat,
            );
            assert(packed_convolution::slots(
                dst@, layout.coefficient_limbs as nat, count as nat,
            )[coefficient as int]
                == value(dst@.subrange(destination_pos as int,
                    (destination_pos + layout.coefficient_limbs) as int)));
            assert(dst@.subrange(0, destination_pos as int)
                == before_dst.subrange(0, destination_pos as int));
            assert forall|i: int| 0 <= i < (coefficient + 1) as int
                implies #[trigger] packed_convolution::slots(
                    src@, slot_limbs as nat, count as nat,
                )[i] == packed_convolution::slots(
                    dst@, layout.coefficient_limbs as nat, count as nat,
                )[i] by {
                if i < coefficient as int {
                    assert((i as nat) as int == i);
                    assert((coefficient as nat) as int == coefficient as int);
                    assert((layout.coefficient_limbs as nat) as int
                        == layout.coefficient_limbs as int);
                    assert((i as nat) as int == i);
                    assert((coefficient as nat) as int == coefficient as int);
                    assert((layout.coefficient_limbs as nat) as int
                        == layout.coefficient_limbs as int);
                    assert((destination_pos as nat) as int == destination_pos as int);
                    assert((i as nat) < (coefficient as nat)) by(nonlinear_arith)
                        requires
                            0 <= i < coefficient as int,
                            (i as nat) as int == i,
                            (coefficient as nat) as int == coefficient as int;
                    slot_range_before_end(
                        i as nat,
                        layout.coefficient_limbs as nat,
                        coefficient as nat,
                    );
                    assert(destination_pos as nat == coefficient as nat
                        * layout.coefficient_limbs as nat) by(nonlinear_arith)
                        requires
                            destination_pos
                                == coefficient * layout.coefficient_limbs,
                            (destination_pos as nat) as int == destination_pos as int,
                            (coefficient as nat) as int == coefficient as int,
                            (layout.coefficient_limbs as nat) as int
                                == layout.coefficient_limbs as int;
                    let slot_start = (i as nat * layout.coefficient_limbs as nat) as int;
                    let slot_end = ((i as nat + 1)
                        * layout.coefficient_limbs as nat) as int;
                    assert(0 <= slot_start);
                    assert(slot_start <= slot_end);
                    assert(slot_end
                        <= (coefficient as nat * layout.coefficient_limbs as nat) as int);
                    assert(slot_end <= (destination_pos as nat) as int);
                    assert(slot_end <= destination_pos as int);
                    equal_subrange_from_prefix(
                        dst@, before_dst, destination_pos as int, slot_start, slot_end,
                    );
                    slot_entry(dst@, layout.coefficient_limbs as nat,
                        count as nat, i as nat);
                    slot_entry(before_dst, layout.coefficient_limbs as nat,
                        count as nat, i as nat);
                    assert(value(dst@.subrange(slot_start, slot_end))
                        == value(before_dst.subrange(slot_start, slot_end)));
                    assert(packed_convolution::slots(
                        dst@, layout.coefficient_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        before_dst, layout.coefficient_limbs as nat, count as nat,
                    )[i]);
                    assert(packed_convolution::slots(
                        src@, slot_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        before_dst, layout.coefficient_limbs as nat, count as nat,
                    )[i]);
                } else {
                    assert(i == coefficient as int);
                    assert(packed_convolution::slots(
                        src@, slot_limbs as nat, count as nat,
                    )[i] == packed_convolution::slots(
                        dst@, layout.coefficient_limbs as nat, count as nat,
                    )[i]);
                }
            }
            assert(canonical_packed_slots(
                src@, count as nat, precision_bits as nat, slot_limbs as nat,
            ));
            assert(packed_convolution::slots(src@, slot_limbs as nat, count as nat)
                [coefficient as int]
                == value(src_slot@.subrange(0, layout.coefficient_limbs as int)));
            assert(packed_convolution::slots(
                    dst@, layout.coefficient_limbs as nat, count as nat,
                )[coefficient as int]
                == value(src_slot@.subrange(0, layout.coefficient_limbs as int)));
            assert(packed_convolution::slots(src@, slot_limbs as nat, count as nat)
                [coefficient as int]
                == packed_convolution::slots(
                    dst@, layout.coefficient_limbs as nat, count as nat,
                )[coefficient as int]);
            assert(copied_words
                == coefficient as nat * layout.coefficient_limbs as nat
                    + layout.coefficient_limbs as nat);
            assert(written_words
                == coefficient as nat * layout.coefficient_limbs as nat
                    + layout.coefficient_limbs as nat);
            assert((coefficient as nat + 1) * layout.coefficient_limbs as nat
                == coefficient as nat * layout.coefficient_limbs as nat
                    + layout.coefficient_limbs as nat) by(nonlinear_arith);
        }
        source_pos += slot_limbs;
        destination_pos += layout.coefficient_limbs;
        coefficient += 1;
    }
    proof {
        assert(copied_words == count as nat * layout.coefficient_limbs as nat);
        assert(written_words == count as nat * layout.coefficient_limbs as nat);
    }
    Ok(())
}

} // verus!

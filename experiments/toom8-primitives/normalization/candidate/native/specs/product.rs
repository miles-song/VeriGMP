//! Integer identities for truncated multiplication; no executable objects.
use vstd::prelude::*;
use crate::radix::*;

verus! {

pub open spec fn tail(words: Seq<u64>, start: nat) -> int
    recommends start <= words.len(),
    decreases words.len() - start,
{
    if start >= words.len() { 0 } else {
        (words[start as int] as int) + base() * tail(words, start + 1)
    }
}

pub proof fn split_value(words: Seq<u64>, start: nat)
    requires start <= words.len(),
    ensures value(words) == prefix(words, start) + radix(start) * tail(words, start),
    decreases words.len() - start,
{
    if start < words.len() {
        split_value(words, start + 1);
        assert(value(words) == prefix(words, start) + radix(start) * tail(words, start))
            by(nonlinear_arith)
            requires
                value(words) == prefix(words, start + 1) + radix(start + 1) * tail(words, start + 1),
                prefix(words, start + 1) == prefix(words, start) + (words[start as int] as int) * radix(start),
                radix(start + 1) == base() * radix(start),
                tail(words, start) == (words[start as int] as int) + base() * tail(words, start + 1);
    }
}

pub proof fn radix_add(a: nat, b: nat)
    ensures radix(a + b) == radix(a) * radix(b),
    decreases b,
{
    if b > 0 {
        radix_add(a, (b - 1) as nat);
        assert(radix(a + b) == radix(a) * radix(b)) by(nonlinear_arith)
            requires
                radix(a + b) == base() * radix((a + b - 1) as nat),
                radix((a + b - 1) as nat) == radix(a) * radix((b - 1) as nat),
                radix(b) == base() * radix((b - 1) as nat);
    }
}

pub proof fn subrange_value(words: Seq<u64>, start: nat, count: nat)
    requires start + count <= words.len(),
    ensures
        prefix(words, start + count) == prefix(words, start)
            + radix(start) * prefix(words.subrange(start as int, words.len() as int), count),
    decreases count,
{
    if count > 0 {
        subrange_value(words, start, (count - 1) as nat);
        radix_add(start, (count - 1) as nat);
        assert(prefix(words, start + count) == prefix(words, start)
            + radix(start) * prefix(words.subrange(start as int, words.len() as int), count))
            by(nonlinear_arith)
            requires
                prefix(words, start + count) == prefix(words, (start + count - 1) as nat)
                    + (words[start + count - 1] as int) * radix((start + count - 1) as nat),
                prefix(words, (start + count - 1) as nat) == prefix(words, start)
                    + radix(start) * prefix(words.subrange(start as int, words.len() as int), (count - 1) as nat),
                prefix(words.subrange(start as int, words.len() as int), count)
                    == prefix(words.subrange(start as int, words.len() as int), (count - 1) as nat)
                        + (words[start + count - 1] as int) * radix((count - 1) as nat),
                radix((start + count - 1) as nat) == radix(start) * radix((count - 1) as nat);
    }
}

/// Scale the exact MAC identity and extend the two processed prefixes.
pub proof fn mac_prefix_step(dp: int, op: int, bp: int, place: int, scale: int,
    word: int, digit: int, old: int, carry: int, low: int, high: int)
    requires
        dp + place * carry == op + scale * bp,
        low + base() * high == word * digit + old + carry,
    ensures
        (dp + low * place) + (base() * place) * high
            == (op + old * place) + scale * bp + word * digit * place,
{
    assert((dp + low * place) + (base() * place) * high
        == (op + old * place) + scale * bp + word * digit * place)
        by(nonlinear_arith)
        requires dp + place * carry == op + scale * bp,
            low + base() * high == word * digit + old + carry;
}

} // verus!

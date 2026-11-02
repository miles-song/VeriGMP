//! Arithmetic representation: little-endian base-2^64 words.
//! These definitions are mathematical and erase from executable code.
use vstd::prelude::*;
use vstd::arithmetic::power::*;

verus! {

pub open spec fn base() -> int { 18446744073709551616int }

pub open spec fn radix(n: nat) -> int
    decreases n,
{
    if n == 0 { 1 } else { base() * radix((n - 1) as nat) }
}

pub open spec fn prefix(words: Seq<u64>, n: nat) -> int
    recommends n <= words.len(),
    decreases n,
{
    if n == 0 { 0 } else {
        prefix(words, (n - 1) as nat) + (words[n - 1] as int) * radix((n - 1) as nat)
    }
}

pub open spec fn value(words: Seq<u64>) -> int { prefix(words, words.len()) }

pub proof fn radix_positive(n: nat)
    ensures radix(n) > 0,
    decreases n,
{
    if n > 0 {
        radix_positive((n - 1) as nat);
        assert(base() * radix((n - 1) as nat) > 0) by(nonlinear_arith)
            requires base() > 0, radix((n - 1) as nat) > 0;
    }
}

pub proof fn prefix_range(words: Seq<u64>, n: nat)
    requires n <= words.len(),
    ensures 0 <= prefix(words, n) < radix(n),
    decreases n,
{
    if n > 0 {
        prefix_range(words, (n - 1) as nat);
        radix_positive((n - 1) as nat);
        assert(0 <= prefix(words, n) < radix(n)) by(nonlinear_arith)
            requires
                0 <= prefix(words, (n - 1) as nat) < radix((n - 1) as nat),
                0 <= (words[n - 1] as int) < base(),
                radix((n - 1) as nat) > 0,
                radix(n) == base() * radix((n - 1) as nat),
                prefix(words, n) == prefix(words, (n - 1) as nat)
                    + (words[n - 1] as int) * radix((n - 1) as nat);
    }
}

pub proof fn equal_prefix(a: Seq<u64>, b: Seq<u64>, n: nat)
    requires
        n <= a.len(), n <= b.len(),
        forall|j: int| 0 <= j < n ==> a[j] == b[j],
    ensures prefix(a, n) == prefix(b, n),
    decreases n,
{
    if n > 0 { equal_prefix(a, b, (n - 1) as nat); }
}

pub proof fn radix_is_power_of_two(n: nat)
    ensures radix(n) == pow(2, 64 * n),
    decreases n,
{
    assert(pow(2, 64) == base()) by(compute);
    if n > 0 {
        radix_is_power_of_two((n - 1) as nat);
        lemma_pow_adds(2, 64 * ((n - 1) as nat), 64);
        assert(64 * ((n - 1) as nat) + 64 == 64 * n);
    } else { reveal(pow); }
}

} // verus!

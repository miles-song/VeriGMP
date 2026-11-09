//! Imported checked callers of the actual compiled native library pair.
use vstd::prelude::*;
use verigmp::{arithmetic, fast_multiply, fixed_row, radix::*, precision::*};

verus! {
pub fn selected<const N: usize>(dst: &mut [u64], a: &[u64], b: &[u64])
    requires 0 < N <= usize::MAX / 2, a@.len() == N, b@.len() == N, old(dst)@.len() == 2 * N,
    ensures final(dst)@.len() == old(dst)@.len(), value(final(dst)@) == value(a@) * value(b@),
{
    fixed_row::full::<N>(dst, a, b);
}

pub fn forced(dst: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], threshold: usize)
    requires a@.len() > 0, a@.len() == b@.len(), old(dst)@.len() == 2 * a@.len(),
        old(scratch)@.len() >= 3 * a@.len(), threshold >= 8,
    ensures final(dst)@.len() == old(dst)@.len(), final(scratch)@.len() == old(scratch)@.len(),
        value(final(dst)@) == value(a@) * value(b@),
{
    fast_multiply::full(dst, a, b, scratch, threshold);
}

pub fn multiply(dst: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], top: u32)
    requires a@.len() > 0, a@.len() == b@.len(), old(dst)@.len() == a@.len(),
        old(scratch)@.len() >= 12 * a@.len(), 1 <= top <= 64,
    ensures final(dst)@.len() == old(dst)@.len(), final(scratch)@.len() == old(scratch)@.len(),
        value(final(dst)@) == (value(a@) * value(b@)) % modulus(a@.len(), top as nat),
{
    arithmetic::mul_mod(dst, a, b, scratch, top);
}

pub fn square(dst: &mut [u64], a: &[u64], scratch: &mut [u64], top: u32)
    requires a@.len() > 0, old(dst)@.len() == a@.len(), old(scratch)@.len() >= 10 * a@.len(), 1 <= top <= 64,
    ensures final(dst)@.len() == old(dst)@.len(), final(scratch)@.len() == old(scratch)@.len(),
        value(final(dst)@) == (value(a@) * value(a@)) % modulus(a@.len(), top as nat),
{
    arithmetic::square_mod(dst, a, scratch, top);
}
}

// Ordinary main executes those checked callers with public native ABI and disjoint buffers.
fn main() {
    let a = [u64::MAX; 15]; let b = [1u64; 15];
    let mut direct = [0xa5a5a5a5a5a5a5a5; 30]; let mut recursive = [0xa5a5a5a5a5a5a5a5; 30];
    let mut scratch = [0xa5a5a5a5a5a5a5a5; 180]; let mut dst = [0xa5a5a5a5a5a5a5a5; 15];
    selected::<15>(&mut direct, &a, &b);
    forced(&mut recursive, &a, &b, &mut scratch, 24);
    assert_eq!(direct, recursive);
    multiply(&mut dst, &a, &b, &mut scratch, 64);
    assert_eq!(dst, direct[..15]);
    square(&mut dst, &a, &mut scratch, 63);
    assert!(dst[14] < (1u64 << 63));
    println!("actual imported consumer passed");
}

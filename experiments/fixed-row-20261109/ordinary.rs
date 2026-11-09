//! Unverified same-algorithm const-row code-generation/oracle control.
#[inline(always)]
fn wide(a: u64, b: u64, acc: u64, carry: u128) -> (u64, u128) {
    let total = (a as u128) * (b as u128) + (acc as u128) + carry;
    let radix: u128 = 18446744073709551616;
    ((total % radix) as u64, total / radix)
}

#[inline(always)]
fn first<const N: usize>(dst: &mut [u64], b: &[u64], word: u64) -> u64 {
    assert!(dst.len() == N && b.len() == N);
    let mut j = 0usize;
    let mut carry = 0u128;
    while j < N {
        let (low, next) = wide(word, b[j], 0, carry);
        dst[j] = low;
        carry = next;
        j += 1;
    }
    carry as u64
}

#[inline(always)]
fn add<const N: usize>(dst: &mut [u64], b: &[u64], word: u64) -> u64 {
    assert!(dst.len() == N && b.len() == N);
    let mut j = 0usize;
    let mut carry = 0u128;
    while j < N {
        let (low, next) = wide(word, b[j], dst[j], carry);
        dst[j] = low;
        carry = next;
        j += 1;
    }
    carry as u64
}

#[inline(always)]
pub fn full<const N: usize>(dst: &mut [u64], a: &[u64], b: &[u64]) {
    assert!(N > 0 && N <= usize::MAX / 2 && dst.len() == 2 * N && a.len() == N && b.len() == N);
    let carry = first::<N>(&mut dst[..N], b, a[0]);
    dst[N] = carry;
    let mut i = 1usize;
    while i < N {
        let carry = add::<N>(&mut dst[i..i + N], b, a[i]);
        dst[i + N] = carry;
        i += 1;
    }
}

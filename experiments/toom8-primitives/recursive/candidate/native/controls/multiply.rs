//! Ordinary safe Rust control: same truncated algorithm, no proof annotations.
pub fn mac(a: u64, b: u64, acc: u64, carry: u64) -> (u64, u64) {
    let total = (a as u128) * (b as u128) + (acc as u128) + (carry as u128);
    (total as u64, (total >> 64) as u64)
}

pub fn add_mul_word(dst: &mut [u64], rhs: &[u64], word: u64) -> u64 {
    assert!(dst.len() <= rhs.len());
    let mut carry = 0;
    for (x, y) in dst.iter_mut().zip(rhs) {
        let (low, high) = mac(word, *y, *x, carry);
        *x = low;
        carry = high;
    }
    carry
}

pub fn add_mul_at(dst: &mut [u64], rhs: &[u64], word: u64, offset: usize) {
    assert!(dst.len() == rhs.len());
    assert!(offset <= dst.len());
    let _carry = add_mul_word(&mut dst[offset..], rhs, word);
}

pub fn mul_low(dst: &mut [u64], lhs: &[u64], rhs: &[u64]) {
    assert!(dst.len() == lhs.len());
    assert!(lhs.len() == rhs.len());
    dst.fill(0);
    for (i, word) in lhs.iter().copied().enumerate() {
        add_mul_at(dst, rhs, word, i);
    }
}

pub fn mul_mod(dst: &mut [u64], lhs: &[u64], rhs: &[u64], top: u32) {
    assert!(dst.len() > 0);
    assert!(1 <= top && top <= 64);
    mul_low(dst, lhs, rhs);
    let last = dst.len() - 1;
    if top < 64 { dst[last] &= (1u64 << top) - 1; }
}

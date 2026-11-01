//! Ordinary Rust comparison only; this is not a verified production module.
pub fn add_assign(dst: &mut [u64], rhs: &[u64]) -> u64 {
    assert!(dst.len() == rhs.len());
    let mut i = 0;
    let mut carry = 0;
    while i < dst.len() {
        let total = (dst[i] as u128) + (rhs[i] as u128) + (carry as u128);
        dst[i] = total as u64;
        carry = (total >> 64) as u64;
        i += 1;
    }
    carry
}

//! Unverified performance prototype; excluded from production native modules.

/// Write a requested product prefix. All arithmetic domains are checked once.
#[inline(never)]
pub fn column_prefix(dst: &mut [u64], a: &[u64], b: &[u64]) {
    assert!(!a.is_empty() && a.len() <= 128);
    assert!(!b.is_empty() && b.len() <= 128);
    assert!(!dst.is_empty() && dst.len() <= a.len() + b.len());
    let mut carry = 0u128;
    for (k, word) in dst.iter_mut().enumerate() {
        let start = k.saturating_sub(b.len() - 1);
        let end = (k + 1).min(a.len());
        let (mut low0, mut high0, mut low1, mut high1) = (0u128, 0u128, 0u128, 0u128);
        let left = a[start..end].chunks_exact(2);
        let right = b[k + 1 - end..k + 1 - start].rchunks_exact(2);
        let tail = left.remainder().first().zip(right.remainder().first());
        for (a_pair, b_pair) in left.zip(right) {
            let first = (a_pair[0] as u128) * (b_pair[1] as u128);
            let second = (a_pair[1] as u128) * (b_pair[0] as u128);
            low0 += (first as u64) as u128;
            high0 += first >> 64;
            low1 += (second as u64) as u128;
            high1 += second >> 64;
        }
        if let Some((&last_a, &last_b)) = tail {
            let product = (last_a as u128) * (last_b as u128);
            low0 += (product as u64) as u128;
            high0 += product >> 64;
        }
        let low = (carry as u64) as u128 + low0 + low1;
        carry = (carry >> 64) + high0 + high1 + (low >> 64);
        *word = low as u64;
    }
}

#[inline(never)]
pub fn column_full(dst: &mut [u64], a: &[u64], b: &[u64]) {
    assert_eq!(a.len(), b.len());
    assert_eq!(dst.len(), 2 * a.len());
    column_prefix(dst, a, b);
}

#[inline(never)]
pub fn column_low(dst: &mut [u64], a: &[u64], b: &[u64]) {
    assert_eq!(a.len(), b.len());
    assert_eq!(dst.len(), a.len());
    column_prefix(dst, a, b);
}

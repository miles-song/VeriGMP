//! Unverified ordinary Rust control with the same semantics and algorithm.
#[path = "limbs.rs"] mod limb_control;

pub fn precision_layout(bits: usize) -> (usize, u32) {
    assert!(bits > 0);
    let remaining = bits - 1;
    (remaining / 64 + 1, (remaining % 64) as u32 + 1)
}

pub fn mask_word(word: u64, bits: u32) -> u64 {
    assert!(1 <= bits && bits <= 64);
    if bits == 64 { word } else { word & ((1u64 << bits) - 1) }
}

pub fn normalize_top(dst: &mut [u64], top: u32) {
    assert!(dst.len() > 0);
    let last = dst.len() - 1;
    dst[last] = mask_word(dst[last], top);
}

pub fn add_mod_assign(dst: &mut [u64], rhs: &[u64], top: u32) {
    assert!(dst.len() > 0);
    assert!(1 <= top && top <= 64);
    let _carry = limb_control::add_assign(dst, rhs);
    normalize_top(dst, top);
}

pub fn sub_mod_assign(dst:&mut[u64],rhs:&[u64],top:u32) {
    assert!(dst.len()>0);assert!(1<=top && top<=64);
    let _borrow=limb_control::sub_assign(dst,rhs);
    normalize_top(dst,top);
}

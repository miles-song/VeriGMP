//! Unverified ordinary/verified compiler comparison, with runtime arguments.
#[path = "specs/radix.rs"] mod radix;
#[path = "specs/precision.rs"] mod precision;
#[path = "verified/kernel.rs"] mod kernel;
#[path = "verified/limbs.rs"] mod limbs;
#[path = "verified/pow2.rs"] mod pow2;
#[path = "controls/pow2.rs"] mod control;

#[no_mangle]
pub fn verified_layout(bits: usize) -> (usize, u32) { pow2::precision_layout(bits) }
#[no_mangle]
pub fn ordinary_layout(bits: usize) -> (usize, u32) { control::precision_layout(bits) }
#[no_mangle]
pub fn verified_mask(word: u64, bits: u32) -> u64 { pow2::mask_word(word, bits) }
#[no_mangle]
pub fn ordinary_mask(word: u64, bits: u32) -> u64 { control::mask_word(word, bits) }
#[no_mangle]
pub fn verified_normalize(dst: &mut [u64], top: u32) { pow2::normalize_top(dst, top); }
#[no_mangle]
pub fn ordinary_normalize(dst: &mut [u64], top: u32) { control::normalize_top(dst, top); }
#[no_mangle]
pub fn verified_add_mod(dst: &mut [u64], rhs: &[u64], top: u32) { pow2::add_mod_assign(dst, rhs, top); }
#[no_mangle]
pub fn ordinary_add_mod(dst: &mut [u64], rhs: &[u64], top: u32) { control::add_mod_assign(dst, rhs, top); }

fn main() {}

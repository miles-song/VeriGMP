//! Unverified code-generation harness; exported arguments are runtime values.
#[path = "specs/radix.rs"] mod radix;
#[path = "specs/precision.rs"] mod precision;
#[path = "specs/product.rs"] mod product;
#[path = "verified/kernel.rs"] mod kernel;
#[path = "verified/limbs.rs"] mod limbs;
#[path = "verified/pow2.rs"] mod pow2;
#[path = "verified/multiply.rs"] mod multiply;
#[path = "controls/multiply.rs"] mod control;

#[no_mangle]
pub fn verified_mac(a: u64, b: u64, acc: u64, carry: u64) -> (u64, u64) { multiply::mac(a,b,acc,carry) }
#[no_mangle]
pub fn ordinary_mac(a: u64, b: u64, acc: u64, carry: u64) -> (u64, u64) { control::mac(a,b,acc,carry) }
#[no_mangle]
pub fn verified_word(dst: &mut [u64], rhs: &[u64], word: u64) -> u64 { multiply::add_mul_word(dst,rhs,word) }
#[no_mangle]
pub fn ordinary_word(dst: &mut [u64], rhs: &[u64], word: u64) -> u64 { control::add_mul_word(dst,rhs,word) }
#[no_mangle]
pub fn verified_row(dst: &mut [u64], rhs: &[u64], word: u64, offset: usize) { multiply::add_mul_at(dst,rhs,word,offset); }
#[no_mangle]
pub fn ordinary_row(dst: &mut [u64], rhs: &[u64], word: u64, offset: usize) { control::add_mul_at(dst,rhs,word,offset); }
#[no_mangle]
pub fn verified_low(dst: &mut [u64], lhs: &[u64], rhs: &[u64]) { multiply::mul_low(dst,lhs,rhs); }
#[no_mangle]
pub fn ordinary_low(dst: &mut [u64], lhs: &[u64], rhs: &[u64]) { control::mul_low(dst,lhs,rhs); }
#[no_mangle]
pub fn verified_mul(dst: &mut [u64], lhs: &[u64], rhs: &[u64], top: u32) { multiply::mul_mod(dst,lhs,rhs,top); }
#[no_mangle]
pub fn ordinary_mul(dst: &mut [u64], lhs: &[u64], rhs: &[u64], top: u32) { control::mul_mod(dst,lhs,rhs,top); }

fn main() {}

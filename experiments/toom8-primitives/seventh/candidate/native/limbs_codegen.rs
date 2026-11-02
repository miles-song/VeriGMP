//! Unverified ordinary-Rust control and wrappers around the verified code.
#[path = "specs/radix.rs"]
mod radix;
#[path = "verified/kernel.rs"]
mod kernel;
#[path = "verified/limbs.rs"]
mod limbs;
#[path = "controls/limbs.rs"]
mod control;

#[no_mangle]
pub fn verified_add_assign(dst: &mut [u64], rhs: &[u64]) -> u64 {
    limbs::add_assign(dst, rhs)
}

#[no_mangle]
pub fn ordinary_add_assign(dst: &mut [u64], rhs: &[u64]) -> u64 {
    control::add_assign(dst, rhs)
}

fn main() {}

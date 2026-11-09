//! Ordinary public-API wrappers with same-algorithm const-row controls.
mod ordinary;

macro_rules! pair {
    ($n:literal, $verified:ident, $control:ident) => {
        #[no_mangle]
        #[inline(never)]
        pub fn $verified(dst: &mut [u64], a: &[u64], b: &[u64]) { verigmp::fixed_row::full::<$n>(dst, a, b); }
        #[no_mangle]
        #[inline(never)]
        pub fn $control(dst: &mut [u64], a: &[u64], b: &[u64]) { ordinary::full::<$n>(dst, a, b); }
    };
}
pair!(15, fixed_15, ordinary_15);
pair!(20, fixed_20, ordinary_20);
pair!(22, fixed_22, ordinary_22);
pair!(23, fixed_23, ordinary_23);

#[no_mangle]
#[inline(never)]
pub fn native_forced(dst: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64]) {
    verigmp::fast_multiply::full(dst, a, b, scratch, 24);
}

#[no_mangle]
#[inline(never)]
pub fn native_mul(dst: &mut [u64], a: &[u64], b: &[u64], scratch: &mut [u64], top: u32) {
    verigmp::arithmetic::mul_mod(dst, a, b, scratch, top);
}

#[no_mangle]
#[inline(never)]
pub fn native_square(dst: &mut [u64], a: &[u64], scratch: &mut [u64], top: u32) {
    verigmp::arithmetic::square_mod(dst, a, scratch, top);
}

//! Verified arithmetic on caller-owned little-endian u64 slices.
#[path="specs/radix.rs"] pub mod radix;
#[path="specs/precision.rs"] pub mod precision;
#[path="specs/product.rs"] pub mod product;
#[path="specs/fast_product.rs"] pub mod fast_product;
#[path="verified/kernel.rs"] pub mod kernel;
#[path="verified/limbs.rs"] pub mod limbs;
#[path="verified/pow2.rs"] pub mod pow2;
#[path="verified/multiply.rs"] pub mod multiply;
#[path="verified/fast_words.rs"] pub mod fast_words;
#[path="verified/fast_multiply.rs"] pub mod fast_multiply;

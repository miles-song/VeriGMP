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
#[path="specs/toom.rs"] pub mod toom;
#[path="specs/toom_blocks.rs"] pub mod toom_blocks;
#[path="specs/square.rs"] pub mod square_spec;
#[path="verified/toom_words.rs"] pub mod toom_words;
#[path="verified/toom_evaluate.rs"] pub mod toom_evaluate;
#[path="verified/toom_interpolate.rs"] pub mod toom_interpolate;
#[path="verified/toom_multiply.rs"] pub mod toom_multiply;
#[path="verified/toom_low.rs"] pub mod toom_low;
#[path="verified/square.rs"] pub mod square;
#[path="verified/toom_square.rs"] pub mod toom_square;
#[path="verified/square_low.rs"] pub mod square_low;
#[path="verified/mac4.rs"] pub mod mac4;
#[path="verified/arithmetic.rs"] pub mod arithmetic;

#[path="specs/square_base.rs"] pub mod square_base_spec;
#[path="verified/square_base.rs"] pub mod square_base;
#[path="specs/toom4.rs"] pub mod toom4;
#[path="verified/toom4_interpolate.rs"] pub mod toom4_interpolate;
#[path="verified/toom4_evaluate.rs"] pub mod toom4_evaluate;
#[path="specs/toom4_blocks.rs"] pub mod toom4_blocks;
#[path="verified/toom4_multiply.rs"] pub mod toom4_multiply;
#[path="verified/toom4_square.rs"] pub mod toom4_square;
#[path="verified/toom4_low.rs"] pub mod toom4_low;
#[path="verified/toom4_square_low.rs"] pub mod toom4_square_low;
#[path="verified/toom4_candidate.rs"] pub mod toom4_candidate;

#[path="specs/odd_division.rs"] pub mod odd_division_spec;
#[path="verified/odd_division.rs"] pub mod odd_division;

#[path="verified/scaled_subtraction.rs"] pub mod scaled_subtraction;

#[path="specs/signed_evaluation.rs"] pub mod signed_evaluation_spec;
#[path="verified/signed_evaluation.rs"] pub mod signed_evaluation;

#[path="specs/wide_odd_division.rs"] pub mod wide_odd_division_spec;
#[path="verified/wide_odd_division.rs"] pub mod wide_odd_division;

#[path="specs/toom8_newton.rs"] pub mod toom8_newton_spec;
#[path="verified/toom8_newton.rs"] pub mod toom8_newton;
#[no_mangle]pub fn verified_newton_even(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64]){toom8_newton::even(a0,a1,a2,a3,a4,a5);}
#[no_mangle]pub fn verified_newton_odd(a0:&mut[u64],a1:&mut[u64],a2:&mut[u64],a3:&mut[u64],a4:&mut[u64],a5:&mut[u64],a6:&mut[u64]){toom8_newton::odd(a0,a1,a2,a3,a4,a5,a6);}
fn main(){}

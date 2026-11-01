#[path="specs/radix.rs"] mod radix;
#[path="specs/precision.rs"] mod precision;
#[path="specs/product.rs"] mod product;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="specs/toom.rs"] mod toom;
#[path="specs/toom_blocks.rs"] mod toom_blocks;
#[path="specs/square.rs"] mod square_spec;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/toom_words.rs"] mod toom_words;
#[path="verified/toom_evaluate.rs"] mod toom_evaluate;
#[path="verified/toom_interpolate.rs"] mod toom_interpolate;
#[path="verified/fast_multiply.rs"] mod fast_multiply;
#[path="verified/toom_multiply.rs"] mod toom_multiply;
#[path="verified/toom_low.rs"] mod toom_low;
#[path="verified/square.rs"] mod square;
#[path="verified/toom_square.rs"] mod toom_square;
#[path="verified/square_low.rs"] mod square_low;
#[path="verified/mac4.rs"] mod mac4;
#[path="verified/arithmetic.rs"] mod arithmetic;

#[no_mangle]pub fn verified_product(out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32){toom4_candidate::mul_mod(out,a,b,scratch,top);}
#[no_mangle]pub fn verified_square(out:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32){toom4_candidate::square_mod(out,a,scratch,top);}
#[no_mangle]pub fn verified_mac4(out:&mut[u64],a:&[u64],word:u64)->u64{mac4::add_mul_word(out,a,word)}
fn main(){}

#[path="specs/square_base.rs"] mod square_base_spec;
#[path="verified/square_base.rs"] mod square_base;

#[path="specs/toom4.rs"] mod toom4;
#[path="verified/toom4_interpolate.rs"] mod toom4_interpolate;
#[path="verified/toom4_evaluate.rs"] mod toom4_evaluate;
#[path="specs/toom4_blocks.rs"] mod toom4_blocks;
#[path="verified/toom4_multiply.rs"] mod toom4_multiply;
#[path="verified/toom4_square.rs"] mod toom4_square;
#[path="verified/toom4_low.rs"] mod toom4_low;
#[path="verified/toom4_square_low.rs"] mod toom4_square_low;
#[path="verified/toom4_candidate.rs"] mod toom4_candidate;

#[path="specs/odd_division.rs"] mod odd_division_spec;
#[path="verified/odd_division.rs"] mod odd_division;

#[no_mangle]pub fn verified_exact3(dst:&mut[u64]){toom_words::divide_exact(dst,3);}
#[no_mangle]pub fn verified_exact9(dst:&mut[u64]){toom_words::divide_exact(dst,9);}
#[no_mangle]pub fn verified_exact15(dst:&mut[u64]){toom_words::divide_exact(dst,15);}

#[path="verified/scaled_subtraction.rs"] mod scaled_subtraction;

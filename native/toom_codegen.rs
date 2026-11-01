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

#[no_mangle]pub fn verified_product(out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32){arithmetic::mul_mod(out,a,b,scratch,top);}
#[no_mangle]pub fn verified_square(out:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32){arithmetic::square_mod(out,a,scratch,top);}
#[no_mangle]pub fn verified_mac4(out:&mut[u64],a:&[u64],word:u64)->u64{mac4::add_mul_word(out,a,word)}
fn main(){}
